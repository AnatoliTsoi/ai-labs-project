"""Generate shareable Google Maps multi-stop URLs — pure functions."""

import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

from concierge.config.settings import get_settings
from concierge.models.day_plan import ItineraryStop

_MAPS_BASE = "https://www.google.com/maps/dir/"


def generate_multi_stop_map_url(
    stops: list[ItineraryStop],
    hotel_lat: float,
    hotel_lng: float,
) -> str:
    """
    Build a Google Maps directions URL with the hotel as origin and all
    itinerary stops as waypoints, returning to the hotel.

    Args:
        stops: Ordered itinerary stops.
        hotel_lat: Hotel latitude (start/end point).
        hotel_lng: Hotel longitude (start/end point).

    Returns:
        Shareable Google Maps URL string.
    """
    if not stops:
        return f"{_MAPS_BASE}{hotel_lat},{hotel_lng}"

    waypoints = [f"{hotel_lat},{hotel_lng}"]
    for stop in stops:
        lat, lng = stop.place.lat_lng
        waypoints.append(f"{lat},{lng}")
    waypoints.append(f"{hotel_lat},{hotel_lng}")  # return to hotel

    # Google Maps accepts slash-separated coords
    return _MAPS_BASE + "/".join(waypoints)


def generate_map_url_from_stops_dict(stops: list[dict]) -> str:
    """ADK tool: build a Google Maps directions URL from a list of stop dicts.

    Hotel coordinates are read from ``HOTEL_LAT`` / ``HOTEL_LNG`` env vars
    (via settings). Each dict must contain a ``lat_lng`` key with
    ``[lat, lng]`` values. Returns an empty string if the stops list is
    malformed.

    Args:
        stops: Ordered list of stop dicts, each with a ``lat_lng`` field.

    Returns:
        Shareable Google Maps URL string, or empty string on error.
    """
    try:
        settings = get_settings()
        hotel_lat = settings.hotel_lat
        hotel_lng = settings.hotel_lng
        waypoints = [f"{hotel_lat},{hotel_lng}"]
        for stop in stops:
            place = stop.get("place", stop)
            lat_lng = place.get("lat_lng")
            if not lat_lng or len(lat_lng) < 2:
                continue
            waypoints.append(f"{lat_lng[0]},{lat_lng[1]}")
        waypoints.append(f"{hotel_lat},{hotel_lng}")
        return _MAPS_BASE + "/".join(waypoints)
    except Exception as exc:
        logger.warning("generate_map_url_from_stops_dict failed: %s", exc, exc_info=True)
        return ""


def generate_place_url(place_id: str) -> str:
    """Deep-link to a specific Google Maps place."""
    params = urlencode({"query_place_id": place_id, "query": "place"})
    return f"https://www.google.com/maps/search/?{params}"
