from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
from exa_py import Exa

import os
import requests
import asyncio

import litellm
litellm.num_retries = 10
from dotenv import load_dotenv
load_dotenv()

SERVER_URL = os.getenv("SERVER_URL")

exa = Exa(api_key=os.getenv("EXA_API_KEY"))

def exa_search(query: str) -> str:
    """Search the web for current, relevant information on a topic.
    Use this before generating a challenge to ground it in real,
    up-to-date examples rather than relying on memory alone.
    Args:
        query: The search topic or question
    Returns:
        A short summary of the most relevant search results
    """
    exaaaaa = exa.search(
        query, type="auto", num_results=5, contents={"highlights": True}
    )
    
    lines = []

    for item in exaaaaa.results:
        highlight = item.highlights[0] if item.highlights else ""
        highlight = highlight[:300]  # cap each highlight
        lines.append(f"- {item.title}: {highlight}")
    
    return "\n".join(lines) if lines else "No results found."

async def save_to_database(topic: str, difficulty: str, description: str, solution : str) -> str:
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
    response = await asyncio.to_thread(
        requests.post, f"{SERVER_URL}/save", json=payload, timeout=10
    )
    response.raise_for_status()
    data = response.json()    
    return f"Saved challenge with ID {data['id']}"

async def current_challenge(topic, difficulty, description, solution):
    payload = {
        "topic": topic,
        "difficulty": difficulty,
        "description": description,
        "solution": solution,
    }
    response = await asyncio.to_thread(
            requests.post, f"{SERVER_URL}/save", json=payload, timeout=10
        )
    response.raise_for_status()
    return response.json()["status"]

async def push_to_leaderboard(topic: str, difficulty: str, description: str, solution: str) -> str:
    """Post a challenge live to the leaderboard display.
    This sets the CURRENT challenge shown on the leaderboard HTML —
    it updates within 5 seconds on the projector.
    Args:
        topic: The challenge topic
        difficulty: One of "easy", "medium", or "hard"
        description: The full challenge description
        solution: The solution to the challenge
    Returns:
        Confirmation message
    """
    payload = {"topic": topic, "difficulty": difficulty, "description": description, "solution" : solution}
    response = await asyncio.to_thread(
        requests.post, f"{SERVER_URL}/challenge", json=payload, timeout=10
    )
    if response.status_code != 200:
        print("VALIDATION ERROR:", response.text)  
    response.raise_for_status()    
    return "Challenge posted to leaderboard live!"


root_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name='Challenge_Generator',
    description='A helpful assistant for user questions.',
    instruction='''You generate coding challenges.
    When you are asked to create a challenge:
    1. Call exa_search and wait.
    2. Generate the challenge.
    3. Call save_to_database and wait.
    4. Call current_challenge and wait.
    5. Call push_to_leaderboard and wait.
    6. Show the challenge to the user.
    Never call more than one tool at the same time & Always use the provided tools rather than describing function calls in text.''',
    tools=[exa_search,save_to_database,current_challenge,push_to_leaderboard]
)
