"""Unit tests for the Settings configuration class."""

from concierge.config.settings import Settings


class TestSettingsDefaults:
    def test_per_agent_model_fields_exist(self) -> None:
        s = Settings()
        assert hasattr(s, "intake_model")
        assert hasattr(s, "discovery_model")
        assert hasattr(s, "route_planner_model")
        assert hasattr(s, "presenter_model")

    def test_per_agent_model_defaults_to_empty_string(self) -> None:
        s = Settings()
        assert s.intake_model == ""
        assert s.discovery_model == ""
        assert s.route_planner_model == ""
        assert s.presenter_model == ""

    def test_agent_model_falls_back_to_gemini_model(self) -> None:
        s = Settings(gemini_model="gemini-2.5-flash")
        assert s.agent_model("") == "gemini-2.5-flash"
        assert s.agent_model(s.intake_model) == "gemini-2.5-flash"

    def test_agent_model_uses_override_when_set(self) -> None:
        s = Settings(intake_model="gemini-2.0-flash")
        assert s.agent_model(s.intake_model) == "gemini-2.0-flash"

    def test_gemini_model_has_default(self) -> None:
        s = Settings()
        assert s.gemini_model != ""
