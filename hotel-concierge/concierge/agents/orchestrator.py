from google.adk.agents import LoopAgent

from concierge.agents.discovery import build_discovery_agent
from concierge.agents.route_planner import build_route_planner_agent
from concierge.config.settings import get_settings


def build_concierge_orchestrator() -> LoopAgent:
    """Build the top-level LoopAgent that drives the concierge pipeline.

    Loop: discovery → route_planner
    Guest profile is pre-seeded into session state by the server before the run.
    Exits when max_iterations is reached.
    """
    settings = get_settings()
    return LoopAgent(
        name="concierge_orchestrator",
        description=(
            "Orchestrates the hotel concierge pipeline: "
            "discover places → build route → save day plan."
        ),
        max_iterations=settings.max_loop_iterations,
        sub_agents=[
            build_discovery_agent(),
            build_route_planner_agent(),
        ],
    )
