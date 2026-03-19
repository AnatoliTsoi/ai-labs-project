from pathlib import Path

from google.adk.agents import LlmAgent

from concierge.config.settings import get_settings
from concierge.tools.guest_history import get_guest_history
from concierge.tools.state_tools import save_guest_profile
from concierge.tools.weather import get_weather_forecast

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "intake_system.md"


def _load_instruction() -> str:
    settings = get_settings()
    template = _PROMPT_PATH.read_text()
    return template.replace("{hotel_name}", settings.hotel_name)


def build_intake_agent() -> LlmAgent:
    settings = get_settings()
    return LlmAgent(
        name="intake_agent",
        model=settings.agent_model(settings.intake_model),
        description=(
            "Collects guest preferences through warm conversation. "
            "Outputs a structured GuestProfile to session state."
        ),
        instruction=_load_instruction(),
        tools=[
            save_guest_profile,
            get_guest_history,
            get_weather_forecast,
        ],
    )
