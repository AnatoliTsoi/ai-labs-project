from dataclasses import dataclass


@dataclass(frozen=True)
class PlacesApiLimits:
    max_results_per_search: int = 20
    max_candidate_options: int = 20    # top N passed to Route Planner
    nearby_search_radius_meters: int = 5000
    # Field mask — only request what we need (reduces cost 30-50%)
    field_mask: tuple[str, ...] = (
        "places.id",
        "places.displayName",
        "places.rating",
        "places.priceLevel",
        "places.formattedAddress",
        "places.location",
        "places.regularOpeningHours",
        "places.primaryType",
    )


@dataclass(frozen=True)
class RoutesApiLimits:
    max_waypoints: int = 10


PLACES_LIMITS = PlacesApiLimits()
ROUTES_LIMITS = RoutesApiLimits()
