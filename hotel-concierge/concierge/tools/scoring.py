"""Pure scoring functions — no side effects, fully unit-testable."""

from concierge.config.api_limits import PLACES_LIMITS
from concierge.config.scoring_weights import DEFAULT_WEIGHTS, ScoringWeights
from concierge.models.discovered_option import DiscoveredOption
from concierge.models.guest_profile import GuestProfile

_BUDGET_TO_PRICE_LEVEL: dict[str, int] = {
    "budget": 1,
    "moderate": 2,
    "luxury": 4,
}

_MAX_PROXIMITY_MINUTES = 60.0  # anything beyond 60 min scores 0


def _normalize_rating(rating: float) -> float:
    """Map 1-5 star rating to 0-1."""
    return max(0.0, min(1.0, (rating - 1.0) / 4.0))


def _proximity_score(travel_time_minutes: int) -> float:
    """Closer is better. Linear decay to 0 at 60 min."""
    return max(0.0, 1.0 - travel_time_minutes / _MAX_PROXIMITY_MINUTES)


def _price_match_score(price_level: int, budget_level: str) -> float:
    """Exact match = 1.0; each level off = -0.25."""
    target = _BUDGET_TO_PRICE_LEVEL.get(budget_level, 2)
    diff = abs(price_level - target)
    return max(0.0, 1.0 - diff * 0.25)


def score_option(
    option: DiscoveredOption,
    profile: GuestProfile,
    weights: ScoringWeights = DEFAULT_WEIGHTS,
) -> float:
    """
    Compute a composite relevance score for a single discovered option
    against a guest profile. Returns a value in [0.0, 1.0].
    """
    composite = (
        weights.interest_match * option.interest_match
        + weights.rating_normalized * _normalize_rating(option.rating)
        + weights.dietary_compatibility * option.dietary_compatibility
        + weights.proximity_score * _proximity_score(option.travel_time_from_hotel)
        + weights.price_match * _price_match_score(option.price_level, profile.budget_level)
    )
    return round(min(1.0, max(0.0, composite)), 4)


def score_and_filter_options(
    options: list[DiscoveredOption],
    profile: GuestProfile,
    weights: ScoringWeights = DEFAULT_WEIGHTS,
    top_n: int = PLACES_LIMITS.max_candidate_options,
) -> list[DiscoveredOption]:
    """
    Score all options, filter out incompatible ones, return top N sorted
    by composite score descending.

    Filtered out:
    - dietary_compatibility < 0.5  (hard dietary conflict)
    - interest_match == 0.0        (zero interest alignment)
    """
    compatible = [
        opt for opt in options
        if opt.dietary_compatibility >= 0.5 and opt.interest_match > 0.0
    ]
    scored = sorted(compatible, key=lambda o: score_option(o, profile, weights), reverse=True)
    return scored[:top_n]
