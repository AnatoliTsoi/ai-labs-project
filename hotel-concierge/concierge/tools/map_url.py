"""Generate shareable Google Maps multi-stop URLs — pure functions."""

from urllib.parse import urlencode

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


def generate_place_url(place_id: str) -> str:
    """Deep-link to a specific Google Maps place."""
    params = urlencode({"query_place_id": place_id, "query": "place"})
    return f"https://www.google.com/maps/search/?{params}"
