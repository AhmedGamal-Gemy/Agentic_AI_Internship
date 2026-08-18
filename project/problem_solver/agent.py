from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import ToolContext

from problem_solver.code_executor import get_code_executor
from problem_solver.tools import exa_search

MODEL_GROQ = "groq/llama-3.3-70b-versatile"
MODEL_OPENAI = "openai/gpt-4o"

MAX_ATTEMPTS = 3


def store_plan(plan: str, tool_context: ToolContext) -> str:
    """Save the step-by-step solving plan to the shared session state.

    Call this once the plan is finalized so the solver can read it later.

    Args:
        plan: The full plan text (steps, edge cases, expected complexity)

    Returns:
        Confirmation message
    """
    tool_context.state["plan"] = plan
    return "Plan saved to state."


def get_plan(tool_context: ToolContext) -> str:
    """Read the plan previously saved by the planner.

    Returns:
        The saved plan text, or a message if none exists
    """
    return tool_context.state.get("plan", "No plan in state yet.")


def store_solution(
    code: str, tests: str, explanation: str, tool_context: ToolContext
) -> str:
    """Save the final verified solution to the shared session state.

    Only call this AFTER the code passed execution in the sandbox.

    Args:
        code: The final solution code
        tests: The test cases that were run and passed
        explanation: How the solution works and its complexity

    Returns:
        Confirmation message
    """
    tool_context.state["solution"] = {
        "code": code,
        "tests": tests,
        "explanation": explanation,
    }
    return "Solution saved to state."


def get_solution(tool_context: ToolContext) -> str:
    """Read the solution saved by the solver for review.

    Returns:
        The saved solution (code, tests, explanation), or a message if none
    """
    sol = tool_context.state.get("solution")
    if not sol:
        return "No solution in state yet."
    return f"CODE:\n{sol['code']}\n\nTESTS:\n{sol['tests']}\n\nEXPLANATION:\n{sol['explanation']}"


def get_attempt_count(tool_context: ToolContext) -> str:
    """Read how many times the solver has already attempted this problem.

    Returns:
        The attempt number as a string
    """
    return str(tool_context.state.get("attempts", 0))


def increment_attempt(tool_context: ToolContext) -> str:
    """Increment the solver attempt counter in the session state.

    Returns:
        The new attempt number
    """
    attempts = tool_context.state.get("attempts", 0) + 1
    tool_context.state["attempts"] = attempts
    return str(attempts)


planner_agent = Agent(
    name="planner",
    model=LiteLlm(model=MODEL_GROQ),
    description="Decomposes a coding problem into a clear step-by-step solving plan with edge cases and complexity targets. Call this agent first for any new problem.",
    instruction="""You are the Planner agent. Your ONLY job is to produce a high-quality solving plan.

1. Read the problem carefully.
2. Decompose it into concrete steps: input parsing, core algorithm, output formatting.
3. List edge cases (empty input, single element, large inputs, duplicates, negatives).
4. State the expected time and space complexity.
5. Call store_plan with the full plan.
6. Reply with a short confirmation of the plan. Do not write code.""",
    tools=[store_plan],
)

researcher_agent = Agent(
    name="researcher",
    model=LiteLlm(model=MODEL_GROQ),
    description="Searches the web for context on algorithms or tricky concepts relevant to the problem. Use only when the problem involves a non-obvious technique.",
    instruction="""You are the Researcher agent. Your ONLY job is web research.

1. Call exa_search with a focused query about the algorithm/technique needed for this problem.
2. Summarize the most relevant findings in 3-5 bullet points.
3. Reply with the summary. Do not write code and do not call any other tools.""",
    tools=[exa_search],
)

solver_agent = Agent(
    name="solver",
    model=LiteLlm(model=MODEL_OPENAI),
    description="Writes the Python solution and test cases, executes them in a sandboxed container, and iterates until all tests pass.",
    instruction=f"""You are the Solver agent. Your ONLY job is to produce a solution verified by execution.

1. Call get_plan to read the plan (and optionally get_attempt_count).
2. If a previous critique is in the conversation, incorporate its feedback.
3. Write your solution AND test cases inside ONE python code block (```python ... ```). The sandbox will execute it automatically and return results in a ```tool_output block.
   - The code must PRINT the test results (e.g. assert statements, or prints of expected vs actual).
4. Inspect the tool_output. If any test fails or the code errors: fix the code, re-run it in a new code block, and repeat. You may iterate up to {MAX_ATTEMPTS} times total.
5. Only when all tests pass: call store_solution with the final code, the tests, and a short explanation with complexity. Also call increment_attempt.
6. Reply confirming the solution passed execution. Never claim success without seeing passing tool_output.""",
    tools=[get_plan, get_attempt_count, store_solution, increment_attempt],
    code_executor=get_code_executor(),
)

critic_agent = Agent(
    name="critic",
    model=LiteLlm(model=MODEL_GROQ),
    description="Reviews the solver's solution against a correctness checklist and returns PASS or a list of concrete fixes.",
    instruction="""You are the Critic agent. Your ONLY job is to review the stored solution.

1. Call get_solution to read the solution code, tests, and explanation.
2. Review against this checklist:
   - Correctness: does the logic handle the problem's core cases?
   - Edge cases: empty, single element, large inputs, duplicates, negatives?
   - Tests: do the tests actually cover the edge cases above?
   - Complexity: is it within the plan's target?
   - Style: any obvious bugs or unused variables?
3. If it passes: reply "VERDICT: PASS" plus one short paragraph.
4. If it fails: reply "VERDICT: FAIL" followed by a numbered list of the exact concrete fixes needed. Be specific.""",
    tools=[get_solution],
)

root_agent = Agent(
    name="orchestrator",
    model=LiteLlm(model=MODEL_GROQ),
    description="Receives a coding problem from the user and coordinates planner, researcher, solver, and critic to deliver a verified solution.",
    instruction=f"""You are the Orchestrator agent coordinating a problem-solving team.

For every new problem follow this flow:

1. Transfer to the planner agent first (transfer_to_planner). WAIT for its plan.
2. If the problem involves a non-obvious algorithm, transfer to the researcher agent (transfer_to_researcher). Otherwise skip.
3. Transfer to the solver agent (transfer_to_solver). WAIT for confirmation that tests passed.
4. Transfer to the critic agent (transfer_to_critic). WAIT for its verdict.
5. If the verdict is FAIL and the solver has attempted fewer than {MAX_ATTEMPTS} times (the solver reports this): transfer back to the solver (transfer_to_solver) telling it the critic's exact feedback. Then repeat the critic review.
6. If the verdict is PASS (or attempts are exhausted): write the FINAL ANSWER:
   - State "VERIFIED" only if the critic said PASS.
   - Present the solution code, the tests run, and the explanation.
   - If attempts were exhausted without PASS, present the best solution with a clear "NOT FULLY VERIFIED" warning and the critic's remaining concerns.

Never present an answer as verified unless the critic said PASS. Never attempt the problem yourself — always delegate.""",
    sub_agents=[planner_agent, researcher_agent, solver_agent, critic_agent],
)