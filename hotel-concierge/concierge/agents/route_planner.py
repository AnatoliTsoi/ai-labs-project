from pathlib import Path

from google.adk.agents import LlmAgent

from concierge.config.settings import get_settings
from concierge.tools.map_url import generate_map_url_from_stops_dict
from concierge.tools.routes import check_opening_hours, compute_route
from concierge.tools.state_tools import save_day_plan

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "route_planner_system.md"


def build_route_planner_agent() -> LlmAgent:
    settings = get_settings()
    return LlmAgent(
        name="route_planner_agent",
        model=settings.agent_model(settings.route_planner_model),
        description=(
            "Transforms discovered options and guest constraints into a time-aware "
            "day itinerary with real travel times between stops."
        ),
        instruction=_PROMPT_PATH.read_text(),
        tools=[
            compute_route,
            check_opening_hours,
            generate_map_url_from_stops_dict,
            save_day_plan,
        ],
    )
