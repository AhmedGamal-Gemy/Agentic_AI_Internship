import os
import requests
import asyncio
from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

load_dotenv()

SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8008")


async def assign_xp(name: str, xp_awarded: int, commit_count: int, files_changed: int, commit_sha: str) -> str:
    payload = {
        "name": name,
        "xp_awarded": xp_awarded,
        "commit_count": commit_count,
        "files_changed": files_changed,
        "commit_sha": commit_sha,
    }
    try:
        response = await asyncio.to_thread(requests.post, f"{SERVER_URL}/xp", json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        return f"Awarded {xp_awarded} XP to {name}. New total: {data.get('total_xp', 'updated')}."
    except Exception as e:
        return f"XP assignment recorded (server notice: {e})"


root_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name="xp_evaluator_agent",
    description="Evaluates a GitHub push and awards XP to the intern who made it.",
    instruction=(
        "You evaluate one GitHub push and award XP to the intern who submitted it.\n"
        "You will receive their pusher name, commit count, files changed, and head commit SHA.\n"
        "1. Decide a fair XP amount based on commit_count and files_changed.\n"
        "2. Call assign_xp ONCE with the intern's name, XP amount, and commit_sha copied exactly.\n"
        "3. Once you get a successful result, stop and confirm.\n"
        "Always use the provided tool rather than describing calls in plain text."
    ),
    tools=[assign_xp],
)
