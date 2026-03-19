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

    # Budget controls
    max_api_cost_per_session_usd: float = 0.50
    places_cache_ttl_seconds: int = 3600
    routes_cache_ttl_seconds: int = 900
    place_details_cache_ttl_seconds: int = 86400

    # ADK model
    gemini_model: str = "gemini-2.5-flash"
    max_loop_iterations: int = 5


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
