"""Unit tests for map URL generation."""

from unittest.mock import MagicMock

import pytest

from concierge.models.day_plan import ItineraryStop
from concierge.models.discovered_option import DiscoveredOption
from concierge.tools.map_url import (
    generate_map_url_from_stops_dict,
    generate_multi_stop_map_url,
    generate_place_url,
)

HOTEL_LAT = 48.8566
HOTEL_LNG = 2.3522


@pytest.fixture
def hotel_settings(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Inject controllable hotel coordinates into generate_map_url_from_stops_dict."""
    mock = MagicMock()
    mock.hotel_lat = HOTEL_LAT
    mock.hotel_lng = HOTEL_LNG
    monkeypatch.setattr("concierge.tools.map_url.get_settings", lambda: mock)
    return mock


def _make_stop(lat: float, lng: float, order: int = 1) -> ItineraryStop:
    option = DiscoveredOption(
        place_id=f"p-{order}",
        name=f"Place {order}",
        category="attraction",
        rating=4.0,
        price_level=2,
        address=f"{order} Main St",
        lat_lng=(lat, lng),
        opening_hours=(),
        dietary_compatibility=1.0,
        interest_match=1.0,
        travel_time_from_hotel=15,
        booking_available=False,
        source="places_api",
    )
    return ItineraryStop(
        order=order,
        place=option,
        arrival_time="10:00",
        departure_time="12:00",
        duration_minutes=120,
        travel_to_next=None,
        notes="",
    )


class TestGenerateMultiStopMapUrl:
    def test_starts_with_maps_base(self) -> None:
        stops = [_make_stop(48.86, 2.35)]
        url = generate_multi_stop_map_url(stops, HOTEL_LAT, HOTEL_LNG)
        assert url.startswith("https://www.google.com/maps/dir/")

    def test_contains_hotel_coords(self) -> None:
        stops = [_make_stop(48.86, 2.35)]
        url = generate_multi_stop_map_url(stops, HOTEL_LAT, HOTEL_LNG)
        assert str(HOTEL_LAT) in url
        assert str(HOTEL_LNG) in url

    def test_contains_stop_coords(self) -> None:
        stops = [_make_stop(48.86, 2.35)]
        url = generate_multi_stop_map_url(stops, HOTEL_LAT, HOTEL_LNG)
        assert "48.86" in url
        assert "2.35" in url

    def test_empty_stops_returns_hotel_only(self) -> None:
        url = generate_multi_stop_map_url([], HOTEL_LAT, HOTEL_LNG)
        assert str(HOTEL_LAT) in url

    def test_multiple_stops_all_included(self) -> None:
        stops = [
            _make_stop(48.86, 2.35, 1),
            _make_stop(48.87, 2.36, 2),
            _make_stop(48.88, 2.37, 3),
        ]
        url = generate_multi_stop_map_url(stops, HOTEL_LAT, HOTEL_LNG)
        assert "48.86" in url
        assert "48.87" in url
        assert "48.88" in url

    def test_returns_string(self) -> None:
        stops = [_make_stop(48.86, 2.35)]
        url = generate_multi_stop_map_url(stops, HOTEL_LAT, HOTEL_LNG)
        assert isinstance(url, str)


class TestGenerateMapUrlFromStopsDict:
    def _make_stop_dict(self, lat: float, lng: float) -> dict:
        return {"place": {"lat_lng": [lat, lng], "name": "Test"}}

    def test_starts_with_maps_base(self, hotel_settings: MagicMock) -> None:
        stops = [self._make_stop_dict(48.86, 2.35)]
        url = generate_map_url_from_stops_dict(stops)
        assert url.startswith("https://www.google.com/maps/dir/")

    def test_contains_hotel_coords(self, hotel_settings: MagicMock) -> None:
        stops = [self._make_stop_dict(48.86, 2.35)]
        url = generate_map_url_from_stops_dict(stops)
        assert str(hotel_settings.hotel_lat) in url
        assert str(hotel_settings.hotel_lng) in url

    def test_contains_stop_coords(self, hotel_settings: MagicMock) -> None:
        stops = [self._make_stop_dict(48.86, 2.35)]
        url = generate_map_url_from_stops_dict(stops)
        assert "48.86" in url
        assert "2.35" in url

    def test_multiple_stops_all_included(self, hotel_settings: MagicMock) -> None:
        stops = [
            self._make_stop_dict(48.86, 2.35),
            self._make_stop_dict(48.87, 2.36),
        ]
        url = generate_map_url_from_stops_dict(stops)
        assert "48.86" in url
        assert "48.87" in url

    def test_empty_stops_returns_non_empty(self, hotel_settings: MagicMock) -> None:
        url = generate_map_url_from_stops_dict([])
        assert isinstance(url, str)
        assert len(url) > 0

    def test_malformed_stop_skipped_gracefully(self, hotel_settings: MagicMock) -> None:
        stops = [{"place": {}}, self._make_stop_dict(48.86, 2.35)]
        url = generate_map_url_from_stops_dict(stops)
        assert isinstance(url, str)
        assert "48.86" in url

    def test_exception_returns_empty_string(self, hotel_settings: MagicMock) -> None:
        url = generate_map_url_from_stops_dict(None)  # type: ignore[arg-type]
        assert url == ""

    def test_custom_hotel_coords_used(self, hotel_settings: MagicMock) -> None:
        hotel_settings.hotel_lat = 59.9139
        hotel_settings.hotel_lng = 10.7522
        stops = [self._make_stop_dict(59.91, 10.75)]
        url = generate_map_url_from_stops_dict(stops)
        assert "59.9139" in url
        assert "10.7522" in url


class TestGeneratePlaceUrl:
    def test_contains_place_id(self) -> None:
        url = generate_place_url("ChIJ123abc")
        assert "ChIJ123abc" in url

    def test_is_google_maps_url(self) -> None:
        url = generate_place_url("place-001")
        assert "google.com/maps" in url

    def test_returns_string(self) -> None:
        url = generate_place_url("place-001")
        assert isinstance(url, str)
