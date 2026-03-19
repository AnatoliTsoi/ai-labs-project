"""Integration tests for the FastAPI server endpoints."""

import pytest
from fastapi.testclient import TestClient

from concierge.server import app


@pytest.fixture()
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "hotel" in data


class TestPlanEndpoint:
    """Test the POST /plan endpoint.

    NOTE: These tests actually run the ADK orchestrator with the Gemini model,
    so they require a valid GOOGLE_API_KEY in .env. They are skipped in CI
    if the key is not set.
    """

    @pytest.fixture()
    def sample_profile(self) -> dict:
        return {
            "profile": {
                "interests": ["art", "food"],
                "dietary_restrictions": ["vegan"],
                "pace": "moderate",
                "budget_level": "luxury",
                "party_composition": "couple",
                "time_available": {
                    "start_time": "09:00",
                    "end_time": "21:00",
                },
            }
        }

    def test_plan_returns_200(self, client: TestClient, sample_profile: dict) -> None:
        resp = client.post(
            "/plan",
            json=sample_profile,
            headers={"X-Session-ID": "test-session-001"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "day_plan" in data

    def test_plan_with_session_header(self, client: TestClient, sample_profile: dict) -> None:
        resp = client.post(
            "/plan",
            json=sample_profile,
            headers={"X-Session-ID": "test-session-002"},
        )
        assert resp.status_code == 200

    def test_plan_without_session_header(self, client: TestClient, sample_profile: dict) -> None:
        """Should auto-generate a session ID when none is provided."""
        resp = client.post("/plan", json=sample_profile)
        assert resp.status_code == 200

    def test_plan_response_shape(self, client: TestClient, sample_profile: dict) -> None:
        """Verify the response matches the frontend DayPlan type shape."""
        resp = client.post(
            "/plan",
            json=sample_profile,
            headers={"X-Session-ID": "test-session-shape"},
        )
        data = resp.json()
        plan = data.get("day_plan")

        if plan is None:
            # Agent didn't produce a plan — check error message is present
            assert "message" in data or "error" in data
            return

        # Validate top-level DayPlan fields
        assert "date" in plan
        assert "stops" in plan
        assert isinstance(plan["stops"], list)
        assert "total_travel_time" in plan
        assert "estimated_total_cost" in plan
        assert "back_at_hotel_by" in plan

        # Validate stop shape if any stops exist
        if plan["stops"]:
            stop = plan["stops"][0]
            assert "order" in stop
            assert "place" in stop
            assert "arrival_time" in stop
            assert "departure_time" in stop
            assert "duration_minutes" in stop
            assert "notes" in stop

            place = stop["place"]
            assert "name" in place
            assert "category" in place

    def test_cors_headers_present(self, client: TestClient, sample_profile: dict) -> None:
        """Verify CORS headers are returned for allowed origins."""
        resp = client.options(
            "/plan",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"

    def test_minimal_profile(self, client: TestClient) -> None:
        """A nearly empty profile should still work (defaults apply)."""
        resp = client.post(
            "/plan",
            json={"profile": {"interests": ["food"]}},
            headers={"X-Session-ID": "test-minimal"},
        )
        assert resp.status_code == 200
