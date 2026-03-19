"""Unit tests for the formatting pure functions."""

import pytest

from concierge.models.day_plan import DayPlan, ItineraryStop, TravelSegment
from concierge.models.discovered_option import DiscoveredOption
from concierge.tools.formatting import format_itinerary_markdown, format_itinerary_summary


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_option() -> DiscoveredOption:
    return DiscoveredOption(
        place_id="p-001",
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
def sample_plan(sample_option: DiscoveredOption) -> DayPlan:
    stop = ItineraryStop(
        order=1,
        place=sample_option,
        arrival_time="10:00",
        departure_time="12:00",
        duration_minutes=120,
        travel_to_next=TravelSegment(mode="walk", duration_minutes=12, distance_meters=900),
        notes="Ask for terrace seating",
    )
    return DayPlan(
        date="2026-03-19",
        stops=(stop,),
        total_travel_time=12,
        estimated_total_cost="$50-80 per person",
        weather_contingency="Visit the covered market instead",
        back_at_hotel_by="22:00",
    )


# ---------------------------------------------------------------------------
# format_itinerary_markdown tests
# ---------------------------------------------------------------------------

class TestFormatItineraryMarkdown:
    def test_contains_date(self, sample_plan: DayPlan) -> None:
        output = format_itinerary_markdown(sample_plan)
        assert "2026-03-19" in output

    def test_contains_place_name(self, sample_plan: DayPlan) -> None:
        output = format_itinerary_markdown(sample_plan)
        assert "Le Bistro" in output

    def test_contains_arrival_and_departure(self, sample_plan: DayPlan) -> None:
        output = format_itinerary_markdown(sample_plan)
        assert "10:00" in output
        assert "12:00" in output

    def test_contains_back_at_hotel(self, sample_plan: DayPlan) -> None:
        output = format_itinerary_markdown(sample_plan)
        assert "22:00" in output

    def test_contains_cost_estimate(self, sample_plan: DayPlan) -> None:
        output = format_itinerary_markdown(sample_plan)
        assert "$50-80" in output

    def test_contains_travel_segment(self, sample_plan: DayPlan) -> None:
        output = format_itinerary_markdown(sample_plan)
        assert "12 min" in output

    def test_contains_notes(self, sample_plan: DayPlan) -> None:
        output = format_itinerary_markdown(sample_plan)
        assert "terrace" in output.lower()

    def test_contains_weather_contingency(self, sample_plan: DayPlan) -> None:
        output = format_itinerary_markdown(sample_plan)
        assert "covered market" in output

    def test_returns_string(self, sample_plan: DayPlan) -> None:
        output = format_itinerary_markdown(sample_plan)
        assert isinstance(output, str)

    def test_stop_without_travel_segment(self, sample_option: DiscoveredOption) -> None:
        stop = ItineraryStop(
            order=1,
            place=sample_option,
            arrival_time="10:00",
            departure_time="12:00",
            duration_minutes=120,
            travel_to_next=None,
            notes="",
        )
        plan = DayPlan(
            date="2026-03-19",
            stops=(stop,),
            total_travel_time=0,
            estimated_total_cost="$50",
            weather_contingency="",
            back_at_hotel_by="22:00",
        )
        output = format_itinerary_markdown(plan)
        assert "Le Bistro" in output

    def test_empty_weather_contingency_omitted(self, sample_option: DiscoveredOption) -> None:
        stop = ItineraryStop(
            order=1,
            place=sample_option,
            arrival_time="10:00",
            departure_time="12:00",
            duration_minutes=120,
            travel_to_next=None,
            notes="",
        )
        plan = DayPlan(
            date="2026-03-19",
            stops=(stop,),
            total_travel_time=0,
            estimated_total_cost="$50",
            weather_contingency="",
            back_at_hotel_by="22:00",
        )
        output = format_itinerary_markdown(plan)
        assert "Rain plan" not in output


# ---------------------------------------------------------------------------
# format_itinerary_summary tests
# ---------------------------------------------------------------------------

class TestFormatItinerarySummary:
    def test_contains_stop_count(self, sample_plan: DayPlan) -> None:
        summary = format_itinerary_summary(sample_plan)
        assert "1 stop" in summary

    def test_contains_place_name(self, sample_plan: DayPlan) -> None:
        summary = format_itinerary_summary(sample_plan)
        assert "Le Bistro" in summary

    def test_contains_date(self, sample_plan: DayPlan) -> None:
        summary = format_itinerary_summary(sample_plan)
        assert "2026-03-19" in summary

    def test_returns_single_line(self, sample_plan: DayPlan) -> None:
        summary = format_itinerary_summary(sample_plan)
        assert "\n" not in summary
