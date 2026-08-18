import asyncio
import sys

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from problem_solver.agent import root_agent

APP_NAME = "problem_solver"
USER_ID = "cli_user"


def run_problem(problem: str, session_id: str = "cli_session") -> None:
    session_service = InMemorySessionService()
    session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )

    runner = Runner(agent=root_agent, app_name=APP_NAME)

    print("\n" + "=" * 70)
    print("PROBLEM:", problem)
    print("=" * 70)

    async def _run():
        final_text = None
        async for event in runner.run(
            user_id=USER_ID,
            session_id=session_id,
            new_message=types.Content(role="user", parts=[types.Part(text=problem)]),
        ):
            if event.content and event.content.parts:
                text = "".join(p.text or "" for p in event.content.parts if p.text)
                if text.strip():
                    if event.is_final_response():
                        final_text = text
                    else:
                        print(f"\n--- {event.author} ---\n{text}")
        return final_text

    final = asyncio.run(_run())

    print("\n" + "=" * 70)
    print("FINAL ANSWER")
    print("=" * 70)
    print(final or "(no final answer produced)")


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: uv run python -m problem_solver "<coding problem>"')
        sys.exit(1)
    run_problem(" ".join(sys.argv[1:]))


if __name__ == "__main__":
    main()