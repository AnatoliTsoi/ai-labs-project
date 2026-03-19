"""CLI entry point for running the concierge interactively."""

import asyncio

from google.adk.runners import InMemoryRunner
from google.genai import types

from concierge.agents.orchestrator import build_concierge_orchestrator
from concierge.config.settings import get_settings


async def run_cli() -> None:
    settings = get_settings()
    orchestrator = build_concierge_orchestrator()
    runner = InMemoryRunner(agent=orchestrator, app_name=settings.app_name)

    user_id = "cli-guest"
    session_id = "cli-session-001"

    print(f"\n{'=' * 60}")
    print(f"  {settings.hotel_name} — AI Concierge")
    print(f"{'=' * 60}")
    print("Type your message and press Enter. Ctrl+C to exit.\n")

    greeting = types.UserContent(parts=[types.Part(text="Hello, I just checked in.")])

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=greeting,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"Concierge: {part.text}\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        message = types.UserContent(parts=[types.Part(text=user_input)])
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=message,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"Concierge: {part.text}\n")


if __name__ == "__main__":
    asyncio.run(run_cli())
