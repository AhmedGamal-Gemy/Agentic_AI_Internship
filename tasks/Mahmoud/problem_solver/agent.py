"""Problem Solver Agent — root orchestrator that delegates to specialized
sub-agents: Research, Planning, Implementer, and Review."""

from __future__ import annotations

from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

from .implementer import execute_step, implementer_agent
from .planning import build_plan, planning_agent
from .research import research_agent, research_problem
from .review import complete_task, review_agent, review_step

# Re-export the tool functions so existing callers keep working.
__all__ = [
    "agent",
    "research_problem",
    "build_plan",
    "execute_step",
    "review_step",
    "complete_task",
]

agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name="Problem_Solver",
    description="Orchestrator that researches, plans, delegates to specialized "
    "agents, executes one task at a time, and reviews each result before "
    "continuing.",
    instruction="""
You are the Problem Solver orchestrator. You do NOT solve problems directly —
you delegate each phase to a specialized sub-agent and only proceed after the
phase result is produced.

Available sub-agents:
- Research_Agent: researches the problem with Exa Search.
- Planning_Agent: turns problem + research into a numbered implementation plan.
- Implementer_Agent: executes exactly ONE task of the plan.
- Review_Agent: reviews a completed task and gates progress.

Workflow (strictly one phase at a time, wait for each result):
1. Delegate to Research_Agent with the user's problem. WAIT for findings.
2. Delegate to Planning_Agent with the problem and the research. WAIT for plan.
3. Delegate to Implementer_Agent for the FIRST task only. WAIT for the result.
4. Delegate to Review_Agent to review that task. WAIT for the verdict.
   - If REJECTED: stop. Report the rejection to the user.
   - If ACCEPTED: report the task result to the user and STOP — never start
     the next task automatically. A human must approve before continuing.
5. Never execute two tasks after a single instruction, and never skip the
   review gate between tasks.

Always delegate through sub-agents rather than performing their work yourself.
""",
    sub_agents=[research_agent, planning_agent, implementer_agent, review_agent],
)