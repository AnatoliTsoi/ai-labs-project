"""Unit tests for the scoring pure functions."""

import pytest

from concierge.config.scoring_weights import ScoringWeights
from concierge.models.discovered_option import DiscoveredOption
from concierge.models.guest_profile import GuestProfile, TimeWindow
from concierge.tools.scoring import (
    _normalize_rating,
    _price_match_score,
    _proximity_score,
    score_and_filter_options,
    score_option,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_option(**overrides) -> DiscoveredOption:
    defaults = dict(
        place_id="p-001",
        name="Test Place",
        category="restaurant",
        rating=4.0,
        price_level=2,
        address="1 Test St",
        lat_lng=(48.0, 2.0),
        opening_hours=("Mon-Sun: 09:00-22:00",),
        dietary_compatibility=1.0,
        interest_match=1.0,
        travel_time_from_hotel=10,
        booking_available=False,
        source="places_api",
    )
    return DiscoveredOption(**{**defaults, **overrides})


def _make_profile(**overrides) -> GuestProfile:
    defaults = dict(
        guest_id="G-001",
        dietary_restrictions=(),
        interests=("art",),
        mobility="full",
        budget_level="moderate",
        pace="moderate",
        party_composition="solo",
        time_available=TimeWindow("09:00", "22:00"),
        location_context="hotel",
        special_requests=(),
    )
    return GuestProfile(**{**defaults, **overrides})


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestNormalizeRating:
    def test_min_rating_is_zero(self) -> None:
        assert _normalize_rating(1.0) == 0.0

    def test_max_rating_is_one(self) -> None:
        assert _normalize_rating(5.0) == 1.0

    def test_midpoint(self) -> None:
        assert _normalize_rating(3.0) == pytest.approx(0.5)

    def test_clamps_below_min(self) -> None:
        assert _normalize_rating(0.0) == 0.0

    def test_clamps_above_max(self) -> None:
        assert _normalize_rating(6.0) == 1.0


class TestProximityScore:
    def test_zero_minutes_is_one(self) -> None:
        assert _proximity_score(0) == 1.0

    def test_sixty_minutes_is_zero(self) -> None:
        assert _proximity_score(60) == 0.0

    def test_beyond_sixty_is_clamped(self) -> None:
        assert _proximity_score(120) == 0.0

    def test_thirty_minutes_is_half(self) -> None:
        assert _proximity_score(30) == pytest.approx(0.5)


class TestPriceMatch:
    def test_exact_match_budget(self) -> None:
        assert _price_match_score(1, "budget") == 1.0

    def test_exact_match_moderate(self) -> None:
        assert _price_match_score(2, "moderate") == 1.0

    def test_exact_match_luxury(self) -> None:
        assert _price_match_score(4, "luxury") == 1.0

    def test_one_level_off(self) -> None:
        assert _price_match_score(3, "moderate") == pytest.approx(0.75)

    def test_two_levels_off(self) -> None:
        assert _price_match_score(4, "budget") == pytest.approx(0.25)

    def test_clamps_at_zero(self) -> None:
        assert _price_match_score(4, "budget") >= 0.0


# ---------------------------------------------------------------------------
# score_option tests
# ---------------------------------------------------------------------------

class TestScoreOption:
    def test_perfect_option_scores_high(self) -> None:
        option = _make_option(
            rating=5.0,
            price_level=2,
            dietary_compatibility=1.0,
            interest_match=1.0,
            travel_time_from_hotel=0,
        )
        profile = _make_profile(budget_level="moderate")
        score = score_option(option, profile)
        assert score >= 0.9

    def test_poor_option_scores_low(self) -> None:
        option = _make_option(
            rating=1.0,
            price_level=4,
            dietary_compatibility=0.5,
            interest_match=0.1,
            travel_time_from_hotel=59,
        )
        profile = _make_profile(budget_level="budget")
        score = score_option(option, profile)
        assert score < 0.3

    def test_score_is_between_zero_and_one(self) -> None:
        option = _make_option()
        profile = _make_profile()
        score = score_option(option, profile)
        assert 0.0 <= score <= 1.0

    def test_custom_weights_applied(self) -> None:
        option_a = _make_option(interest_match=1.0, rating=1.0)
        option_b = _make_option(interest_match=0.0, rating=5.0)
        profile = _make_profile()

        # Weight interest heavily
        w_interest = ScoringWeights(
            interest_match=0.90,
            rating_normalized=0.05,
            dietary_compatibility=0.02,
            proximity_score=0.02,
            price_match=0.01,
        )
        score_a = score_option(option_a, profile, w_interest)
        score_b = score_option(option_b, profile, w_interest)
        assert score_a > score_b


# ---------------------------------------------------------------------------
# score_and_filter_options tests
# ---------------------------------------------------------------------------

class TestScoreAndFilterOptions:
    def test_filters_dietary_incompatible(self) -> None:
        incompatible = _make_option(dietary_compatibility=0.3)
        compatible = _make_option(dietary_compatibility=0.8)
        profile = _make_profile()
        result = score_and_filter_options([incompatible, compatible], profile)
        assert incompatible not in result
        assert compatible in result

    def test_filters_zero_interest_match(self) -> None:
        no_interest = _make_option(interest_match=0.0)
        some_interest = _make_option(interest_match=0.5)
        profile = _make_profile()
        result = score_and_filter_options([no_interest, some_interest], profile)
        assert no_interest not in result

    def test_returns_sorted_by_score_descending(self) -> None:
        options = [
            _make_option(place_id="low", rating=1.5, interest_match=0.2),
            _make_option(place_id="high", rating=4.8, interest_match=0.9),
            _make_option(place_id="mid", rating=3.5, interest_match=0.6),
        ]
        profile = _make_profile()
        result = score_and_filter_options(options, profile)
        scores = [score_option(o, profile) for o in result]
        assert scores == sorted(scores, reverse=True)

    def test_respects_top_n(self) -> None:
        options = [_make_option(place_id=str(i)) for i in range(30)]
        profile = _make_profile()
        result = score_and_filter_options(options, profile, top_n=10)
        assert len(result) <= 10

    def test_empty_input_returns_empty(self) -> None:
        result = score_and_filter_options([], _make_profile())
        assert result == []


# ---------------------------------------------------------------------------
# ScoringWeights validation
# ---------------------------------------------------------------------------

class TestScoringWeights:
    def test_default_weights_sum_to_one(self) -> None:
        from concierge.config.scoring_weights import DEFAULT_WEIGHTS
        total = (
            DEFAULT_WEIGHTS.interest_match
            + DEFAULT_WEIGHTS.rating_normalized
            + DEFAULT_WEIGHTS.dietary_compatibility
            + DEFAULT_WEIGHTS.proximity_score
            + DEFAULT_WEIGHTS.price_match
        )
        assert total == pytest.approx(1.0)

    def test_invalid_weights_raise(self) -> None:
        with pytest.raises(ValueError, match="sum to 1.0"):
            ScoringWeights(
                interest_match=0.5,
                rating_normalized=0.5,
                dietary_compatibility=0.5,
                proximity_score=0.5,
                price_match=0.5,
            )
