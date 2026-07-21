from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
import redis
import os
import json


#def push_to_leaderboard(challenge : str) -> str:
#    """ function to show the challenge """

#    return f"Challenge is {challenge}"




"""
Real tool implementations for the Challenge Generator agent.
Replaces the Session 1 stubs (save_to_database, push_to_leaderboard)
and adds the new exa_search tool.

Drop these functions into challenge_generator/agent.py, replacing the
stub versions, and add them to the agent's `tools=[...]` list.
"""

import os
import requests
from exa_py import Exa

SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8007")
exa = Exa(api_key=os.getenv("EXA_API_KEY"))

r = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    username=os.getenv("REDIS_USERNAME"),
    password=os.getenv("REDIS_PASSWORD"),
    decode_responses=True,
)

def exa_search(query: str) -> str:
    """Search the web for current, relevant information on a topic.

    Use this before generating a challenge to ground it in real,
    up-to-date examples rather than relying on memory alone.

    Args:
        query: The search topic or question

    Returns:
        A short summary of the most relevant search results
    """
    results = exa.search(
        query, type="auto", num_results=5, contents={"highlights": True}
    )
    
    lines = []
    
    for item in results.results:
        highlight = item.highlights[0] if item.highlights else ""
        lines.append(f"- {item.title}: {highlight}")
    
    return "\n".join(lines) if lines else "No results found."



def save_to_database(topic: str, difficulty: str, description: str, solution : str) -> str:
    """Save a generated challenge to persistent storage.

    This keeps a permanent record of every challenge ever generated,
    separate from what's currently shown on the leaderboard.

    Args:
        topic: The challenge topic
        difficulty: One of "easy", "medium", or "hard"
        description: The full challenge description

    Returns:
        Confirmation message including the saved challenge's ID
    """
    
    payload = {
        "topic": topic, 
        "difficulty": difficulty, 
        "description": description, 
        "solution" : solution
        }

    response = requests.post(f"{SERVER_URL}/save", json=payload, timeout=5)

    response.raise_for_status()

    data = response.json()
    
    return f"Saved challenge with ID {data['id']}"


def push_to_leaderboard(topic: str, difficulty: str, description: str, solution: str) -> str:
     """Post a challenge live to the leaderboard display.

     This sets the CURRENT challenge shown on the leaderboard HTML —
     it updates within 5 seconds on the projector.

     Args:
         topic: The challenge topic
         difficulty: One of "easy", "medium", or "hard"
         description: The full challenge description

     Returns:
         Confirmation message
     """
     payload = {"topic": topic, "difficulty": difficulty, "description": description, "solution" : solution}

     response = requests.post(f"{SERVER_URL}/challenge", json=payload, timeout=5)
     if response.status_code != 200:
         print("VALIDATION ERROR:", response.text)  # shows exactly what's wrong
     response.raise_for_status()
    
     return "Challenge posted to leaderboard live!"

def check_duplicate_challenge(description: str) -> str:
    """Verify whether a the new challenge is too similar to an existing one..
    Args:
        new_challenge: The new challenge to check for duplicates
    Returns:
     A message indicating whether the challenge is a duplicate or not
    """
    for record in r.lrange("challenge_log", 0, -1):
        existing_challenge = json.loads(record)
        if description == existing_challenge["description"]:
            return "Duplicate challenge found."
    return "No duplicate challenge found."

root_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name='Challenge_Generator',
    description='A helpful assistant for generating coding challenges for an internship',
    instruction = """
    You are a Challenge Generator agent. Follow this sequence:

    1. Call exa_search with a query related to the requested topic. WAIT for the result.
    2. Using the search results, write a challenge with a topic, difficulty, description, and solution.
    3. Call check_duplicate_challenge with the challenge description to ensure it is not a duplicate.
    4. Call save_to_database AND push_to_leaderboard TOGETHER in the same turn, both with the same challenge details if it is not a duplicate.

    Do not call exa_search at the same time as the other tools — it must run first, alone, since you need its results before writing the challenge. But save_to_database and push_to_leaderboard should always be called together in a single turn once the challenge is written.
    """,
    tools=[save_to_database,exa_search,push_to_leaderboard,check_duplicate_challenge]
)