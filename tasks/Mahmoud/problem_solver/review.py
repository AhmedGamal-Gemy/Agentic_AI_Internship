"""Review Agent — reviews each completed task; the gate between tasks."""

from __future__ import annotations

from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm


def review_step(step_id: int, output: str, acceptable: bool, notes: str) -> str:
    """Review the result of a single step before moving on.

    This is the gate: if the output is NOT acceptable, the caller must redo
    this step (call execute_step again for the same step_id) and re-review.
    Only proceed to the next step after this returns ACCEPTED.

    Args:
        step_id: The step number that was just executed
        output: The result produced by execute_step for this step
        acceptable: Whether the output satisfies the step requirements
        notes: Brief justification for the verdict

    Returns:
        ACCEPTED or REJECTED verdict; REJECTED means redo before continuing
    """
    if acceptable:
        return f"Step {step_id} ACCEPTED ({notes}). Continue to the next step."
    return (
        f"Step {step_id} REJECTED ({notes}). Do NOT continue. "
        f"Redo step {step_id} with execute_step, then re-review."
    )


def complete_task(problem: str, summary: str) -> str:
    """Finalize the task once every plan step has been reviewed and accepted.

    Args:
        problem: The original problem
        summary: The final solution summary produced after review

    Returns:
        Final hand-off message for the problem
    """
    return f"Problem solved: {problem}\n{summary}"


review_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name="Review_Agent",
    description="Reviews each completed task and gates progress to the next task.",
    instruction="""
You are the Review Agent of a Problem Solver system.

When given a completed task:
1. Call review_step with the step id, the task output, acceptable=true/false,
   and short notes.
2. If it returns REJECTED, report the rejection — do NOT let the workflow
   continue.
3. Only after all steps are ACCEPTED, call complete_task with the original
   problem and the final summary.

Never approve a task that does not satisfy its requirements.
Always use the provided tools rather than describing function calls in text.
""",
    tools=[review_step, complete_task],
)