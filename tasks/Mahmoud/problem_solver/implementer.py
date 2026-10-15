"""Implementation Agent — executes exactly one task at a time."""

from __future__ import annotations

from typing import Dict

from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

_STEPS: Dict[int, str] = {}


def execute_step(step_id: int, action: str) -> str:
    """Execute exactly ONE task/step of the plan.

    Do not execute more than one step per call — the caller must review each
    result before continuing to the next step.

    Args:
        step_id: The step number to execute (1-based, from the plan)
        action: The concrete action taken for this step

    Returns:
        Confirmation of what was executed for the step
    """
    _STEPS[step_id] = action
    return f"Executed step {step_id}: {action}"


implementer_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name="Implementer_Agent",
    description="Executes exactly one task of the plan at a time.",
    instruction="""
You are the Implementer Agent of a Problem Solver system.

When given a single task:
1. Call execute_step with the task's step id and a concrete action.
2. Return the confirmation as your final answer.

Never execute more than one task per call, and never modify code outside the
task you were asked to implement.
Always use the provided tools rather than describing function calls in text.
""",
    tools=[execute_step],
)