"""Problem Solver Agent — researches, plans, delegates, executes one task at a
time, and reviews each result before continuing."""

from __future__ import annotations

import os
from typing import Dict, List

from dotenv import load_dotenv
from exa_py import Exa
from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

load_dotenv()

EXA_API_KEY = os.getenv("EXA_API_KEY")
exa = Exa(api_key=EXA_API_KEY) if EXA_API_KEY else None


def research_problem(problem: str) -> str:
    """Search the web for current, relevant information about the problem.

    Use this FIRST, before planning, so the solution is grounded in real
    facts rather than memory alone.

    Args:
        problem: The problem to solve

    Returns:
        Bullet-point summary of the most relevant search results
    """
    if exa is None:
        return "No EXA_API_KEY set; skipping research."
    results = exa.search(
        problem, type="auto", num_results=5, contents={"highlights": True}
    )
    lines = []
    for item in results.results:
        highlight = item.highlights[0] if item.highlights else ""
        lines.append(f"- {item.title}: {highlight[:300]}")
    return "\n".join(lines) if lines else "No results found."


def build_plan(problem: str, research: str) -> str:
    """Turn the problem into a short numbered execution plan.

    Call this AFTER research_problem and BEFORE any execute_step call.

    Args:
        problem: The problem to solve
        research: The research summary produced by research_problem

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


_STEPS: Dict[int, str] = {}


def execute_step(step_id: int, action: str) -> str:
    """Execute exactly ONE step of the plan.

    Do not execute more than one step per call — the caller must review each
    result before continuing to the next step.

    Args:
        step_id: The step number to execute (1-based, from build_plan)
        action: The concrete action taken for this step

    Returns:
        Confirmation of what was executed for the step
    """
    _STEPS[step_id] = action
    return f"Executed step {step_id}: {action}"


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

    Call this only after all steps returned ACCEPTED.

    Args:
        problem: The original problem
        summary: The final solution summary produced after review

    Returns:
        Final hand-off message for the problem
    """
    _STEPS.clear()
    return f"Problem solved: {problem}\n{summary}"


agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name="Problem_Solver",
    description="Orchestrator that researches, plans, executes one task at a "
    "time, and reviews each result before continuing.",
    instruction="""
You are a Problem Solver orchestrator. Solve the user's problem step by step,
executing and reviewing ONE step at a time:

1. Call research_problem with the problem. WAIT for the result.
2. Call build_plan with the problem and the research. WAIT for the plan.
3. Call execute_step with the FIRST step id and a concrete action.
4. Call review_step with that step's id, output, acceptable=true/false, and
   short notes. If it returns REJECTED, redo the step (execute_step with the
   SAME step id) and re-review. Do NOT move to the next step until ACCEPTED.
5. Repeat steps 3-4 for each remaining step, one at a time.
6. Only after every step is ACCEPTED, call complete_task with the problem and
   a final summary.

Never execute multiple steps or skip the review gate between steps.
Always use the provided tools rather than describing function calls in text.
""",
    tools=[
        research_problem,
        build_plan,
        execute_step,
        review_step,
        complete_task,
    ],
)