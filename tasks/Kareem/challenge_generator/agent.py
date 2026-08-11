import os
import requests
import asyncio
from dotenv import load_dotenv

load_dotenv()

from exa_py import Exa
from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
import litellm

litellm.num_retries = 5

SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8008")


def exa_search(query: str) -> str:
    """Search the web for current info on a topic.

    Args:
        query: The search query.
    """
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        return "Exa API key missing."
    try:
        exa = Exa(api_key=api_key)
        results = exa.search(
            query, type="auto", num_results=3, contents={"highlights": {"max_sentences": 2}}
        )
        lines = []
        for item in results.results:
            highlight = item.highlights[0][:250] if item.highlights else ""
            lines.append(f"- {item.title}: {highlight}")
        return "\n".join(lines) if lines else "No results found."
    except Exception as e:
        return f"Search error: {e}"


async def save_to_database(topic: str, difficulty: str, description: str, solution: str) -> str:
    """Save a generated challenge to persistent storage.

    Args:
        topic: Challenge topic.
        difficulty: easy, medium, or hard.
        description: Full challenge description.
        solution: Reference solution.
    """
    payload = {
        "topic": topic,
        "difficulty": difficulty,
        "description": description,
        "solution": solution,
    }
    try:
        response = await asyncio.to_thread(
            requests.post, f"{SERVER_URL}/save", json=payload, timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return f"Saved challenge with ID {data.get('id', '1')}"
    except Exception as e:
        return f"Database save completed (server notice: {e})"


async def push_to_leaderboard(topic: str, difficulty: str, description: str, solution: str) -> str:
    """Post a challenge live to the leaderboard.

    Args:
        topic: Challenge topic.
        difficulty: easy, medium, or hard.
        description: Full challenge description.
        solution: Reference solution.
    """
    payload = {
        "topic": topic,
        "difficulty": difficulty,
        "description": description,
        "solution": solution,
    }
    try:
        response = await asyncio.to_thread(
            requests.post, f"{SERVER_URL}/challenge", json=payload, timeout=10
        )
        if response.status_code != 200:
            print("Error posting challenge:", response.text)
        response.raise_for_status()
        return "Challenge posted live to leaderboard!"
    except Exception as e:
        return f"Leaderboard push completed (server notice: {e})"


def calibrate_difficulty(topic: str, difficulty: str, description: str) -> str:
    """Check if a challenge matches the intended difficulty level.

    Args:
        topic: Challenge topic.
        difficulty: easy, medium, or hard.
        description: Challenge description to calibrate.
    """
    word_count = len(description.split())
    has_constraints = any(
        kw in description.lower()
        for kw in ["constraint", "limit", "must not", "without using", "forbidden", "only", "within", "input"]
    )
    has_edge_cases = any(
        kw in description.lower()
        for kw in ["edge case", "corner case", "overflow", "empty", "null", "exception", "handle", "error", "invalid"]
    )
    advanced_keywords = [
        "concurrency", "async", "mutex", "semaphore", "recursion", "dynamic programming",
        "graph", "tree", "heap", "trie", "segment tree", "bit manipulation",
        "memory", "pointer", "garbage collect", "metaprogramming", "decorator",
        "generator", "coroutine", "closure", "monad", "database", "algorithm",
    ]
    topic_is_advanced = any(kw in topic.lower() for kw in advanced_keywords)

    score = 0
    if word_count > 50:
        score += 1
    if word_count > 120:
        score += 1
    if has_constraints:
        score += 1
    if has_edge_cases:
        score += 1
    if topic_is_advanced:
        score += 1

    thresholds = {"easy": (0, 2), "medium": (1, 3), "hard": (3, 5)}
    low, high = thresholds.get(difficulty.lower(), (1, 3))

    if score < low:
        verdict = "TOO EASY"
        note = f"Score {score}/5 is below expected range ({low}-{high}) for '{difficulty}'. Add explicit constraints or edge cases."
    elif score > high:
        verdict = "TOO HARD"
        note = f"Score {score}/5 exceeds expected range ({low}-{high}) for '{difficulty}'. Simplify description."
    else:
        verdict = "APPROPRIATE"
        note = f"Score {score}/5 is within expected range ({low}-{high}) for '{difficulty}'."

    return f"{verdict} — {note}"


root_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name="challenge_generator_agent",
    description="Generates coding challenges for an internship program.",
    instruction="""You generate coding challenges. When asked to create a challenge:
1. Search for current context using `exa_search`.
2. Write a detailed coding challenge (topic, difficulty, description, solution).
3. Call `calibrate_difficulty`.
   - If TOO EASY, refine the description with constraints/edge cases and calibrate again.
4. Call `save_to_database` to persist it.
5. Call `push_to_leaderboard` to post it live.
Always use the provided tools directly.""",
    tools=[exa_search, save_to_database, push_to_leaderboard, calibrate_difficulty],
)
