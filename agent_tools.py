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


def exa_search(query: str) -> str:
    """Search the web for current, relevant information on a topic.

    Use this before generating a challenge to ground it in real,
    up-to-date examples rather than relying on memory alone.

    Args:
        query: The search topic or question

    Returns:
        A short summary of the most relevant search results
    """
    results = exa.search_and_contents(
        query, type="auto", num_results=5, highlights=True
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
    payload = {"topic": topic, "difficulty": difficulty, "description": description, "solution" : solution}

    response = requests.post(f"{SERVER_URL}/save", json=payload, timeout=5)

    response.raise_for_status()

    data = response.json()
    
    return f"Saved challenge with ID {data['id']}"


def push_to_leaderboard(topic: str, difficulty: str, description: str) -> str:
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
    payload = {"topic": topic, "difficulty": difficulty, "description": description}

    response = requests.post(f"{SERVER_URL}/challenge", json=payload, timeout=5)
    
    response.raise_for_status()
    
    return "Challenge posted to leaderboard live!"
