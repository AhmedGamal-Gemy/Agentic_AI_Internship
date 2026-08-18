from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
from .sandbox import run_code

import google.adk.models.lite_llm as _adk_lite_llm

# gpt-oss on Groq streams `reasoning_content`, which ADK stores and Groq
# then rejects when the assistant message is resent. Ignore the reasoning
# stream entirely (we only need the final answer).
_adk_lite_llm._extract_reasoning_value = lambda message: None

planner = Agent(
    name="planner",
    model=LiteLlm("groq/openai/gpt-oss-120b"),
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
    model=LiteLlm("groq/openai/gpt-oss-120b"),
    instruction="""You receive a coding problem and the planner's plan {plan?}.
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
    model=LiteLlm("groq/openai/gpt-oss-120b"),
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

root_agent = Agent(
    model=LiteLlm("groq/openai/gpt-oss-120b"),
    name='root_agent',
    description='A helpful assistant for user questions.',
    instruction='Answer user questions to the best of your knowledge',
)
