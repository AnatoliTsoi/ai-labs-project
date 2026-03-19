from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
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
    hotel_address: str = "Kungsgatan 2, Stockholm, Sweden"
    hotel_lat: float = 59.3346
    hotel_lng: float = 18.0632

    # Budget controls
    max_api_cost_per_session_usd: float = 0.50
    places_cache_ttl_seconds: int = 3600
    routes_cache_ttl_seconds: int = 900
    place_details_cache_ttl_seconds: int = 86400

    # ADK model
    gemini_model: str = "gemini-2.5-flash"
    max_loop_iterations: int = 5

    def agent_model(self, override: str) -> str:
        return override or self.gemini_model


_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create settings. Reloads from .env each time the module is reimported."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Force settings to reload from .env on next access."""
    global _settings
    _settings = None
