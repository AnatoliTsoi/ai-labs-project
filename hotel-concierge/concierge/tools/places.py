"""Google Places API wrapper.

Phase 1: Uses mock data so the agent runs without a real API key.
Phase 2: Replace _call_places_api with real httpx calls.
"""

import uuid
from google.adk.tools import ToolContext

from concierge.models.discovered_option import DiscoveredOption


# ---------------------------------------------------------------------------
# Mock data helpers
# ---------------------------------------------------------------------------

def _make_mock_options(
    query: str,
    lat: float,
    lng: float,
    count: int = 5,
) -> list[dict]:
    """Return mock place data shaped like Places API (New) responses."""
    categories = ["restaurant", "attraction", "cafe", "museum", "park"]
    templates = [
        {"name": f"Le Bistro {query[:4].title()}", "category": "restaurant",
         "rating": 4.5, "price_level": 2},
        {"name": f"Café {query[:3].title()} Modern", "category": "cafe",
         "rating": 4.2, "price_level": 1},
        {"name": f"Museum of {query[:5].title()} Arts", "category": "museum",
         "rating": 4.7, "price_level": 2},
        {"name": f"{query[:4].title()} City Park", "category": "park",
         "rating": 4.3, "price_level": 1},
        {"name": f"Restaurant {query[:3].title()} Fusion", "category": "restaurant",
         "rating": 4.1, "price_level": 3},
    ]
    results = []
    for i, tmpl in enumerate(templates[:count]):
        results.append({
            "place_id": str(uuid.uuid4()),
            "name": tmpl["name"],
            "category": tmpl["category"],
            "rating": tmpl["rating"],
            "price_level": tmpl["price_level"],
            "address": f"{i * 10 + 1} Sample Street",
            "lat": lat + i * 0.002,
            "lng": lng + i * 0.002,
            "opening_hours": ["Mon-Sun: 08:00-22:00"],
            "source": "places_api",
        })
    return results


# ---------------------------------------------------------------------------
# ADK tool functions — called by Discovery Agent
# ---------------------------------------------------------------------------

def search_nearby_places(
    query: str,
    latitude: float,
    longitude: float,
    radius_meters: int = 5000,
    tool_context: ToolContext = None,
) -> dict:
    """Search for places near a location using Google Places API.

    Args:
        query: Type of place or keyword (e.g. "restaurant", "museum").
        latitude: Search center latitude.
        longitude: Search center longitude.
        radius_meters: Search radius in meters (default 5000).

    Returns:
        Dict with "places" list of place data.
    """
    # TODO Phase 2: Replace with real Places API (New) searchNearby call
    # POST https://places.googleapis.com/v1/places:searchNearby
    mock_results = _make_mock_options(query, latitude, longitude)
    return {"places": mock_results, "status": "mock"}


def get_place_details(
    place_id: str,
    tool_context: ToolContext = None,
) -> dict:
    """Fetch detailed information about a specific place.

    Args:
        place_id: The unique identifier for the place.

    Returns:
        Dict with detailed place information.
    """
    # TODO Phase 2: Replace with real Places API (New) getPlace call
    # GET https://places.googleapis.com/v1/places/{place_id}
    return {
        "place_id": place_id,
        "name": "Sample Place",
        "opening_hours": ["Mon-Sun: 09:00-21:00"],
        "reviews_summary": "Highly rated by recent visitors.",
        "status": "mock",
    }


def save_discovered_options(
    options: list[dict],
    tool_context: ToolContext,
) -> str:
    """Persist scored discovery results to session state.

    Args:
        options: List of discovered option dicts.

    Returns:
        Confirmation message.
    """
    tool_context.state["discovered_options"] = options
    return f"Saved {len(options)} discovered options to session."
