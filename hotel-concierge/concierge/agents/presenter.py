from pathlib import Path

from google.adk.agents import LlmAgent

from concierge.config.settings import get_settings
from concierge.tools.state_tools import record_feedback

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "presenter_system.md"


def build_presenter_agent() -> LlmAgent:
    settings = get_settings()
    return LlmAgent(
        name="presenter_agent",
        model=settings.gemini_model,
        description=(
            "Presents the day plan conversationally, interprets guest feedback, "
            "and controls the refinement loop (approve to exit, or route back)."
        ),
        instruction=_PROMPT_PATH.read_text(),
        tools=[
            record_feedback,
        ],
    )
