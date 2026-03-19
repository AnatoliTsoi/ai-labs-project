"""Unit tests for tool functions (places, routes, weather, state_tools)."""

from unittest.mock import MagicMock

import pytest

from concierge.tools.guest_history import get_guest_history
from concierge.tools.places import (
    _make_mock_options,
    get_place_details,
    save_discovered_options,
    search_nearby_places,
)
from concierge.tools.routes import check_opening_hours, compute_route, get_travel_time
from concierge.tools.state_tools import (
    KEY_CURRENT_PLAN,
    KEY_DISCOVERED_OPTIONS,
    KEY_FEEDBACK_HISTORY,
    KEY_GUEST_PROFILE,
    KEY_PLAN_APPROVED,
    KEY_REFINEMENT_SCOPE,
    record_feedback,
    save_day_plan,
    save_guest_profile,
)
from concierge.tools.weather import get_weather_forecast


def _mock_ctx(initial_state: dict | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.state = initial_state or {}
    ctx.actions = MagicMock()
    return ctx


# ---------------------------------------------------------------------------
# Places tools
# ---------------------------------------------------------------------------

class TestMakeMockOptions:
    def test_returns_requested_count(self) -> None:
        results = _make_mock_options("restaurant", 48.8, 2.3, count=3)
        assert len(results) == 3

    def test_all_have_required_fields(self) -> None:
        results = _make_mock_options("cafe", 48.8, 2.3, count=2)
        for r in results:
            assert "place_id" in r
            assert "name" in r
            assert "rating" in r
            assert "lat" in r and "lng" in r


class TestSearchNearbyPlaces:
    def test_returns_places_key(self) -> None:
        result = search_nearby_places("restaurant", 48.8, 2.3)
        assert "places" in result

    def test_places_is_list(self) -> None:
        result = search_nearby_places("museum", 48.8, 2.3)
        assert isinstance(result["places"], list)

    def test_default_radius_accepted(self) -> None:
        result = search_nearby_places("park", 48.8, 2.3, radius_meters=5000)
        assert result["places"]


class TestGetPlaceDetails:
    def test_returns_place_id(self) -> None:
        result = get_place_details("place-001")
        assert result["place_id"] == "place-001"

    def test_returns_opening_hours(self) -> None:
        result = get_place_details("place-002")
        assert "opening_hours" in result


class TestSaveDiscoveredOptions:
    def test_saves_to_state(self) -> None:
        ctx = _mock_ctx()
        options = [{"place_id": "p1", "name": "Café"}]
        msg = save_discovered_options(options, ctx)
        assert ctx.state["discovered_options"] == options
        assert "1" in msg


# ---------------------------------------------------------------------------
# Routes tools
# ---------------------------------------------------------------------------

class TestComputeRoute:
    def test_returns_duration_and_distance(self) -> None:
        result = compute_route(48.85, 2.35, 48.86, 2.36)
        assert "duration_minutes" in result
        assert "distance_meters" in result

    def test_walk_is_slower_than_drive(self) -> None:
        walk = compute_route(48.0, 2.0, 48.1, 2.1, mode="walk")
        drive = compute_route(48.0, 2.0, 48.1, 2.1, mode="drive")
        assert walk["duration_minutes"] >= drive["duration_minutes"]

    def test_same_point_is_short(self) -> None:
        result = compute_route(48.0, 2.0, 48.0, 2.0, mode="walk")
        assert result["duration_minutes"] >= 2  # minimum floor


class TestGetTravelTime:
    def test_returns_int(self) -> None:
        result = get_travel_time(48.0, 2.0, 48.1, 2.1)
        assert isinstance(result, int)

    def test_positive_duration(self) -> None:
        result = get_travel_time(48.0, 2.0, 48.05, 2.05)
        assert result > 0


class TestCheckOpeningHours:
    def test_midday_is_open(self) -> None:
        result = check_opening_hours("p-001", "12:00")
        assert result["is_open"] is True

    def test_midnight_is_closed(self) -> None:
        result = check_opening_hours("p-001", "00:00")
        assert result["is_open"] is False

    def test_returns_next_open_when_closed(self) -> None:
        result = check_opening_hours("p-001", "00:00")
        assert result["next_open"] is not None

    def test_next_open_none_when_open(self) -> None:
        result = check_opening_hours("p-001", "12:00")
        assert result["next_open"] is None


# ---------------------------------------------------------------------------
# Weather tool
# ---------------------------------------------------------------------------

class TestGetWeatherForecast:
    def test_returns_condition(self) -> None:
        result = get_weather_forecast(48.8, 2.3, "2026-03-19")
        assert "condition" in result

    def test_returns_temperature(self) -> None:
        result = get_weather_forecast(48.8, 2.3, "2026-03-19")
        assert "temperature_celsius" in result

    def test_returns_rain_probability(self) -> None:
        result = get_weather_forecast(48.8, 2.3, "2026-03-19")
        assert 0.0 <= result["rain_probability"] <= 1.0


# ---------------------------------------------------------------------------
# Guest history tool
# ---------------------------------------------------------------------------

class TestGetGuestHistory:
    def test_returns_guest_id(self) -> None:
        result = get_guest_history("G-001")
        assert result["guest_id"] == "G-001"

    def test_returns_past_stays(self) -> None:
        result = get_guest_history("G-001")
        assert "past_stays" in result


# ---------------------------------------------------------------------------
# State tools
# ---------------------------------------------------------------------------

class TestSaveGuestProfile:
    def test_writes_to_state(self) -> None:
        ctx = _mock_ctx()
        msg = save_guest_profile(
            guest_id="G-001",
            dietary_restrictions=["vegan"],
            interests=["art"],
            mobility="full",
            budget_level="moderate",
            pace="moderate",
            party_composition="solo",
            start_time="09:00",
            end_time="22:00",
            location_context="Hotel ABC",
            special_requests=[],
            tool_context=ctx,
        )
        assert KEY_GUEST_PROFILE in ctx.state
        assert ctx.state[KEY_GUEST_PROFILE]["guest_id"] == "G-001"
        assert "G-001" in msg

    def test_stores_dietary_as_list(self) -> None:
        ctx = _mock_ctx()
        save_guest_profile(
            guest_id="G-002",
            dietary_restrictions=["halal", "nut-free"],
            interests=[],
            mobility="full",
            budget_level="budget",
            pace="relaxed",
            party_composition="family_young_kids",
            start_time="10:00",
            end_time="20:00",
            location_context="Hotel XYZ",
            special_requests=["slow pace"],
            tool_context=ctx,
        )
        stored = ctx.state[KEY_GUEST_PROFILE]
        assert "halal" in stored["dietary_restrictions"]


class TestSaveDayPlan:
    def test_writes_plan_to_state(self) -> None:
        ctx = _mock_ctx()
        plan = {"date": "2026-03-19", "stops": [{"order": 1}]}
        msg = save_day_plan(plan, ctx)
        assert ctx.state[KEY_CURRENT_PLAN] == plan
        assert "1" in msg


class TestRecordFeedback:
    def test_approve_sets_plan_approved(self) -> None:
        ctx = _mock_ctx()
        record_feedback("approve", "Looks great", None, ctx)
        assert ctx.state[KEY_PLAN_APPROVED] is True

    def test_approve_escalates(self) -> None:
        ctx = _mock_ctx()
        record_feedback("approve", "", None, ctx)
        assert ctx.actions.escalate is True

    def test_feedback_appended_to_history(self) -> None:
        ctx = _mock_ctx()
        record_feedback("swap_stop", "Change lunch", 2, ctx)
        history = ctx.state[KEY_FEEDBACK_HISTORY]
        assert len(history) == 1
        assert history[0]["action"] == "swap_stop"

    def test_multiple_feedbacks_accumulated(self) -> None:
        ctx = _mock_ctx()
        record_feedback("change_pace", "More relaxed", None, ctx)
        record_feedback("swap_stop", "Swap stop 1", 1, ctx)
        assert len(ctx.state[KEY_FEEDBACK_HISTORY]) == 2

    @pytest.mark.parametrize("action,expected_scope", [
        ("swap_stop", "route_only"),
        ("change_time", "route_only"),
        ("remove_stop", "route_only"),
        ("change_pace", "route_only"),
        ("add_activity", "discovery_narrow"),
        ("restart", "full"),
    ])
    def test_refinement_scope_set_correctly(self, action: str, expected_scope: str) -> None:
        ctx = _mock_ctx()
        record_feedback(action, "", None, ctx)
        assert ctx.state[KEY_REFINEMENT_SCOPE] == expected_scope
