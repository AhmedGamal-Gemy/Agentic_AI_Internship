from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
from exa_py import Exa
import os
import requests
import os
from dotenv import load_dotenv
load_dotenv()

exa = Exa(api_key=os.getenv("EXA_API_KEY"))
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8007")

async def exa_search(query: str) -> str:
    exaaaaa = exa.search_and_contents(
        query,
        num_results=3,
        highlights=True,
    )

    lines = []
    for item in exaaaaa.results:
        highlight = item.highlights[0] if item.highlights else ""
        lines.append(f"- {item.title}: {highlight}")

    return "\n".join(lines) if lines else "No results found."
####################################################################################################
async def save_to_database(topic: str, difficulty: str, description: str, solution : str) -> str:
    """Save a generated challenge to persistent storage.

    This keeps a permanent record of every challenge ever generated,
    separate from what's currently shown on the leaderboard.

    Args:
        topic: The challenge topic
        difficulty: One of "easy", "medium", or "hard"
        description: The full challenge description
        solution: The solution to the challenge

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


async def push_to_leaderboard(topic: str, difficulty: str, description: str, solution: str) -> str:
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


def check_duplicate_challenge():
    pass
########################################################################

"""Basic connection example.
"""

import redis

r = redis.Redis(
    host='passenger-eggnog-yare-15195.db.redis.io',
    port=10942,
    decode_responses=True,
    username="default",
    password="6UQIXRLDPSCf3PjM2zZc8MVha9f6zJbO",
)

success = r.set('foo', 'bar')
# True

result = r.get('foo')
print(result)
# >>> bar




root_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name="root_agent",
    description='A helpful assistant for user questions.',
    instruction='Answer user questions to the best of your knowledge',
    tools=[save_to_database, push_to_leaderboard, exa_search]
)
