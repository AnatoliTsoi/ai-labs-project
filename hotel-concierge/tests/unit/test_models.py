"""Unit tests for frozen dataclass models."""

import pytest

from concierge.models.day_plan import DayPlan, ItineraryStop, TravelSegment
from concierge.models.discovered_option import DiscoveredOption
from concierge.models.feedback import VALID_ACTIONS, FeedbackAction
from concierge.models.guest_profile import GuestProfile, TimeWindow


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_option() -> DiscoveredOption:
    return DiscoveredOption(
        place_id="place-001",
        name="Le Bistro",
        category="restaurant",
        rating=4.5,
        price_level=2,
        address="1 Rue de la Paix",
        lat_lng=(48.8566, 2.3522),
        opening_hours=("Mon-Sun: 12:00-22:00",),
        dietary_compatibility=0.9,
        interest_match=0.8,
        travel_time_from_hotel=10,
        booking_available=True,
        source="places_api",
    )


@pytest.fixture
def sample_profile() -> GuestProfile:
    return GuestProfile(
        guest_id="G-001",
        dietary_restrictions=("vegan",),
        interests=("art", "local-food"),
        mobility="full",
        budget_level="moderate",
        pace="moderate",
        party_composition="couple",
        time_available=TimeWindow(start_time="09:00", end_time="22:00"),
        location_context="123 Main Street",
        special_requests=("avoid tourist traps",),
    )


# ---------------------------------------------------------------------------
# GuestProfile tests
# ---------------------------------------------------------------------------

class TestGuestProfile:
    def test_is_immutable(self, sample_profile: GuestProfile) -> None:
        with pytest.raises((AttributeError, TypeError)):
            sample_profile.guest_id = "hacked"  # type: ignore[misc]

    def test_round_trip_serialization(self, sample_profile: GuestProfile) -> None:
        data = sample_profile.to_dict()
        restored = GuestProfile.from_dict(data)
        assert restored == sample_profile

    def test_dietary_restrictions_are_tuple(self, sample_profile: GuestProfile) -> None:
        assert isinstance(sample_profile.dietary_restrictions, tuple)

    def test_interests_are_tuple(self, sample_profile: GuestProfile) -> None:
        assert isinstance(sample_profile.interests, tuple)

    def test_time_window_preserved(self, sample_profile: GuestProfile) -> None:
        assert sample_profile.time_available.start_time == "09:00"
        assert sample_profile.time_available.end_time == "22:00"


# ---------------------------------------------------------------------------
# DiscoveredOption tests
# ---------------------------------------------------------------------------

class TestDiscoveredOption:
    def test_is_immutable(self, sample_option: DiscoveredOption) -> None:
        with pytest.raises((AttributeError, TypeError)):
            sample_option.name = "hacked"  # type: ignore[misc]

    def test_round_trip_serialization(self, sample_option: DiscoveredOption) -> None:
        data = sample_option.to_dict()
        restored = DiscoveredOption.from_dict(data)
        assert restored == sample_option

    def test_lat_lng_is_tuple(self, sample_option: DiscoveredOption) -> None:
        assert isinstance(sample_option.lat_lng, tuple)
        assert len(sample_option.lat_lng) == 2

    def test_opening_hours_is_tuple(self, sample_option: DiscoveredOption) -> None:
        assert isinstance(sample_option.opening_hours, tuple)


# ---------------------------------------------------------------------------
# FeedbackAction tests
# ---------------------------------------------------------------------------

class TestFeedbackAction:
    @pytest.mark.parametrize("action", list(VALID_ACTIONS))
    def test_valid_actions_accepted(self, action: str) -> None:
        fb = FeedbackAction(action=action, target_stop=None, details="test")
        assert fb.action == action

    def test_invalid_action_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid action"):
            FeedbackAction(action="fly_to_moon", target_stop=None, details="")

    def test_round_trip_serialization(self) -> None:
        fb = FeedbackAction(action="swap_stop", target_stop=2, details="I prefer Italian")
        restored = FeedbackAction.from_dict(fb.to_dict())
        assert restored == fb

    def test_is_immutable(self) -> None:
        fb = FeedbackAction(action="approve", target_stop=None, details="")
        with pytest.raises((AttributeError, TypeError)):
            fb.action = "restart"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DayPlan / ItineraryStop tests
# ---------------------------------------------------------------------------

class TestDayPlan:
    def _make_stop(self, option: DiscoveredOption, order: int = 1) -> ItineraryStop:
        return ItineraryStop(
            order=order,
            place=option,
            arrival_time="10:00",
            departure_time="12:00",
            duration_minutes=120,
            travel_to_next=TravelSegment(mode="walk", duration_minutes=12, distance_meters=900),
            notes="First stop of the day",
        )

    def test_day_plan_round_trip(self, sample_option: DiscoveredOption) -> None:
        stop = self._make_stop(sample_option)
        plan = DayPlan(
            date="2026-03-19",
            stops=(stop,),
            total_travel_time=12,
            estimated_total_cost="$50-80",
            weather_contingency="Indoor museum if rain",
            back_at_hotel_by="22:00",
        )
        restored = DayPlan.from_dict(plan.to_dict())
        assert restored == plan

    def test_stops_are_tuple(self, sample_option: DiscoveredOption) -> None:
        stop = self._make_stop(sample_option)
        plan = DayPlan(
            date="2026-03-19",
            stops=(stop,),
            total_travel_time=12,
            estimated_total_cost="$50",
            weather_contingency="",
            back_at_hotel_by="22:00",
        )
        assert isinstance(plan.stops, tuple)

    def test_stop_without_travel_segment(self, sample_option: DiscoveredOption) -> None:
        stop = ItineraryStop(
            order=1,
            place=sample_option,
            arrival_time="10:00",
            departure_time="12:00",
            duration_minutes=120,
            travel_to_next=None,
            notes="Last stop",
        )
        data = stop.to_dict()
        restored = ItineraryStop.from_dict(data)
        assert restored.travel_to_next is None
