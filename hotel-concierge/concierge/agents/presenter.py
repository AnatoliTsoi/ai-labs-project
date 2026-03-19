from pathlib import Path

from google.adk.agents import LlmAgent

from concierge.config.settings import get_settings

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "presenter_system.md"


def build_presenter_agent() -> LlmAgent:
    settings = get_settings()
    return LlmAgent(
        name="presenter_agent",
        model=settings.agent_model(settings.presenter_model),
        description=(
            "Presents the completed day plan as a clear summary. "
            "Does not collect feedback — this is a one-shot flow."
        ),
        instruction=_PROMPT_PATH.read_text(),
        tools=[],
    )
