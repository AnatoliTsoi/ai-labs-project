from pathlib import Path

from google.adk.agents import LlmAgent

from concierge.config.settings import get_settings
from concierge.tools.places import get_place_details, save_discovered_options, search_nearby_places

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "discovery_system.md"


def _load_instruction() -> str:
    settings = get_settings()
    template = _PROMPT_PATH.read_text()
    return (
        template
        + f"\n\n## Hotel Coordinates\nLatitude: {settings.hotel_lat}, "
        f"Longitude: {settings.hotel_lng}\nAddress: {settings.hotel_address}"
    )


def build_discovery_agent() -> LlmAgent:
    settings = get_settings()
    return LlmAgent(
        name="discovery_agent",
        model=settings.agent_model(settings.discovery_model),
        description=(
            "Searches for local places and activities using Google Places API. "
            "Saves top scored options to session state for the Route Planner."
        ),
        instruction=_load_instruction(),
        tools=[
            search_nearby_places,
            get_place_details,
            save_discovered_options,
        ],
    )
