# from google.adk.agents.llm_agent import Agent
# from google.adk.models.lite_llm import LiteLlm
# import asyncio
# import requests
# from challenge_generator.agent import SERVER_URL

# async def assign_xp(name: str, xp_awarded: int, commit_count: int, files_changed: int) -> str:
#     """Award XP to an intern for a push.

#     Call this once you've decided how much XP a push deserves, based
#     on commit_count and files_changed.

#     Args:
#         name: The intern's GitHub username (must match pusher_name exactly)
#         xp_awarded: XP to award for this push
#         commit_count: Number of commits in the push
#         files_changed: Number of distinct files touched

#     Returns:
#         Confirmation message with the intern's new total XP
#     """
#     payload = {"name": name, "xp_awarded": xp_awarded,
#                "commit_count": commit_count, "files_changed": files_changed}
#     response = await asyncio.to_thread(
#         requests.post, f"{SERVER_URL}/xp", json=payload, timeout=10
#     )
#     response.raise_for_status()
#     data = response.json()
#     return f"Awarded {xp_awarded} XP to {name}. New total: {data['total_xp']}."





# root_agent = Agent(
#     model=LiteLlm("groq/llama-3.3-70b-versatile"),
#     name='root_agent',
#     description='A helpful assistant for user questions.',
#     instruction="You evaluate one GitHub push and award XP to the intern who made it.\n"

#         "You'll receive their name, commit count, and files changed.\n"

#         "1. Decide a fair XP amount from commit_count and files_changed.\n"

#         "2. Call assign_xp exactly once with the intern's name and your XP decision.\n"

#         "Always use the provided tools rather than describing function calls in text.",
#     tools=[assign_xp]

# )



from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
import requests
import asyncio
import os
from challenge_generator.agent import SERVER_URL


SERVER_URL = os.getenv("SERVER_URL")
# added 5 files 
# modified 4 files


# user -> push -> github -> webhook -> push callback -> server -> run agent ( tool -> server ) ( using runner ) -> update redis. 

async def assign_xp(name: str, xp_awarded: int, commit_count: int, files_changed: int, commit_sha: str) -> str:
    """Award XP to an intern for a push.

    Call this once you've decided how much XP a push deserves, based
    on commit_count and files_changed.

    Args:
        name: The intern's GitHub username (must match pusher_name exactly)
        xp_awarded: XP to award for this push
        commit_count: Number of commits in the push
        files_changed: Number of distinct files touched
        commit_sha: The push's head commit sha — copy it exactly from the message

    Returns:
        Confirmation message with the intern's new total XP
    """
    payload = {"name": name, "xp_awarded": xp_awarded,
               "commit_count": commit_count, "files_changed": files_changed,
               "commit_sha": commit_sha}
    response = await asyncio.to_thread(
        requests.post, f"{SERVER_URL}/xp", json=payload, timeout=10
    )
    response.raise_for_status()
    data = response.json()
    return f"Awarded {xp_awarded} XP to {name}. New total: {data['total_xp']}."






root_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name='root_agent',
    description='A helpful assistant for user questions.',
    instruction=(
        "You evaluate one GitHub push and award XP to the intern who made it.\n"
        "You'll receive their name, commit count, and files changed.\n"
        "1. Decide a fair XP amount from commit_count and files_changed.\n"
        "2. Call assign_xp once with the intern's name, your XP decision, and commit_sha copied exactly from the message.\n"
        "Always use the provided tools rather than describing function calls in text."
        "Call assign_xp exactly ONCE per push. Once you receive a successful tool result, you are done — respond with a short confirmation and STOP. Do not call assign_xp again for the same push, even if you think a different amount would be more fair. If the tool result says the commit was already processed, respond with a short confirmation and STOP — do not call assign_xp again."
    ),
    tools = [assign_xp]
)

