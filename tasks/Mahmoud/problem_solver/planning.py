"""Planning Agent — turns research findings into a numbered implementation plan."""

from __future__ import annotations

from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm


def build_plan(problem: str, research: str) -> str:
    """Turn the problem and research findings into a numbered implementation plan.

    Args:
        problem: The problem to solve
        research: The research findings produced by the Research Agent

    Returns:
        A numbered plan; each step must be executed and reviewed one at a time
    """
    steps = [
        f"Step 1: Clarify the problem statement and constraints for: {problem}",
        "Step 2: Draft a solution approach grounded in the research.",
        "Step 3: Write the concrete deliverable (code / answer).",
        "Step 4: Verify the deliverable against the problem requirements.",
    ]
    return "\n".join(steps)


planning_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name="Planning_Agent",
    description="Turns research findings into a numbered implementation plan.",
    instruction="""
You are the Planning Agent of a Problem Solver system.

When given a problem and research findings:
1. Call build_plan with the problem and the research. WAIT for the result.
2. Return the plan verbatim as your final answer.

Never skip research and never invent steps beyond what build_plan returns.
Always use the provided tools rather than describing function calls in text.
""",
    tools=[build_plan],
)