"""Hotel Concierge — Google ADK multi-agent system.

The `root_agent` export is required by `adk web concierge` to serve
the agent in the ADK developer UI.
"""

from concierge.agents.orchestrator import build_concierge_orchestrator

root_agent = build_concierge_orchestrator()

__all__ = ["root_agent"]
