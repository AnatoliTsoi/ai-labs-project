from google.adk.agents import LoopAgent

from concierge.agents.discovery import build_discovery_agent
from concierge.agents.intake import build_intake_agent
from concierge.agents.presenter import build_presenter_agent
from concierge.agents.route_planner import build_route_planner_agent
from concierge.config.settings import get_settings


def build_concierge_orchestrator() -> LoopAgent:
    """Build the top-level LoopAgent that drives the full concierge cycle.

    Loop: intake → discovery → route_planner → presenter
    Exits when the presenter calls record_feedback(action="approve")
    or when max_iterations is reached.
    """
    settings = get_settings()
    return LoopAgent(
        name="concierge_orchestrator",
        description=(
            "Orchestrates the hotel concierge loop: collect preferences → "
            "discover places → build route → present and refine. "
            "Exits when the guest approves the plan."
        ),
        max_iterations=settings.max_loop_iterations,
        sub_agents=[
            build_intake_agent(),
            build_discovery_agent(),
            build_route_planner_agent(),
            build_presenter_agent(),
        ],
    )
