from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
import requests 
import asyncio
# from ..challenge_generator.agent import SERVER_URL
import os 
# from ..challenge_generator. import get_intern_history
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8007")

async def assign_xp(name: str, xp_awarded: int, commit_count: int, files_changed: int) -> str:
    """Award XP to an intern for a push.

    Call this once you've decided how much XP a push deserves, based
    on commit_count and files_changed.

    Args:
        name: The intern's GitHub username (must match pusher_name exactly)
        xp_awarded: XP to award for this push
        commit_count: Number of commits in the push
        files_changed: Number of distinct files touched

    Returns:
        Confirmation message with the intern's new total XP
    """
    payload = {"name": name, "xp_awarded": xp_awarded,
               "commit_count": commit_count, "files_changed": files_changed}
    response = await asyncio.to_thread(
        requests.post, f"{SERVER_URL}/xp", json=payload, timeout=10
    )
    response.raise_for_status()
    data = response.json()
    return f"Awarded {xp_awarded} XP to {name}. New total: {data['total_xp']}."


async def get_intern_history(name: str) -> list[str]:
    """
    get history of intern of this name

    """
    payload = {"name": name}
    response = await asyncio.to_thread(
        requests.post, f"{SERVER_URL}/get_history", json=payload, timeout=10
    )
    response.raise_for_status()
    data = response.json()
    return data


async def summarize_progress(name: str) -> str:
    """Summarize an intern's activity using their real history."""
    history = await get_intern_history(name)
    if not history:
        return f"{name} has no recorded activity yet."
    total_xp = sum(e["xp_awarded"] for e in history)
    total_pushes = len(history)
    return f"{name} has pushed {total_pushes} times, earning {total_xp} XP total."

root_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name="evaluator_agent",
    description="Evaluates a GitHub push and awards XP to the intern who made it.",
    instruction=(
        "You evaluate one GitHub push and award XP to the intern who made it. \n"
        "You'll receive their name, commit count, and files changed. \n"
        "1. Decide a fair XP amount from commit_count and files_changed. \n"
        "2. Call assign_xp exactly once with the intern's name and your XP decision. \n"
        "Always use the provided tools rather than describing function calls in text."
        ),
    tools=[assign_xp , summarize_progress , get_intern_history]
)
