"""FastAPI REST server — bridges the React frontend to the ADK orchestrator."""

import logging
import uuid
from pathlib import Path

from dotenv import load_dotenv

# Load .env BEFORE any ADK imports so GOOGLE_API_KEY is in the environment
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from google.adk.runners import InMemoryRunner
from google.genai import types

from concierge.agents.orchestrator import build_concierge_orchestrator
from concierge.config.settings import get_settings
from concierge.tools.state_tools import KEY_CURRENT_PLAN, KEY_GUEST_PROFILE

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

    return {
        "date": plan.get("date", ""),
        "stops": transformed_stops,
        "total_travel_time": plan.get("total_travel_time", 0),
        "estimated_total_cost": plan.get("estimated_total_cost", ""),
        "weather_contingency": plan.get("weather_contingency", ""),
        "back_at_hotel_by": plan.get("back_at_hotel_by", ""),
        "map_url": plan.get("map_url"),
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

    message = types.UserContent(parts=[types.Part(text=profile_summary)])

    try:
        # Create session with pre-seeded guest profile in state
        session = await runner.session_service.create_session(
            app_name=settings.app_name,
            user_id=user_id,
            session_id=session_id,
            state={KEY_GUEST_PROFILE: profile_dict},
        )

        # Run the full orchestrator loop
        last_text = ""
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=message,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        last_text = part.text

        # Re-fetch session to get the latest state after the run
        session = await runner.session_service.get_session(
            app_name=settings.app_name,
            user_id=user_id,
            session_id=session.id,
        )

        plan = session.state.get(KEY_CURRENT_PLAN) if session else None

        if not plan:
            logger.warning("No current_plan in session state after run")
            return {
                "day_plan": None,
                "message": last_text,
                "error": "Agent did not produce a structured day plan",
            }

        return {"day_plan": _transform_plan_for_frontend(plan)}

    except Exception as e:
        logger.exception("Error running concierge orchestrator")
        raise HTTPException(status_code=500, detail=str(e))


