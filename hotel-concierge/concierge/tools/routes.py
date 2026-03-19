"""Google Routes API wrapper.

Phase 1: Uses mock travel times so the agent runs without a real API key.
Phase 2: Replace with real Routes API calls.
"""

from google.adk.tools import ToolContext


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
    # TODO Phase 2: Replace with real Routes API call
    # POST https://routes.googleapis.com/directions/v2:computeRoutes
    lat_diff = abs(destination_lat - origin_lat)
    lng_diff = abs(destination_lng - origin_lng)
    distance_deg = (lat_diff**2 + lng_diff**2) ** 0.5
    distance_meters = int(distance_deg * 111_000)

    speed = {"walk": 5, "transit": 25, "drive": 50}.get(mode, 5)
    duration_minutes = max(2, int((distance_meters / 1000) / speed * 60))

    return {
        "duration_minutes": duration_minutes,
        "distance_meters": distance_meters,
        "mode": mode,
        "status": "mock",
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
    # TODO Phase 2: Fetch real hours from Place Details API
    hour = int(arrival_time.split(":")[0])
    is_open = 9 <= hour <= 21
    return {
        "place_id": place_id,
        "arrival_time": arrival_time,
        "is_open": is_open,
        "next_open": "09:00" if not is_open else None,
        "status": "mock",
    }
