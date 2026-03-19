"""Google Places API (New) — Text Search & Place Details.

Uses the Places API (New) REST endpoints:
- POST https://places.googleapis.com/v1/places:searchText
- GET  https://places.googleapis.com/v1/places/{place_id}
"""

import asyncio
import logging
import math
import os
from concurrent.futures import ThreadPoolExecutor

import httpx
from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)

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
# Enrichment helpers — deterministic scoring for fields the LLM can't provide
# ---------------------------------------------------------------------------

# Place category keywords that conflict with dietary restrictions
_DIETARY_CONFLICTS: dict[str, set[str]] = {
    "vegan": {"steakhouse", "burger", "seafood", "barbecue", "sushi", "ramen", "meat"},
    "vegetarian": {"steakhouse", "burger", "barbecue", "meat"},
    "halal": {"bar", "brewery", "pub", "wine", "sake"},
    "kosher": {"bar", "brewery", "pub", "seafood"},
}

# Guest interest keywords → place category keywords
_INTEREST_TO_CATEGORIES: dict[str, set[str]] = {
    "art": {"art_gallery", "museum", "art", "gallery"},
    "history": {"museum", "historical", "monument", "church", "cathedral", "palace"},
    "nature": {"park", "garden", "nature_reserve", "botanical"},
    "nightlife": {"bar", "night_club", "brewery", "cocktail", "lounge"},
    "local-food": {"restaurant", "food", "market", "cafe", "bistro", "brasserie"},
    "shopping": {"shopping_mall", "clothing_store", "market", "shop", "boutique"},
    "sports": {"sports", "gym", "stadium", "arena"},
    "music": {"music_venue", "concert_hall", "jazz", "live_music"},
}


def _dietary_compatibility(raw: dict, restrictions: list[str]) -> float:
    """Return 0.0 if place conflicts with any restriction, 0.8 if uncertain, 1.0 if clear."""
    if not restrictions:
        return 1.0
    text = ((raw.get("category") or "") + " " + raw.get("name", "")).lower()
    for restriction in restrictions:
        conflicts = _DIETARY_CONFLICTS.get(restriction.lower(), set())
        if any(kw in text for kw in conflicts):
            return 0.0
    return 0.8  # restrictions present but no detected conflict


def _interest_match(raw: dict, interests: list[str]) -> float:
    """Return 1.0 if category matches any guest interest, 0.5 otherwise."""
    if not interests:
        return 0.5
    category = (raw.get("category") or "").lower()
    for interest in interests:
        matched = _INTEREST_TO_CATEGORIES.get(interest.lower(), set())
        if any(kw in category for kw in matched):
            return 1.0
    return 0.5


def _walking_minutes(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    """Approximate walking time in minutes via haversine at 5 km/h."""
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    km = 6371 * 2 * math.asin(math.sqrt(a))
    return max(1, int(km / 5 * 60))


def _google_headers(field_mask: str) -> dict:
    return {
        "X-Goog-Api-Key": os.environ.get("GOOGLE_API_KEY", ""),
        "X-Goog-FieldMask": field_mask,
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# ADK tool functions — called by Discovery Agent
# ---------------------------------------------------------------------------

async def search_nearby_places(
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
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                _TEXT_SEARCH_URL,
                json=body,
                headers=_google_headers(_FIELD_MASK),
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


async def get_place_details(
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
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                url,
                headers=_google_headers(_DETAILS_FIELD_MASK),
            )
        resp.raise_for_status()
        raw = resp.json()

        result = _parse_place(raw)
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
    """Enrich, score, filter, and persist discovered options to session state.

    Enriches each raw Places API dict with computed fields (dietary_compatibility,
    interest_match, travel_time_from_hotel), then scores and filters using the
    calibrated scoring weights before saving.

    Args:
        options: List of raw place dicts from search_nearby_places.

    Returns:
        Confirmation message.
    """
    from concierge.config.scoring_weights import DEFAULT_WEIGHTS
    from concierge.config.settings import get_settings
    from concierge.models.discovered_option import DiscoveredOption
    from concierge.models.guest_profile import GuestProfile
    from concierge.tools.scoring import score_and_filter_options

    settings = get_settings()
    profile_dict = tool_context.state.get("guest_profile", {})
    restrictions = profile_dict.get("dietary_restrictions", [])
    interests = profile_dict.get("interests", [])

    enriched = []
    for raw in options:
        lat = raw.get("lat", settings.hotel_lat)
        lng = raw.get("lng", settings.hotel_lng)
        enriched.append(
            DiscoveredOption.from_dict({
                **raw,
                "lat_lng": [lat, lng],
                "dietary_compatibility": _dietary_compatibility(raw, restrictions),
                "interest_match": _interest_match(raw, interests),
                "travel_time_from_hotel": _walking_minutes(
                    settings.hotel_lat, settings.hotel_lng, lat, lng
                ),
                "booking_available": raw.get("booking_available", False),
            })
        )

    if profile_dict:
        profile = GuestProfile.from_dict(profile_dict)
        scored = score_and_filter_options(enriched, profile, DEFAULT_WEIGHTS)
    else:
        scored = enriched

    result = [o.to_dict() for o in scored]
    tool_context.state["discovered_options"] = result
    logger.info(
        "Saved %d options (scored/filtered from %d raw results)", len(result), len(options)
    )
    return f"Saved {len(result)} discovered options to session (filtered from {len(options)})."


def _search_single(query: str, lat: float, lng: float, radius: int) -> list[dict]:
    """Run a single text search (blocking). Used by batch_search_places."""
    body = {
        "textQuery": query.strip(),
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": float(radius),
            }
        },
        "maxResultCount": 5,
        "languageCode": "en",
    }
    try:
        resp = httpx.post(
            _TEXT_SEARCH_URL,
            json=body,
            headers=_google_headers(_FIELD_MASK),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        places = [_parse_place(p) for p in data.get("places", [])]
        logger.info("Places API returned %d results for '%s'", len(places), query.strip())
        return places
    except Exception as e:
        logger.error("Places batch search failed for '%s': %s", query.strip(), e)
        return []


def batch_search_places(
    queries: str,
    latitude: float,
    longitude: float,
    radius_meters: int = 5000,
    tool_context: ToolContext = None,
) -> dict:
    """Search for multiple types of places in parallel (much faster).

    Args:
        queries: Comma-separated search queries, e.g. "vegan restaurant, art museum, park, cocktail bar".
        latitude: Search center latitude.
        longitude: Search center longitude.
        radius_meters: Search radius in meters (default 5000).

    Returns:
        Dict with "all_places" list of all results combined.
    """
    query_list = [q.strip() for q in queries.split(",") if q.strip()]
    logger.info("Batch searching %d queries in parallel: %s", len(query_list), query_list)

    all_places = []
    with ThreadPoolExecutor(max_workers=min(len(query_list), 6)) as executor:
        futures = [
            executor.submit(_search_single, q, latitude, longitude, radius_meters)
            for q in query_list
        ]
        for future in futures:
            all_places.extend(future.result())

    # Deduplicate by place_id
    seen = set()
    unique = []
    for p in all_places:
        if p["place_id"] not in seen:
            seen.add(p["place_id"])
            unique.append(p)

    logger.info("Batch search complete: %d unique places from %d queries", len(unique), len(query_list))
    return {"all_places": unique, "count": len(unique), "status": "ok"}
