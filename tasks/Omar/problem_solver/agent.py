from typing import AsyncGenerator

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.llm_agent import Agent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.events.event import Event
from google.adk.models.lite_llm import LiteLlm
from google.adk.utils.context_utils import Aclosing
from .sandbox import run_code

import litellm

litellm.num_retries = 10  # auto-retries on RateLimitError/APIError with exponential backoff

import google.adk.models.lite_llm as _adk_lite_llm

# gpt-oss on Groq streams `reasoning_content`, which ADK stores and Groq
# then rejects when the assistant message is resent. Ignore the reasoning
# stream entirely (we only need the final answer).
_adk_lite_llm._extract_reasoning_value = lambda message: None

model = LiteLlm("groq/openai/gpt-oss-120b", max_tokens=4096)

planner = Agent(
    name="planner",
    model=model,
    instruction="""You receive a coding problem from the user.
Analyze it and output ONLY a structured plan with these sections:
1. Approach: the algorithm/strategy to use and why.
2. Steps: implementation steps in order.
3. Edge cases: tricky inputs the solution must handle.
4. Tests: 2-3 sample test cases written as (input -> expected output).
Do not write any code, do not output anything besides the plan.""",
    output_key="plan",
    disallow_transfer_to_peers=True,
)

coder = Agent(
    name="coder",
    model=model,
    instruction="""You receive a coding problem and the planner's plan {plan?}.
If a previous verdict from the verifier exists {verdict?} and it starts with "rejected", fix exactly the issues it lists.
Write a complete, runnable Python solution that follows the plan:
1. A function (or class) that solves the problem.
2. A __main__ block that runs every sample test from the plan
   and prints "PASS: <input> -> <output>" or "FAIL: expected <expected>, got <actual>".
Output ONLY the Python code, no explanations.""",
    output_key="solution",
    disallow_transfer_to_peers=True,
)

verifier = Agent(
    name="verifier",
    model=model,
    instruction="""You receive a coding problem, the planner's plan {plan?}, and the coder's solution {solution?}.
1. Call the run_code tool with the solution to execute it, then inspect exit_code, stdout, and stderr.
2. A traceback, nonzero exit_code, timeout, or any "FAIL" line in stdout means the solution is NOT verified.
   Every sample test must print "PASS".
3. Also review the logic against the problem and the plan for mistakes the tests may miss.
Output ONLY one of:
- If the solution runs and passes all checks: "approved" followed by the final verified solution code.
- Otherwise: "rejected" followed by specific, actionable feedback: what is wrong and exactly how to fix it.""",
    output_key="verdict",
    tools=[run_code],
    disallow_transfer_to_peers=True,
)

pipeline = SequentialAgent(
    name="pipeline",
    sub_agents=[planner, coder, verifier],
)

responder = Agent(
    name="responder",
    model=model,
    instruction="""You are the final output step of a problem-solving pipeline. You receive the verifier's verdict {verdict?}.
If it starts with "approved": output ONLY the solution code from the verdict, with any markdown code fences removed. Nothing else.
If it starts with "rejected" or is empty: output exactly "No verified solution was produced after 3 attempts." Nothing else.""",
    disallow_transfer_to_peers=True,
)

class VerifyFixOrchestrator(BaseAgent):
    """Deterministic orchestrator: runs the pipeline, re-runs it while the
    verdict is rejected (max_attempts times), then lets the responder print
    the final verified solution."""

    max_attempts: int = 3

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        for _ in range(self.max_attempts):
            async with Aclosing(pipeline.run_async(ctx)) as agen:
                async for event in agen:
                    yield event
            verdict = ctx.session.state.get("verdict") or ""
            if verdict.startswith("approved"):
                break
        async with Aclosing(responder.run_async(ctx)) as agen:
            async for event in agen:
                yield event


root_agent = VerifyFixOrchestrator(
    name="Orchestrator",
    max_attempts=3,
    description="Decomposes coding problems, delegates to specialist agents, and returns a verified solution.",
    sub_agents=[pipeline, responder],
)
