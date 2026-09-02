"""Research Agent — researches the user's problem using Exa Search."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from exa_py import Exa
from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

load_dotenv()

# Read once from the environment; never hardcode credentials in source.
EXA_API_KEY = os.getenv("EXA_API_KEY")
exa = Exa(api_key=EXA_API_KEY) if EXA_API_KEY else None


def research_problem(problem: str) -> str:
    """Search the web for current, relevant information about the problem.

    Args:
        problem: The problem to research

    Returns:
        Bullet-point findings and their sources from the most relevant results
    """
    if exa is None:
        return "No EXA_API_KEY set; skipping research."
    results = exa.search(
        problem, type="auto", num_results=5, contents={"highlights": True}
    )
    lines = []
    for item in results.results:
        highlight = item.highlights[0] if item.highlights else ""
        source = getattr(item, "url", "")
        lines.append(f"- {item.title}: {highlight[:300]} ({source})")
    return "\n".join(lines) if lines else "No results found."


research_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name="Research_Agent",
    description="Researches the user's problem using Exa Search and returns "
    "findings with sources.",
    instruction="""
You are the Research Agent of a Problem Solver system.

When given a problem:
1. Call research_problem with the exact problem text. WAIT for the result.
2. Return the findings verbatim, including the sources, as your final answer.

Never invent search results. If research is unavailable, say so.
Always use the provided tools rather than describing function calls in text.
""",
    tools=[research_problem],
)