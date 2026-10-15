# Problem Solver Agent

ADK-based orchestrator that takes a user problem and drives it through
research → planning → plan review → Git-sized task execution → review, with a
mandatory human approval between tasks.

Built for the Agentic AI Internship under `tasks/Mahmoud`.

## Architecture

```
Problem Solver Agent (root orchestrator, problem_solver/agent.py)
        │  delegates via ADK sub_agents
        ├── Research Agent    → Exa Search            (research.py)
        ├── Planning Agent    → build_plan            (planning.py)
        ├── Implementer Agent → execute_step          (implementer.py)
        └── Review Agent      → review_step           (review.py)
```

- Framework: **Google ADK** (`Agent`, `sub_agents`, `InMemoryRunner`, sessions)
- LLM: **LiteLLM** (`LiteLlm("groq/llama-3.3-70b-versatile")`), keys from env
- Search: **Exa Search** (`EXA_API_KEY` from env)
- Persistence: JSON state store (`state_store.py`)

## Workflow

```
1. Research + Plan
2. Split into tasks + Git commits
3. Review plan
4. Execute ONE task
5. STOP
6. Review completed task
   ├─ APPROVED → next task (only after human says resume/approved/continue)
   └─ REJECTED → STOP + explain problem
```

Driven by the workflow controller (`workflow.py`):

| Phase | Function |
|---|---|
| Create workflow | `start_workflow(problem, context, assumptions)` |
| Research | `run_research(wf, problem)` |
| Plan + split | `run_planning(wf, problem)` → `split_plan(plan)` |
| Plan review | `review_plan(wf, approved, notes)` |
| One task | `execute_one_task(wf)` — implement → test → git commit → review |
| Human gate | `resume(wf, input)` / `resume_from_path(path, input)` |
| Snapshot | `report(wf)` |

## Human-in-the-loop (mandatory)

- One human approval (`resume` / `approved` / `continue`) = **exactly one**
  implementation task.
- Anything else keeps the workflow waiting at `awaiting_approval`.
- A rejected plan or task sets status `rejected`; the workflow can **never**
  be resumed from a rejected state — it stops and reports the problem.

## Persistence

Every step is saved to `problem_solver/workflows/<workflow_id>.json`
(gitignored) and survives a restart. The workflow records: workflow ID,
problem, context, assumptions, research (queries/results/sources), plan, plan
review, tasks, dependencies, assigned agents, execution results, test
results, Git commit hashes, task reviews, current/next task, workflow status,
and a chronological event history.

**Secrets are never stored.** Sensitive keys are stripped on save
(`state_store._sanitize`) and credential-like values are redacted to
`[REDACTED]` before persistence (`workflow._redact`).

## Task history

| Task | Deliverable | Commit | Status |
|---|---|---|---|
| T1 | Package scaffold | `faddd13` | APPROVED |
| T2 | Orchestrator agent | `19dab15` | APPROVED |
| T3 | Persistent state store | `19dab15` | APPROVED |
| T4 | ADK multi-agent delegation | `e27f75e` | APPROVED |
| T5 | Human approval workflow + resumable state | `fd313dc` | APPROVED |

All requirements delivered. No pending tasks.

## Files

```
problem_solver/
├── __init__.py      # public exports
├── agent.py         # root orchestrator + sub-agent delegation
├── research.py      # Research Agent (Exa Search)
├── planning.py      # Planning Agent
├── implementer.py   # Implementer Agent
├── review.py        # Review Agent
├── runner.py        # InMemoryRunner entry (run_problem)
├── state_store.py   # JSON persistence (create/load/save/update/append_event)
├── workflow.py      # human-in-the-loop workflow controller
└── workflows/       # persisted state (gitignored)
```

## Testing

```powershell
cd tasks\Mahmoud
uv sync --python 3.12
uv run pytest
```

Deterministic, no API keys / LLM / Exa / network required. External seams
(ADK invocation, pytest, git) are monkeypatched. Suite: **30 passed**.

## Live run

Requires real keys in `tasks\Mahmoud\.env` (`GROQ_API_KEY`, `EXA_API_KEY`):

```python
from problem_solver.runner import run_problem  # interactive single-shot run
from problem_solver import workflow           # gated workflow controller
```

For a full gated run use the workflow controller, calling `resume(wf, ...)`
between tasks.