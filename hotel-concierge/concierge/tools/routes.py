"""Google Routes API — compute travel time and distance.

Uses the Routes API REST endpoint:
- POST https://routes.googleapis.com/directions/v2:computeRoutes
"""

import logging
import os

import httpx
from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)

_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

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


def compute_route(
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
        resp = httpx.post(
            _COMPUTE_ROUTES_URL,
            json=body,
            headers={
                "X-Goog-Api-Key": _API_KEY,
                "X-Goog-FieldMask": _FIELD_MASK,
                "Content-Type": "application/json",
            },
            timeout=10,
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


def get_travel_time(
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
    result = compute_route(origin_lat, origin_lng, destination_lat, destination_lng, mode)
    return result["duration_minutes"]


def check_opening_hours(
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
    # Use Place Details API to get real opening hours
    url = f"https://places.googleapis.com/v1/places/{place_id}"
    try:
        resp = httpx.get(
            url,
            headers={
                "X-Goog-Api-Key": _API_KEY,
                "X-Goog-FieldMask": "currentOpeningHours",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        is_open = data.get("currentOpeningHours", {}).get("openNow", True)
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
