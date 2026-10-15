"""Runner-based entry point for the Problem Solver Agent.

Follows the repository's ADK pattern: an ``InMemoryRunner`` drives the agent
over an in-memory session service.
"""

from __future__ import annotations

from google.adk.runners import InMemoryRunner
from google.genai import types

from .agent import agent

APP_NAME = "problem_solver"

runner = InMemoryRunner(agent=agent, app_name=APP_NAME)


async def run_problem(problem: str, user_id: str = "default") -> str:
    """Run the Problem Solver orchestrator on a problem and return its reply.

    Args:
        problem: The user's problem to solve.
        user_id: Session owner id (defaults to "default").

    Returns:
        The concatenated text output of the orchestrator.
    """
    session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id=user_id
    )
    message = types.Content(role="user", parts=[types.Part(text=problem)])
    texts = []
    async for event in runner.run_async(
        user_id=user_id, session_id=session.id, new_message=message
    ):
        for part in (event.content and event.content.parts) or []:
            if part.text:
                texts.append(part.text)
    return "\n".join(texts)