"""FastAPI REST server — bridges the React frontend to the ADK orchestrator."""

import json
import logging
import re
import uuid
from pathlib import Path

from dotenv import load_dotenv

# Load .env BEFORE any ADK imports so GOOGLE_API_KEY is in the environment
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

# Reset cached settings so they reload from the fresh .env
from concierge.config.settings import reset_settings
reset_settings()

import tenacity
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from google.adk.runners import InMemoryRunner
from google.genai import errors as genai_errors
from google.genai import types

from concierge.agents.orchestrator import build_concierge_orchestrator
from concierge.config.settings import get_settings
from concierge.tools.state_tools import KEY_CURRENT_PLAN, KEY_GUEST_PROFILE

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------


class TimeWindow(BaseModel):
    start_time: str
    end_time: str


class ProfilePayload(BaseModel):
    interests: list[str] = []
    dietary_restrictions: list[str] = []
    pace: str = "moderate"
    budget_level: str = "moderate"
    party_composition: str = "solo"
    time_available: TimeWindow = TimeWindow(start_time="09:00", end_time="21:00")


class PlanRequest(BaseModel):
    profile: ProfilePayload


# ── Response models ──

class TravelSegment(BaseModel):
    mode: str = "walking"
    duration_minutes: int = 0
    distance_km: float = 0.0


class PlaceInfo(BaseModel):
    place_id: str = ""
    name: str = "Unknown"
    category: str = "place"
    rating: float = 0.0
    price_level: int = 2
    address: str = ""
    lat_lng: list[float] = [0.0, 0.0]
    opening_hours: list[str] = []
    dietary_compatibility: float = 0.8
    interest_match: float = 0.8
    travel_time_from_hotel: int = 10
    booking_available: bool = False
    source: str = "places_api"
    website: str = ""


class StopResponse(BaseModel):
    order: int
    place: PlaceInfo
    arrival_time: str = ""
    departure_time: str = ""
    duration_minutes: int = 60
    travel_to_next: TravelSegment | None = None
    notes: str = ""


class DayPlanResponse(BaseModel):
    date: str = ""
    stops: list[StopResponse] = []
    total_travel_time: int = 0
    estimated_total_cost: str = ""
    weather_contingency: str = ""
    back_at_hotel_by: str = ""
    map_url: str | None = None


class PlanResponse(BaseModel):
    day_plan: DayPlanResponse | None = None
    message: str = ""
    error: str = ""


class ErrorResponse(BaseModel):
    error: str
    detail: str = ""


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

settings = get_settings()
app = FastAPI(title=f"{settings.hotel_name} Concierge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",    # Vite dev server
        "http://localhost:4173",    # Vite preview
        "http://127.0.0.1:5173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Build the orchestrator and runner once at startup
orchestrator = build_concierge_orchestrator()
runner = InMemoryRunner(agent=orchestrator, app_name=settings.app_name)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _try_parse_plan_from_text(text: str) -> dict | None:
    """Try extracting a JSON plan from the Presenter's text output."""
    # Strip markdown code fences
    match = re.search(r"```(?:json)?\s*({.*?})\s*```", text, re.DOTALL)
    json_str = match.group(1) if match else text.strip()

    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError:
        return None

    # Handle nested structures — look for the plan dict
    if "stops" in parsed:
        return parsed
    if "day_plan_summary" in parsed:
        return parsed.get("day_plan_summary")
    if "itinerary" in parsed:
        # Convert simplified itinerary format to our stop format
        stops = []
        for i, item in enumerate(parsed.get("itinerary", [])):
            stops.append({
                "order": item.get("stop_number", i + 1),
                "place": {
                    "name": item.get("name", "Unknown"),
                    "category": "place",
                    "rating": 0,
                    "price_level": 2,
                    "address": "",
                    "lat": 0, "lng": 0,
                    "source": "agent_text",
                },
                "arrival_time": item.get("time", ""),
                "departure_time": "",
                "duration_minutes": 60,
                "travel_to_next": None,
                "notes": item.get("reason", ""),
            })
        return {
            "date": "",
            "stops": stops,
            "total_travel_time": 0,
            "estimated_total_cost": parsed.get("estimated_cost", ""),
            "weather_contingency": "",
            "back_at_hotel_by": parsed.get("return_time", ""),
        }
    return None


def _profile_to_state_dict(profile: ProfilePayload, session_id: str) -> dict:
    """Convert the frontend profile payload into the session state dict shape."""
    dietary = (
        [] if profile.dietary_restrictions == ["none"]
        else profile.dietary_restrictions
    )
    return {
        "guest_id": f"guest-{session_id[:8]}",
        "dietary_restrictions": dietary,
        "interests": profile.interests,
        "mobility": "full",
        "budget_level": profile.budget_level,
        "pace": profile.pace,
        "party_composition": profile.party_composition,
        "time_available": {
            "start_time": profile.time_available.start_time,
            "end_time": profile.time_available.end_time,
        },
        "location_context": settings.hotel_address,
        "special_requests": [],
    }


def _transform_plan_for_frontend(plan: dict) -> dict:
    """Adapt the backend DayPlan shape to match what the frontend expects.

    Key differences:
    - Backend TravelSegment uses `distance_meters` (int)
    - Frontend TravelSegment uses `distance_km` (float)
    - Backend place uses `lat`/`lng` → frontend expects `lat_lng` tuple
    - Frontend expects fields like `dietary_compatibility`, `interest_match`, etc.
    """
    transformed_stops = []
    for stop in plan.get("stops", []):
        place = stop.get("place", {})

        # Normalise lat/lng to lat_lng tuple
        if "lat_lng" not in place and "lat" in place:
            place["lat_lng"] = [place.pop("lat", 0), place.pop("lng", 0)]

        # Ensure frontend-expected fields have defaults
        place.setdefault("dietary_compatibility", 0.8)
        place.setdefault("interest_match", 0.8)
        place.setdefault("travel_time_from_hotel", 10)
        place.setdefault("booking_available", False)
        place.setdefault("source", "places_api")

        # Transform travel segment
        travel = stop.get("travel_to_next")
        if travel and "distance_meters" in travel:
            travel["distance_km"] = round(travel.pop("distance_meters") / 1000, 1)

        # Map backend mode names to frontend names
        if travel and travel.get("mode") == "walk":
            travel["mode"] = "walking"
        if travel and travel.get("mode") == "drive":
            travel["mode"] = "driving"

        transformed_stops.append({
            "order": stop.get("order", 0),
            "place": place,
            "arrival_time": stop.get("arrival_time", ""),
            "departure_time": stop.get("departure_time", ""),
            "duration_minutes": stop.get("duration_minutes", 60),
            "travel_to_next": travel,
            "notes": stop.get("notes", ""),
        })

    # Generate Google Maps multi-stop directions URL
    hotel_lat = settings.hotel_lat
    hotel_lng = settings.hotel_lng
    waypoints = [f"{hotel_lat},{hotel_lng}"]
    for stop in transformed_stops:
        place = stop.get("place", {})
        lat_lng = place.get("lat_lng", [0, 0])
        if lat_lng and lat_lng != [0, 0] and lat_lng != [0.0, 0.0]:
            waypoints.append(f"{lat_lng[0]},{lat_lng[1]}")
    waypoints.append(f"{hotel_lat},{hotel_lng}")  # return to hotel
    map_url = "https://www.google.com/maps/dir/" + "/".join(waypoints)

    return {
        "date": plan.get("date", ""),
        "stops": transformed_stops,
        "total_travel_time": plan.get("total_travel_time", 0),
        "estimated_total_cost": plan.get("estimated_total_cost", ""),
        "weather_contingency": plan.get("weather_contingency", ""),
        "back_at_hotel_by": plan.get("back_at_hotel_by", ""),
        "map_url": map_url,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {"status": "ok", "hotel": settings.hotel_name}


@app.post("/plan")
async def create_plan(
    body: PlanRequest,
    x_session_id: str = Header(default=""),
):
    # Always generate a unique session ID to avoid AlreadyExistsError on retries
    session_id = f"session-{uuid.uuid4().hex}"
    user_id = f"user-{uuid.uuid4().hex[:8]}"

    profile_dict = _profile_to_state_dict(body.profile, session_id)

    # Build a message that tells the agents the profile is already collected
    profile_summary = (
        f"The guest has already completed the questionnaire. "
        f"Here is their profile:\n"
        f"Interests: {', '.join(profile_dict['interests'])}\n"
        f"Dietary restrictions: {', '.join(profile_dict['dietary_restrictions']) or 'none'}\n"
        f"Pace: {profile_dict['pace']}\n"
        f"Budget: {profile_dict['budget_level']}\n"
        f"Party: {profile_dict['party_composition']}\n"
        f"Time: {profile_dict['time_available']['start_time']} – "
        f"{profile_dict['time_available']['end_time']}\n"
        f"Hotel location: {settings.hotel_address}\n\n"
        f"Please save this profile using save_guest_profile, then proceed to "
        f"discover places, build a route, and present the day plan."
    )

    logger.info("Using hotel address: %s (lat=%s, lng=%s)", settings.hotel_address, settings.hotel_lat, settings.hotel_lng)
    logger.info("Profile summary sent to agents: %s", profile_summary[:200])

    message = types.UserContent(parts=[types.Part(text=profile_summary)])

    def _is_retryable(exc: BaseException) -> bool:
        return isinstance(exc, genai_errors.ServerError) and exc.code >= 500

    try:
        run_start = time.monotonic()
        logger.info("[  0.0s] ── concierge pipeline START ──────────────────────────────")

        last_text = ""
        attempt_num = 0

        try:
            async with asyncio.timeout(settings.request_timeout_seconds):
                async for attempt in tenacity.AsyncRetrying(
                    retry=tenacity.retry_if_exception(_is_retryable),
                    wait=tenacity.wait_exponential(multiplier=1, min=2, max=30),
                    stop=tenacity.stop_after_attempt(3),
                    reraise=True,
                    before_sleep=lambda rs: logger.warning(
                        "[%5.1fs] Gemini 5xx (attempt %d) — retrying in %.1fs",
                        time.monotonic() - run_start,
                        rs.attempt_number,
                        rs.next_action.sleep,  # type: ignore[union-attr]
                    ),
                ):
                    with attempt:
                        attempt_num += 1
                        attempt_session_id = session_id if attempt_num == 1 else f"{session_id}-r{attempt_num}"
                        session = await runner.session_service.create_session(
                            app_name=settings.app_name,
                            user_id=user_id,
                            session_id=attempt_session_id,
                        )
                        last_text = ""
                        async for event in runner.run_async(
                            user_id=user_id,
                            session_id=session.id,
                            new_message=message,
                        ):
                            elapsed = time.monotonic() - run_start
                            _log_adk_event(event, elapsed)
                            if event.content and event.content.parts:
                                for part in event.content.parts:
                                    if part.text:
                                        last_text = part.text

        except TimeoutError:
            elapsed = time.monotonic() - run_start
            logger.error(
                "[%5.1fs] Orchestrator timed out after %ds",
                elapsed,
                settings.request_timeout_seconds,
            )
            raise HTTPException(
                status_code=504,
                detail=f"Plan generation timed out after {settings.request_timeout_seconds}s",
            )

        elapsed = time.monotonic() - run_start
        logger.info("[%5.1fs] ── concierge pipeline END ────────────────────────────────", elapsed)

        # Re-fetch session to get the latest state after the run
        session = await runner.session_service.get_session(
            app_name=settings.app_name,
            user_id=user_id,
            session_id=session.id,
        )

        state_keys = list(session.state.keys()) if session else []
        logger.info("Session state keys after run: %s", state_keys)

        plan = session.state.get(KEY_CURRENT_PLAN) if session else None

        if not plan:
            missing = [k for k in ("guest_profile", "discovered_options", "current_plan") if k not in state_keys]
            logger.warning(
                "No current_plan in session state (missing keys: %s). "
                "route_planner_agent likely skipped save_day_plan.",
                missing,
            )

        # Fallback: try to parse JSON from the last text output
        if not plan and last_text:
            plan = _try_parse_plan_from_text(last_text)
            if plan:
                logger.info("Extracted plan from text output (fallback)")

        if not plan:
            return {
                "day_plan": None,
                "message": last_text,
                "error": "Agent did not produce a structured day plan",
            }

        return {"day_plan": _transform_plan_for_frontend(plan)}

    except Exception as e:
        logger.exception("Error running concierge orchestrator")
        raise HTTPException(status_code=500, detail=str(e))


