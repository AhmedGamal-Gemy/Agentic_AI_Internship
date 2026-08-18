import os

from dotenv import load_dotenv
from exa_py import Exa

load_dotenv()

exa = Exa(api_key=os.getenv("EXA_API_KEY"))


def exa_search(query: str) -> str:
    """Search the web for current, relevant information on a topic.

    Use this to ground a solution in real reference material (known
    algorithms, edge cases, community discussions) instead of relying
    on model memory alone.

    Args:
        query: The search topic or question

    Returns:
        A short summary of the most relevant search results
    """
    results = exa.search(query, type="auto", num_results=5, contents={"highlights": True})

    lines = []
    for item in results.results:
        highlight = item.highlights[0] if item.highlights else ""
        lines.append(f"- {item.title}: {highlight}")

    return "\n".join(lines) if lines else "No results found."