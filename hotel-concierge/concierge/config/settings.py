from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Google APIs
    google_api_key: str = ""
    google_maps_api_key: str = ""
    google_genai_use_vertexai: bool = False

    # Application
    app_name: str = "hotel-concierge"
    log_level: str = "INFO"
    hotel_name: str = "Grand Hotel"
    hotel_address: str = "123 Main Street"
    hotel_lat: float = 48.8566
    hotel_lng: float = 2.3522

    # Request timeout — covers the entire 4-agent pipeline (LLM + API calls)
    request_timeout_seconds: int = 300

    # Budget controls
    max_api_cost_per_session_usd: float = 0.50
    places_cache_ttl_seconds: int = 3600
    routes_cache_ttl_seconds: int = 900
    place_details_cache_ttl_seconds: int = 86400

    # ADK model
    gemini_model: str = "gemini-2.5-flash"
    # The pipeline is one-shot: profile is fully provided upfront, so one pass
    # through intake→discovery→route_planner→presenter is all that's needed.
    max_loop_iterations: int = 1

    # Per-agent model overrides (empty string → falls back to gemini_model)
    intake_model: str = ""
    discovery_model: str = ""
    route_planner_model: str = ""
    presenter_model: str = ""

    def agent_model(self, override: str) -> str:
        return override or self.gemini_model


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
