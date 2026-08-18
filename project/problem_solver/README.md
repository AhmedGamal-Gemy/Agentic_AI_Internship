# problem_solver

Multi-agent system that solves coding problems: the user submits a problem,
the orchestrator delegates to specialized agents, and only a **verified**
solution (passed code execution + critique) is returned.

## Agents

| Agent | Model | Job |
|---|---|---|
| `orchestrator` (root) | `groq/qwen/qwen3.6-27b` | Receives the problem, coordinates the team, compiles the final answer |
| `planner` | `groq/qwen/qwen3.6-27b` | Decomposes the problem into steps + edge cases + complexity, saves to state |
| `researcher` | `groq/qwen/qwen3.6-27b` | Web research via Exa for non-obvious algorithms |
| `solver` | `groq/openai/gpt-oss-120b` | Writes solution + tests, executes them in a sandbox, iterates until green |
| `critic` | `groq/qwen/qwen3.6-27b` | Checklist review; FAIL verdicts bounce back to the solver (max 3 attempts) |

## Setup

```bash
cd project/problem_solver
uv sync
```

Create a `.env` file (in `project/`) with:

```
GROQ_API_KEY=...
OPENAI_API_KEY=...
EXA_API_KEY=...        # optional; research agent degrades gracefully without it
```

Code execution prefers the sandboxed `ContainerCodeExecutor` (Docker daemon
must be running). If Docker is unavailable it falls back to a local
subprocess executor with a 60s timeout.

## Run

```bash
uv run python -m problem_solver "Write a function that returns the two numbers in a list that sum to a target"

# visual debugging / agent UI
uv run adk web .
```

The CLI prints the delegation trace (each agent's turn) and the final
answer, tagged `VERIFIED` only when the critic passed the solution.