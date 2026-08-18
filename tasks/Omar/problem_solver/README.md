# Problem Solver Agent

An ADK-based agent that takes a coding problem from the user, delegates it to
specialist sub-agents, and returns a **verified** solution.

## Architecture

```
user problem
   │
   ▼
Orchestrator (VerifyFixOrchestrator, deterministic)
   │  runs pipeline up to 3 times while verdict is "rejected"
   ▼
pipeline (SequentialAgent)
   ├── planner   → writes {plan}      (approach, steps, edge cases, sample tests)
   ├── coder     → writes {solution}  (runnable Python + PASS/FAIL test harness)
   └── verifier  → writes {verdict}   (executes code in a sandbox, approves/rejects)
   │
   ▼
responder → prints the final verified solution code
```

- **planner** analyzes the problem and produces a plan (approach, steps, edge
  cases, sample tests).
- **coder** writes a runnable Python solution with a `__main__` block that runs
  the planner's sample tests and prints PASS/FAIL per case.
- **verifier** executes the solution via the `run_code` sandbox tool
  (`sandbox.py`, isolated subprocess, 10s timeout) and reviews the logic. It
  outputs `approved` + final code, or `rejected` + actionable feedback.
- **Orchestrator** re-runs the pipeline while the verdict is `rejected`
  (max 3 attempts) so the coder can fix the issues, then hands off to the
  **responder**, which prints the verified solution.
- No LLM orchestration: the flow is deterministic Python, so delegation order
  and the fix loop cannot be skipped by the model.

## Run

From `tasks/Omar`:

```
uv run adk run problem_solver "Solve: write a function that returns the sum of even numbers from 1 to n"
```

Or serve the web UI:

```
uv run adk web problem_solver
```

Requires a `GROQ_API_KEY` in `.env` (see the other agent folders for the format).

## Notes

- Model: `groq/openai/gpt-oss-120b` via LiteLlm, `max_tokens=4096` per call.
- gpt-oss streams `reasoning_content`, which Groq rejects when resent; it is
  stripped via a LiteLlm patch in `agent.py`.
- `litellm.num_retries = 10` handles transient errors; the free Groq tier
  (~8k TPM) makes multi-pass runs slow — runs complete once the rate-limit
  window clears.