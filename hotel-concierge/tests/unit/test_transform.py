"""Unit tests for the _transform_plan_for_frontend helper in server.py.

These tests validate the contract between backend DayPlan dict shape
and what the React frontend expects, without requiring a live Gemini API call.
"""

from concierge.server import _transform_plan_for_frontend


def _backend_stop(
    order: int = 1,
    lat: float = 48.86,
    lng: float = 2.35,
    mode: str = "walk",
    distance_meters: int = 900,
) -> dict:
    return {
        "order": order,
        "place": {
            "place_id": f"p-{order}",
            "name": f"Place {order}",
            "category": "restaurant",
            "rating": 4.5,
            "price_level": 2,
            "address": "1 Test St",
            "lat": lat,
            "lng": lng,
            "opening_hours": ["09:00-22:00"],
        },
        "arrival_time": "10:00",
        "departure_time": "12:00",
        "duration_minutes": 120,
        "travel_to_next": {
            "mode": mode,
            "duration_minutes": 12,
            "distance_meters": distance_meters,
        },
        "notes": "Test note",
    }


def _backend_plan(stops: list[dict] | None = None) -> dict:
    return {
        "date": "2026-03-19",
        "stops": [_backend_stop()] if stops is None else stops,
        "total_travel_time": 45,
        "estimated_total_cost": "$80-120",
        "weather_contingency": "Indoor backup available",
        "back_at_hotel_by": "22:00",
    }


class TestTransformPlanForFrontend:
    def test_top_level_fields_preserved(self) -> None:
        result = _transform_plan_for_frontend(_backend_plan())
        assert result["date"] == "2026-03-19"
        assert result["total_travel_time"] == 45
        assert result["estimated_total_cost"] == "$80-120"
        assert result["back_at_hotel_by"] == "22:00"

    def test_distance_meters_converted_to_distance_km(self) -> None:
        result = _transform_plan_for_frontend(_backend_plan([_backend_stop(distance_meters=1500)]))
        travel = result["stops"][0]["travel_to_next"]
        assert "distance_km" in travel
        assert "distance_meters" not in travel
        assert travel["distance_km"] == 1.5

    def test_walk_mode_converted_to_walking(self) -> None:
        result = _transform_plan_for_frontend(_backend_plan([_backend_stop(mode="walk")]))
        assert result["stops"][0]["travel_to_next"]["mode"] == "walking"

    def test_drive_mode_converted_to_driving(self) -> None:
        result = _transform_plan_for_frontend(_backend_plan([_backend_stop(mode="drive")]))
        assert result["stops"][0]["travel_to_next"]["mode"] == "driving"

    def test_transit_mode_unchanged(self) -> None:
        result = _transform_plan_for_frontend(_backend_plan([_backend_stop(mode="transit")]))
        assert result["stops"][0]["travel_to_next"]["mode"] == "transit"

    def test_lat_lng_normalised_from_lat_lng_fields(self) -> None:
        result = _transform_plan_for_frontend(_backend_plan([_backend_stop(lat=48.86, lng=2.35)]))
        place = result["stops"][0]["place"]
        assert "lat_lng" in place
        assert place["lat_lng"] == [48.86, 2.35]

    def test_frontend_defaults_added_to_place(self) -> None:
        result = _transform_plan_for_frontend(_backend_plan())
        place = result["stops"][0]["place"]
        assert "dietary_compatibility" in place
        assert "interest_match" in place
        assert "travel_time_from_hotel" in place
        assert "booking_available" in place
        assert "source" in place

    def test_map_url_passed_through(self) -> None:
        plan = _backend_plan()
        plan["map_url"] = "https://www.google.com/maps/dir/1,2/3,4"
        result = _transform_plan_for_frontend(plan)
        assert result["map_url"] == "https://www.google.com/maps/dir/1,2/3,4"

    def test_map_url_none_when_absent(self) -> None:
        result = _transform_plan_for_frontend(_backend_plan())
        assert result.get("map_url") is None

    def test_empty_stops_list(self) -> None:
        result = _transform_plan_for_frontend(_backend_plan(stops=[]))
        assert result["stops"] == []

    def test_null_travel_to_next_preserved(self) -> None:
        stop = _backend_stop()
        stop["travel_to_next"] = None
        result = _transform_plan_for_frontend(_backend_plan([stop]))
        assert result["stops"][0]["travel_to_next"] is None

    def test_input_plan_not_mutated(self) -> None:
        original = _backend_plan([_backend_stop(mode="walk", distance_meters=1500)])
        import copy
        snapshot = copy.deepcopy(original)
        _transform_plan_for_frontend(original)
        assert original == snapshot
