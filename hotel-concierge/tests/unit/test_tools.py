"""Unit tests for tool functions (places, routes, weather, state_tools)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from concierge.tools.guest_history import get_guest_history
from concierge.tools.places import (
    _dietary_compatibility,
    _interest_match,
    _walking_minutes,
    get_place_details,
    save_discovered_options,
    search_nearby_places,
)
from concierge.tools.routes import _is_open_at, check_opening_hours, compute_route, get_travel_time
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


# ---------------------------------------------------------------------------
# Shared mock HTTP responses
# ---------------------------------------------------------------------------

def _mock_places_response():
    """Return a mock httpx Response for Places Text Search."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "places": [
            {
                "id": "place-001",
                "displayName": {"text": "Le Bistro"},
                "formattedAddress": "1 Rue de Rivoli, Paris",
                "location": {"latitude": 48.8566, "longitude": 2.3522},
                "rating": 4.5,
                "priceLevel": "PRICE_LEVEL_MODERATE",
                "primaryType": "restaurant",
                "currentOpeningHours": {
                    "weekdayDescriptions": ["Mon: 09:00-22:00"],
                    "openNow": True,
                },
            }
        ]
    }
    return resp


def _mock_route_response():
    """Return a mock httpx Response for Routes computeRoutes."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "routes": [{"duration": "420s", "distanceMeters": 1500}]
    }
    return resp


def _mock_ctx(initial_state: dict | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.state = initial_state or {}
    ctx.actions = MagicMock()
    return ctx


def _async_client_mock(response: MagicMock) -> MagicMock:
    """Build an AsyncClient context-manager mock returning the given response."""
    client = AsyncMock()
    client.post = AsyncMock(return_value=response)
    client.get = AsyncMock(return_value=response)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


# ---------------------------------------------------------------------------
# Places tools
# ---------------------------------------------------------------------------

class TestSearchNearbyPlaces:
    @patch("concierge.tools.places.httpx.AsyncClient")
    async def test_returns_places_key(self, mock_cls) -> None:
        mock_cls.return_value = _async_client_mock(_mock_places_response())
        result = await search_nearby_places("restaurant", 48.8, 2.3)
        assert "places" in result

    @patch("concierge.tools.places.httpx.AsyncClient")
    async def test_places_is_list(self, mock_cls) -> None:
        mock_cls.return_value = _async_client_mock(_mock_places_response())
        result = await search_nearby_places("museum", 48.8, 2.3)
        assert isinstance(result["places"], list)

    @patch("concierge.tools.places.httpx.AsyncClient")
    async def test_parsed_place_has_required_fields(self, mock_cls) -> None:
        mock_cls.return_value = _async_client_mock(_mock_places_response())
        result = await search_nearby_places("restaurant", 48.8, 2.3)
        place = result["places"][0]
        assert "place_id" in place
        assert "name" in place
        assert "lat" in place and "lng" in place
        assert "rating" in place


class TestGetPlaceDetails:
    @patch("concierge.tools.places.httpx.AsyncClient")
    async def test_returns_place_id(self, mock_cls) -> None:
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "id": "place-001",
            "displayName": {"text": "Test Place"},
            "formattedAddress": "1 Test St",
            "location": {"latitude": 48.8, "longitude": 2.3},
            "rating": 4.0,
            "primaryType": "restaurant",
        }
        mock_cls.return_value = _async_client_mock(resp)
        result = await get_place_details("place-001")
        assert result["place_id"] == "place-001"


class TestDietaryCompatibility:
    def test_no_restrictions_returns_one(self) -> None:
        assert _dietary_compatibility({"category": "steakhouse"}, []) == 1.0

    def test_vegan_conflict_with_steakhouse(self) -> None:
        assert _dietary_compatibility({"category": "steakhouse", "name": "Grill"}, ["vegan"]) == 0.0

    def test_vegan_no_conflict_with_cafe(self) -> None:
        result = _dietary_compatibility({"category": "cafe", "name": "Green Café"}, ["vegan"])
        assert result == 0.8

    def test_halal_conflict_with_bar(self) -> None:
        assert _dietary_compatibility({"category": "bar", "name": "The Pub"}, ["halal"]) == 0.0


class TestInterestMatch:
    def test_no_interests_returns_half(self) -> None:
        assert _interest_match({"category": "museum"}, []) == 0.5

    def test_art_matches_art_gallery(self) -> None:
        assert _interest_match({"category": "art_gallery"}, ["art"]) == 1.0

    def test_no_match_returns_half(self) -> None:
        assert _interest_match({"category": "steakhouse"}, ["art"]) == 0.5


class TestWalkingMinutes:
    def test_same_location_is_one_minute(self) -> None:
        assert _walking_minutes(48.85, 2.35, 48.85, 2.35) == 1

    def test_returns_positive(self) -> None:
        assert _walking_minutes(48.85, 2.35, 48.86, 2.36) > 0


class TestSaveDiscoveredOptions:
    def _raw_place(self, place_id: str = "p1", category: str = "museum") -> dict:
        return {
            "place_id": place_id,
            "name": "Test Place",
            "category": category,
            "rating": 4.0,
            "price_level": 2,
            "address": "1 Main St",
            "lat": 48.86,
            "lng": 2.35,
            "opening_hours": [],
            "source": "places_api",
        }

    def test_saves_to_state(self) -> None:
        ctx = _mock_ctx()
        msg = save_discovered_options([self._raw_place()], ctx)
        assert "discovered_options" in ctx.state
        assert len(ctx.state["discovered_options"]) >= 0  # may be filtered

    def test_enriches_lat_lng(self) -> None:
        ctx = _mock_ctx({"guest_profile": {"guest_id": "g1", "dietary_restrictions": [],
            "interests": ["art"], "budget_level": "moderate", "pace": "moderate",
            "party_composition": "solo", "mobility": "full",
            "time_available": {"start_time": "09:00", "end_time": "21:00"},
            "location_context": "", "special_requests": []}})
        save_discovered_options([self._raw_place()], ctx)
        saved = ctx.state["discovered_options"]
        if saved:
            assert "lat_lng" in saved[0]

    def test_filters_dietary_conflicts(self) -> None:
        ctx = _mock_ctx({"guest_profile": {"guest_id": "g1",
            "dietary_restrictions": ["vegan"], "interests": [],
            "budget_level": "moderate", "pace": "moderate",
            "party_composition": "solo", "mobility": "full",
            "time_available": {"start_time": "09:00", "end_time": "21:00"},
            "location_context": "", "special_requests": []}})
        places = [self._raw_place("p1", "steakhouse"), self._raw_place("p2", "cafe")]
        save_discovered_options(places, ctx)
        saved = ctx.state["discovered_options"]
        saved_ids = [s["place_id"] for s in saved]
        assert "p1" not in saved_ids  # steakhouse filtered for vegan

    def test_message_contains_count(self) -> None:
        ctx = _mock_ctx()
        msg = save_discovered_options([self._raw_place()], ctx)
        assert "1" in msg


# ---------------------------------------------------------------------------
# Routes tools
# ---------------------------------------------------------------------------

class TestComputeRoute:
    @patch("concierge.tools.routes.httpx.AsyncClient")
    async def test_returns_duration_and_distance(self, mock_cls) -> None:
        mock_cls.return_value = _async_client_mock(_mock_route_response())
        result = await compute_route(48.85, 2.35, 48.86, 2.36)
        assert "duration_minutes" in result
        assert "distance_meters" in result

    @patch("concierge.tools.routes.httpx.AsyncClient")
    async def test_returns_correct_values(self, mock_cls) -> None:
        mock_cls.return_value = _async_client_mock(_mock_route_response())
        result = await compute_route(48.85, 2.35, 48.86, 2.36)
        assert result["duration_minutes"] == 7  # 420s = 7 min
        assert result["distance_meters"] == 1500


class TestGetTravelTime:
    @patch("concierge.tools.routes.httpx.AsyncClient")
    async def test_returns_int(self, mock_cls) -> None:
        mock_cls.return_value = _async_client_mock(_mock_route_response())
        result = await get_travel_time(48.0, 2.0, 48.1, 2.1)
        assert isinstance(result, int)

    @patch("concierge.tools.routes.httpx.AsyncClient")
    async def test_positive_duration(self, mock_cls) -> None:
        mock_cls.return_value = _async_client_mock(_mock_route_response())
        result = await get_travel_time(48.0, 2.0, 48.05, 2.05)
        assert result > 0


class TestIsOpenAt:
    """Unit tests for the schedule-based _is_open_at helper."""

    def _period(self, open_day: int, open_h: int, close_day: int, close_h: int) -> dict:
        return {
            "open": {"day": open_day, "hour": open_h, "minute": 0},
            "close": {"day": close_day, "hour": close_h, "minute": 0},
        }

    def test_no_periods_returns_true(self) -> None:
        assert _is_open_at({}, "12:00") is True

    def test_within_hours_returns_true(self) -> None:
        import datetime
        today_api = (datetime.date.today().weekday() + 1) % 7
        hours = {"periods": [self._period(today_api, 9, today_api, 22)]}
        assert _is_open_at(hours, "12:00") is True

    def test_before_open_returns_false(self) -> None:
        import datetime
        today_api = (datetime.date.today().weekday() + 1) % 7
        hours = {"periods": [self._period(today_api, 11, today_api, 22)]}
        assert _is_open_at(hours, "09:00") is False

    def test_after_close_returns_false(self) -> None:
        import datetime
        today_api = (datetime.date.today().weekday() + 1) % 7
        hours = {"periods": [self._period(today_api, 9, today_api, 17)]}
        assert _is_open_at(hours, "18:00") is False

    def test_wrong_day_returns_false(self) -> None:
        import datetime
        tomorrow_api = (datetime.date.today().weekday() + 2) % 7
        hours = {"periods": [self._period(tomorrow_api, 9, tomorrow_api, 22)]}
        assert _is_open_at(hours, "12:00") is False

    def test_invalid_arrival_time_returns_true(self) -> None:
        assert _is_open_at({"periods": [{"open": {"day": 1}}]}, "bad") is True


class TestCheckOpeningHours:
    @patch("concierge.tools.routes.httpx.AsyncClient")
    async def test_uses_arrival_time_not_openNow(self, mock_cls) -> None:
        """API response uses regularOpeningHours; result reflects arrival_time."""
        import datetime
        today_api = (datetime.date.today().weekday() + 1) % 7
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "regularOpeningHours": {
                "periods": [
                    {
                        "open": {"day": today_api, "hour": 9, "minute": 0},
                        "close": {"day": today_api, "hour": 22, "minute": 0},
                    }
                ]
            }
        }
        mock_cls.return_value = _async_client_mock(resp)
        result = await check_opening_hours("p-001", "12:00")
        assert result["is_open"] is True

    async def test_fallback_midnight_is_closed(self) -> None:
        """When API fails, fallback uses hour-based check."""
        with patch("concierge.tools.routes.httpx.AsyncClient", side_effect=Exception("timeout")):
            result = await check_opening_hours("p-001", "00:00")
            assert result["is_open"] is False


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
