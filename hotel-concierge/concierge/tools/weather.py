"""Weather forecast tool.

Phase 1: Returns mock data. Phase 2: Integrate a real weather API.
"""

from google.adk.tools import ToolContext


def get_weather_forecast(
    latitude: float,
    longitude: float,
    date: str,
    tool_context: ToolContext = None,
) -> dict:
    """Get weather forecast for a location and date.

    Args:
        latitude: Location latitude.
        longitude: Location longitude.
        date: Date in YYYY-MM-DD format.

    Returns:
        Dict with condition, temperature_celsius, rain_probability.
    """
    # TODO Phase 2: Integrate real weather API (e.g., Open-Meteo or Google Weather)
    return {
        "date": date,
        "condition": "Partly cloudy",
        "temperature_celsius": 18,
        "rain_probability": 0.20,
        "outdoor_friendly": True,
        "status": "mock",
    }
