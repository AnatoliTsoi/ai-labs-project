"""Google Places API (New) — Text Search & Place Details.

Uses the Places API (New) REST endpoints:
- POST https://places.googleapis.com/v1/places:searchText
- GET  https://places.googleapis.com/v1/places/{place_id}
"""

import logging
import os

import httpx
from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)


def _get_api_key() -> str:
    return os.environ.get("GOOGLE_API_KEY", "")

_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
_PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places"

_FIELD_MASK = (
    "places.id,"
    "places.displayName,"
    "places.formattedAddress,"
    "places.location,"
    "places.rating,"
    "places.priceLevel,"
    "places.currentOpeningHours,"
    "places.primaryType,"
    "places.websiteUri"
)

_DETAILS_FIELD_MASK = (
    "id,displayName,formattedAddress,location,rating,"
    "priceLevel,currentOpeningHours,primaryType,websiteUri,"
    "reviews,editorialSummary"
)


def _parse_price_level(raw: str | None) -> int:
    """Convert API price level string to int 1-4."""
    mapping = {
        "PRICE_LEVEL_FREE": 0,
        "PRICE_LEVEL_INEXPENSIVE": 1,
        "PRICE_LEVEL_MODERATE": 2,
        "PRICE_LEVEL_EXPENSIVE": 3,
        "PRICE_LEVEL_VERY_EXPENSIVE": 4,
    }
    return mapping.get(raw or "", 2)


def _parse_place(raw: dict) -> dict:
    """Normalise a Places API (New) result into our internal shape."""
    location = raw.get("location", {})
    opening_hours = raw.get("currentOpeningHours", {})
    weekday_text = opening_hours.get("weekdayDescriptions", [])

    return {
        "place_id": raw.get("id", ""),
        "name": raw.get("displayName", {}).get("text", "Unknown"),
        "category": raw.get("primaryType", "place"),
        "rating": raw.get("rating", 0),
        "price_level": _parse_price_level(raw.get("priceLevel")),
        "address": raw.get("formattedAddress", ""),
        "lat": location.get("latitude", 0),
        "lng": location.get("longitude", 0),
        "opening_hours": weekday_text[:3] if weekday_text else ["Hours not available"],
        "website": raw.get("websiteUri", ""),
        "source": "places_api",
    }


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
        query: Type of place or keyword (e.g. "vegan restaurant", "art museum").
        latitude: Search center latitude.
        longitude: Search center longitude.
        radius_meters: Search radius in meters (default 5000).

    Returns:
        Dict with "places" list of place data.
    """
    body = {
        "textQuery": query,
        "locationBias": {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": float(radius_meters),
            }
        },
        "maxResultCount": 5,
        "languageCode": "en",
    }

    try:
        resp = httpx.post(
            _TEXT_SEARCH_URL,
            json=body,
            headers={
                "X-Goog-Api-Key": _get_api_key(),
                "X-Goog-FieldMask": _FIELD_MASK,
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        places = [_parse_place(p) for p in data.get("places", [])]
        logger.info("Places API returned %d results for '%s'", len(places), query)
        return {"places": places, "status": "ok"}

    except httpx.HTTPStatusError as e:
        logger.error("Places API error %s: %s", e.response.status_code, e.response.text)
        return {"places": [], "status": "error", "error": str(e)}
    except Exception as e:
        logger.error("Places API request failed: %s", e)
        return {"places": [], "status": "error", "error": str(e)}


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
    url = f"{_PLACE_DETAILS_URL}/{place_id}"

    try:
        resp = httpx.get(
            url,
            headers={
                "X-Goog-Api-Key": _get_api_key(),
                "X-Goog-FieldMask": _DETAILS_FIELD_MASK,
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        resp.raise_for_status()
        raw = resp.json()

        result = _parse_place(raw)
        # Add extra detail fields
        editorial = raw.get("editorialSummary", {})
        result["reviews_summary"] = editorial.get("text", "No editorial summary available.")
        return result

    except httpx.HTTPStatusError as e:
        logger.error("Place Details error %s: %s", e.response.status_code, e.response.text)
        return {"place_id": place_id, "error": str(e)}
    except Exception as e:
        logger.error("Place Details request failed: %s", e)
        return {"place_id": place_id, "error": str(e)}


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
