from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
import os
import asyncio
import requests 
import os
from dotenv import load_dotenv
load_dotenv()
SERVER_URL = os.getenv("SERVER_URL")
print("SERVER_URL:", SERVER_URL) 

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


root_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name="XP_calc",
    description="Evaluates a GitHub push and awards XP to the intern who made it.",
    instruction=(
    "You are an XP evaluator.\n"
    "You will receive a GitHub push summary.\n"
    "Your ONLY job is to call the assign_xp tool exactly ONE time, then stop.\n\n"
    "Rules:\n"
    "- Call assign_xp exactly once with the correct name, xp_awarded, "
    "commit_count, and files_changed.\n"
    "- After the tool returns a result, reply with a single short "
    "confirmation sentence (e.g. 'Awarded 5 XP to gannaosama137.') and stop.\n"
    "- Do NOT call assign_xp again after it has returned a result, even if "
    "you're unsure the first call succeeded.\n"
    "- The name argument must be exactly the GitHub username received.\n"
    "- xp_awarded must be an integer.\n"
    ),
    tools=[assign_xp],
)
# JJJJJJJJ 
# GADBrgioerogjesrojo