"""XP Calculator agent — awards XP only for Mahmoud's own GitHub pushes."""

from __future__ import annotations

import asyncio
import os

import requests
from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

# Reuse Challenge Generator tools (they are plain functions).
from challenge_generator.agent import push_to_leaderboard, save_to_database  # noqa: F401

load_dotenv()

SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8011")
# Must match GitHub pusher.name and the shared leaderboard entry (seed_interns).
MY_GITHUB_USERNAME = os.getenv("MY_GITHUB_USERNAME", "mahmoud-aymann")


def _compute_xp(commit_count: int, files_changed: int) -> int:
    """Simple XP formula: base per commit + bonus per distinct file."""
    return max(1, (commit_count * 10) + (files_changed * 5))


async def evaluate_task(
    pusher_name: str,
    commit_count: int,
    files_changed: int,
    your_name: str,
) -> str:
    """Compute and award XP for a push — only when it is your own push.

    Args:
        pusher_name: GitHub pusher.name from the webhook payload
        commit_count: Number of commits in the push
        files_changed: Number of distinct files added/modified/removed
        your_name: Your GitHub username (must equal MY_GITHUB_USERNAME)

    Returns:
        Status string. If the push is not yours, nothing is written.
    """
    if pusher_name != your_name:
        msg = f'ignored, not my push (pusher={pusher_name!r}, me={your_name!r})'
        print(msg)
        return msg

    xp_awarded = _compute_xp(commit_count, files_changed)
    payload = {
        "name": pusher_name,
        "xp_awarded": xp_awarded,
        "commit_count": commit_count,
        "files_changed": files_changed,
    }
    response = await asyncio.to_thread(
        requests.post, f"{SERVER_URL}/xp", json=payload, timeout=10
    )
    response.raise_for_status()
    data = response.json()
    return (
        f"Awarded {xp_awarded} XP to {pusher_name}. "
        f"New total: {data.get('total_xp', '?')}."
    )


root_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name="XP_Evaluator",
    description="Evaluates a GitHub push and awards XP only for Mahmoud's pushes.",
    instruction=f"""
You evaluate ONE GitHub push and award XP.

You will receive short plain-text facts: Pusher, Commits, Files changed.

Rules:
1. Call evaluate_task exactly once with:
   - pusher_name = the Pusher value
   - commit_count = the Commits number (integer)
   - files_changed = the Files changed number (integer)
   - your_name = "{MY_GITHUB_USERNAME}"
2. Do not invent extra tool calls.
3. If evaluate_task says the push was ignored, stop — do not retry.
Always use the provided tools rather than describing function calls in text.
""",
    tools=[evaluate_task],
)
