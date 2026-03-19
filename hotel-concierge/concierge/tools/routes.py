"""Google Routes API — compute travel time and distance.

Uses the Routes API REST endpoint:
- POST https://routes.googleapis.com/directions/v2:computeRoutes
"""

import datetime
import logging
import os

import httpx
from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)

_COMPUTE_ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

_FIELD_MASK = "routes.duration,routes.distanceMeters"

# Map our mode names → API travelMode enum values
_MODE_MAP = {
    "walk": "WALK",
    "walking": "WALK",
    "transit": "TRANSIT",
    "drive": "DRIVE",
    "driving": "DRIVE",
    "bicycle": "BICYCLE",
}


def _google_headers(field_mask: str) -> dict:
    return {
        "X-Goog-Api-Key": os.environ.get("GOOGLE_API_KEY", ""),
        "X-Goog-FieldMask": field_mask,
        "Content-Type": "application/json",
    }


async def compute_route(
    origin_lat: float,
    origin_lng: float,
    destination_lat: float,
    destination_lng: float,
    mode: str = "walk",
    tool_context: ToolContext = None,
) -> dict:
    """Compute travel time and distance between two points.

    Args:
        origin_lat: Origin latitude.
        origin_lng: Origin longitude.
        destination_lat: Destination latitude.
        destination_lng: Destination longitude.
        mode: Travel mode — "walk", "transit", or "drive".

    Returns:
        Dict with duration_minutes and distance_meters.
    """
    travel_mode = _MODE_MAP.get(mode.lower(), "WALK")

    body = {
        "origin": {
            "location": {
                "latLng": {"latitude": origin_lat, "longitude": origin_lng}
            }
        },
        "destination": {
            "location": {
                "latLng": {"latitude": destination_lat, "longitude": destination_lng}
            }
        },
        "travelMode": travel_mode,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                _COMPUTE_ROUTES_URL,
                json=body,
                headers=_google_headers(_FIELD_MASK),
            )
        resp.raise_for_status()
        data = resp.json()

        routes = data.get("routes", [])
        if not routes:
            logger.warning("Routes API returned no routes")
            return _fallback_compute(origin_lat, origin_lng, destination_lat, destination_lng, mode)

        route = routes[0]
        # Duration comes as "123s" string
        duration_str = route.get("duration", "0s")
        duration_seconds = int(duration_str.rstrip("s"))
        duration_minutes = max(1, duration_seconds // 60)
        distance_meters = route.get("distanceMeters", 0)

        return {
            "duration_minutes": duration_minutes,
            "distance_meters": distance_meters,
            "mode": mode,
            "status": "ok",
        }

    except httpx.HTTPStatusError as e:
        logger.error("Routes API error %s: %s", e.response.status_code, e.response.text)
        return _fallback_compute(origin_lat, origin_lng, destination_lat, destination_lng, mode)
    except Exception as e:
        logger.error("Routes API request failed: %s", e)
        return _fallback_compute(origin_lat, origin_lng, destination_lat, destination_lng, mode)


def _fallback_compute(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    mode: str,
) -> dict:
    """Rough estimate when the API call fails."""
    lat_diff = abs(dest_lat - origin_lat)
    lng_diff = abs(dest_lng - origin_lng)
    distance_deg = (lat_diff**2 + lng_diff**2) ** 0.5
    distance_meters = int(distance_deg * 111_000)
    speed = {"walk": 5, "transit": 25, "drive": 50}.get(mode, 5)
    duration_minutes = max(2, int((distance_meters / 1000) / speed * 60))
    return {
        "duration_minutes": duration_minutes,
        "distance_meters": distance_meters,
        "mode": mode,
        "status": "fallback",
    }


async def get_travel_time(
    origin_lat: float,
    origin_lng: float,
    destination_lat: float,
    destination_lng: float,
    mode: str = "walk",
    tool_context: ToolContext = None,
) -> int:
    """Get travel time in minutes between two points.

    Args:
        origin_lat: Origin latitude.
        origin_lng: Origin longitude.
        destination_lat: Destination latitude.
        destination_lng: Destination longitude.
        mode: Travel mode — "walk", "transit", or "drive".

    Returns:
        Estimated travel time in minutes.
    """
    result = await compute_route(origin_lat, origin_lng, destination_lat, destination_lng, mode)
    return result["duration_minutes"]


def _is_open_at(regular_hours: dict, arrival_time: str) -> bool:
    """Return True if a place is open at arrival_time on the current weekday.

    Uses regularOpeningHours.periods where day 0=Sunday … 6=Saturday.
    Returns True (assume open) when no period data is available.
    """
    periods = regular_hours.get("periods", [])
    if not periods:
        return True  # No schedule data → assume open

    try:
        hour, minute = (int(x) for x in arrival_time.split(":"))
    except (ValueError, AttributeError):
        return True

    arrival_min = hour * 60 + minute

    # Python weekday: 0=Mon … 6=Sun → Places API: 0=Sun, 1=Mon … 6=Sat
    api_day = (datetime.date.today().weekday() + 1) % 7

    for period in periods:
        open_info = period.get("open", {})
        close_info = period.get("close", {})
        if open_info.get("day") != api_day:
            continue
        open_min = open_info.get("hour", 0) * 60 + open_info.get("minute", 0)
        # A missing close means open 24 h from this period
        if not close_info:
            return True
        close_day = close_info.get("day", api_day)
        close_min = close_info.get("hour", 23) * 60 + close_info.get("minute", 59)
        if close_day != api_day:
            # Spans midnight — any time from open until EOD counts as open
            if arrival_min >= open_min:
                return True
        elif open_min <= arrival_min <= close_min:
            return True

    return False


async def check_opening_hours(
    place_id: str,
    arrival_time: str,
    tool_context: ToolContext = None,
) -> dict:
    """Check if a place is open at the planned arrival time.

    Args:
        place_id: Google Places place ID.
        arrival_time: Planned arrival in "HH:MM" format.

    Returns:
        Dict with is_open (bool) and next_open (str or None).
    """
    url = f"https://places.googleapis.com/v1/places/{place_id}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                url,
                headers=_google_headers("regularOpeningHours"),
            )
        resp.raise_for_status()
        data = resp.json()
        is_open = _is_open_at(data.get("regularOpeningHours", {}), arrival_time)
        return {
            "place_id": place_id,
            "arrival_time": arrival_time,
            "is_open": is_open,
            "status": "ok",
        }
    except Exception:
        # Fallback: assume open during typical hours
        hour = int(arrival_time.split(":")[0]) if ":" in arrival_time else 12
        return {
            "place_id": place_id,
            "arrival_time": arrival_time,
            "is_open": 8 <= hour <= 22,
            "next_open": "09:00" if hour < 8 else None,
            "status": "fallback",
        }
