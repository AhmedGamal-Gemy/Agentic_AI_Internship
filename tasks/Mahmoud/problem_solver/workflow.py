"""Workflow controller — drives the Problem Solver through the
research → plan → plan-review → one-task → test → task-review → report →
STOP → wait-for-human-approval cycle.

Every step is persisted through the state store so the workflow survives a
restart and resumes from the last persisted step. One human approval
(``resume`` / ``approved`` / ``continue``) enables exactly ONE implementation
task. A rejected plan or task stops the workflow and reports the problem.

Secrets are redacted from agent outputs and test output before anything is
persisted.
"""

from __future__ import annotations

import asyncio
import re
import subprocess
from typing import Any, Dict, List, Optional

from google.adk.runners import InMemoryRunner
from google.genai import types

from .implementer import implementer_agent
from .planning import planning_agent
from .research import research_agent
from .review import review_agent
from .state_store import (
    append_event,
    create_workflow as _create_workflow,
    load_workflow,
)

RESUME_KEYWORDS = ("resume", "approved", "continue")
APP_NAME_PREFIX = "problem_solver"

_SECRET_PATTERNS = (
    r"\b(?:sk|pk)-[A-Za-z0-9_-]{8,}\b",
    r"\bAKIA[0-9A-Z]{16}\b",
    r"\bghp_[A-Za-z0-9]{30,}\b",
    r"\b(?:api[_-]?key|token|password|secret)\s*[=:]\s*\S+",
)

_runners: Dict[str, InMemoryRunner] = {}


def _redact(text: str) -> str:
    """Mask anything that looks like a credential in text."""
    if not isinstance(text, str):
        return text
    for pattern in _SECRET_PATTERNS:
        text = re.sub(pattern, "[REDACTED]", text, flags=re.IGNORECASE)
    return text


def _runner_for(agent) -> InMemoryRunner:
    if agent.name not in _runners:
        _runners[agent.name] = InMemoryRunner(
            agent=agent, app_name=f"{APP_NAME_PREFIX}_{agent.name}"
        )
    return _runners[agent.name]


async def _run_agent(agent, prompt: str, user_id: str) -> str:
    """Stream an ADK agent and return its concatenated text reply."""
    runner = _runner_for(agent)
    session = await runner.session_service.create_session(
        app_name=runner.app_name, user_id=user_id
    )
    message = types.Content(role="user", parts=[types.Part(text=prompt)])
    texts = []
    async for event in runner.run_async(
        user_id=user_id, session_id=session.id, new_message=message
    ):
        for part in (event.content and event.content.parts) or []:
            if part.text:
                texts.append(part.text)
    return "\n".join(texts)


def _invoke_agent(agent, prompt: str, user_id: str = "default") -> str:
    """Sync wrapper around the ADK Runner.

    Test seam: deterministic tests monkeypatch this to avoid real LLM calls.
    """
    return asyncio.run(_run_agent(agent, prompt, user_id=user_id))


def _extract_sources(text: str) -> List[str]:
    return sorted(set(re.findall(r"https?://\S+", text or "")))


def _make_verdict(review_output: str) -> str:
    """Parse a Review Agent verdict. Unknown output is treated as rejected."""
    upper = (review_output or "").upper()
    if "REJECTED" in upper:
        return "rejected"
    if "ACCEPTED" in upper:
        return "accepted"
    return "rejected"


def _next_pending_task(wf: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return next(
        (t for t in wf.get("tasks", []) if t.get("status") == "pending"), None
    )


def _find_task(wf: Dict[str, Any], task_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not task_id:
        return None
    return next((t for t in wf.get("tasks", []) if t.get("id") == task_id), None)


def _next_task_id_after(wf: Dict[str, Any], task_id: Optional[str]) -> Optional[str]:
    ids = [t["id"] for t in wf.get("tasks", [])]
    try:
        index = ids.index(task_id)
    except (ValueError, TypeError):
        return None
    return ids[index + 1] if index + 1 < len(ids) else None


def start_workflow(
    problem: str,
    context: Optional[Dict[str, Any]] = None,
    assumptions: Optional[List[str]] = None,
    path=None,
) -> Dict[str, Any]:
    """Create and persist a new workflow, status ``researching``."""
    wf = _create_workflow(problem, context=context or {}, path=path)
    wf["assumptions"] = assumptions or []
    wf["status"] = "researching"
    append_event(wf, "workflow_started", {"status": "researching"}, path=path)
    return wf


def run_research(
    wf: Dict[str, Any], problem: str, user_id: str = "default", path=None
) -> Dict[str, Any]:
    """Delegate research to the Research Agent (Exa) and persist findings."""
    findings = _invoke_agent(research_agent, problem, user_id=user_id)
    findings = _redact(findings)
    wf["research"] = {
        "queries": [problem],
        "results": [findings],
        "sources": _extract_sources(findings),
    }
    wf["status"] = "researched"
    append_event(
        wf,
        "research_completed",
        {"queries": 1, "sources": len(wf["research"]["sources"])},
        path=path,
    )
    return wf


def split_plan(plan: str) -> List[Dict[str, Any]]:
    """Turn a ``Step N: description`` plan into Git-sized tasks."""
    tasks = []
    for line in (plan or "").splitlines():
        match = re.match(r"Step\s+(\d+)\s*:\s*(.+)", line.strip(), re.IGNORECASE)
        if not match:
            continue
        n = int(match.group(1))
        tasks.append(
            {
                "id": f"task-{n}",
                "step": n,
                "description": match.group(2).strip(),
                "dependencies": [f"task-{n - 1}"] if n > 1 else [],
                "assigned_agent": implementer_agent.name,
                "status": "pending",
                "result": None,
                "test_results": None,
                "git_commit_hash": None,
                "review": None,
            }
        )
    return tasks


def run_planning(
    wf: Dict[str, Any],
    problem: str,
    research: Optional[str] = None,
    user_id: str = "default",
    path=None,
) -> Dict[str, Any]:
    """Delegate planning to the Planning Agent and split the plan into tasks."""
    if research is None:
        research = (wf.get("research", {}).get("results") or [""])[0]
    prompt = f"Problem: {problem}\nResearch:\n{research}"
    plan = _redact(_invoke_agent(planning_agent, prompt, user_id=user_id))
    wf["plan"] = plan
    wf["tasks"] = split_plan(plan)
    wf["status"] = "plan_review"
    append_event(wf, "plan_completed", {"tasks": len(wf["tasks"])}, path=path)
    return wf


def review_plan(
    wf: Dict[str, Any], approved: bool, notes: str = "", path=None
) -> Dict[str, Any]:
    """Record the plan review. Rejecting the plan stops the workflow."""
    wf["plan_review"] = {"approved": approved, "notes": _redact(notes)}
    tasks = wf.get("tasks", [])
    if approved:
        wf["status"] = "ready"
        wf["current_task"] = tasks[0]["id"] if tasks else None
        wf["next_task"] = tasks[1]["id"] if len(tasks) > 1 else None
        append_event(wf, "plan_approved", {"notes": notes}, path=path)
    else:
        wf["status"] = "rejected"
        append_event(wf, "plan_rejected", {"notes": notes}, path=path)
    return wf


def _run_tests(wf: Dict[str, Any]) -> Dict[str, Any]:
    """Run the project test suite. Test seam: monkeypatched in tests."""
    command = wf.get("test_command") or ["uv", "run", "pytest"]
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=300)
        return {
            "returncode": proc.returncode,
            "output": _redact((proc.stdout or "")[-4000:]),
        }
    except Exception as exc:  # pragma: no cover - defensive
        return {"returncode": -1, "output": _redact(str(exc))}


def _git_commit(message: str) -> str:
    """Commit the task's changes and return the short hash. Test seam."""
    subprocess.run(["git", "add", "-A"], check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "commit", "-m", message], check=True, capture_output=True, text=True
    )
    proc = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], check=True, capture_output=True, text=True
    )
    return proc.stdout.strip()


def execute_one_task(
    wf: Dict[str, Any], user_id: str = "default", path=None
) -> Dict[str, Any]:
    """Execute exactly ONE task: implement → test → commit → review.

    After an accepted review the workflow stops at ``awaiting_approval`` and
    only a human approval (see :func:`resume`) unlocks the next task.
    """
    task = _next_pending_task(wf)
    if task is None:
        wf["status"] = "completed"
        append_event(wf, "workflow_completed", {}, path=path)
        return wf

    task["status"] = "in_progress"
    wf["current_task"] = task["id"]
    wf["next_task"] = _next_task_id_after(wf, task["id"])
    append_event(wf, "task_started", {"task": task["id"]}, path=path)

    output = _redact(
        _invoke_agent(
            implementer_agent,
            f"Execute task {task['id']}: {task['description']}",
            user_id=user_id,
        )
    )
    task["result"] = output
    append_event(wf, "task_executed", {"task": task["id"]}, path=path)

    test_result = _run_tests(wf)
    task["test_results"] = test_result
    append_event(
        wf,
        "task_tested",
        {"task": task["id"], "returncode": test_result.get("returncode")},
        path=path,
    )
    if test_result.get("returncode") != 0:
        task["status"] = "rejected"
        wf["status"] = "rejected"
        append_event(
            wf,
            "task_rejected",
            {"task": task["id"], "reason": "tests failed"},
            path=path,
        )
        return wf

    commit_hash = _git_commit(f"task {task['id']}: {task['description']}")
    task["git_commit_hash"] = commit_hash
    append_event(
        wf, "task_committed", {"task": task["id"], "git_commit": commit_hash}, path=path
    )

    verdict_text = _redact(
        _invoke_agent(
            review_agent,
            f"Review task {task['id']}.\nOutput:\n{output}\n"
            f"Test results:\n{test_result.get('output', '')}",
            user_id=user_id,
        )
    )
    verdict = _make_verdict(verdict_text)
    task["review"] = {"verdict": verdict, "notes": verdict_text}
    append_event(
        wf, "task_reviewed", {"task": task["id"], "verdict": verdict}, path=path
    )

    if verdict == "rejected":
        task["status"] = "rejected"
        wf["status"] = "rejected"
        return wf

    task["status"] = "reviewed"
    wf["status"] = "awaiting_approval"
    wf["current_task"] = task["id"]
    wf["next_task"] = _next_task_id_after(wf, task["id"])
    append_event(wf, "task_review_accepted", {"task": task["id"]}, path=path)
    return wf


def resume(
    wf: Dict[str, Any], user_input: str, user_id: str = "default", path=None
) -> Dict[str, Any]:
    """Handle one human approval: unlocks exactly ONE next task.

    Anything other than ``resume`` / ``approved`` / ``continue`` leaves the
    workflow waiting. A rejected workflow can never be resumed.
    """
    if wf.get("status") == "rejected":
        append_event(
            wf,
            "resume_denied",
            {"reason": "workflow is rejected; stopping and reporting"},
            path=path,
        )
        return wf

    if wf.get("status") != "awaiting_approval":
        return wf

    if (user_input or "").strip().lower() not in RESUME_KEYWORDS:
        append_event(wf, "still_waiting", {"input": user_input}, path=path)
        return wf

    task = _find_task(wf, wf.get("current_task"))
    if task is not None and task.get("status") == "reviewed":
        task["status"] = "approved"
        append_event(
            wf, "task_approved", {"task": task["id"], "approved_by": "human"}, path=path
        )

    next_id = _next_task_id_after(wf, task["id"]) if task else None
    if next_id is None:
        wf["status"] = "completed"
        append_event(wf, "workflow_completed", {}, path=path)
        return wf

    return execute_one_task(wf, user_id=user_id, path=path)


def resume_from_path(path, user_input: str, user_id: str = "default"):
    """Load a persisted workflow and resume it (survives application restart)."""
    wf = load_workflow(path)
    return resume(wf, user_input, user_id=user_id, path=path)


def report(wf: Dict[str, Any]) -> str:
    """Human-readable snapshot of the current workflow state."""
    lines = [
        f"Workflow: {wf.get('workflow_id')}",
        f"Status: {wf.get('status')}",
        f"Problem: {wf.get('problem')}",
        f"Current task: {wf.get('current_task')}",
        f"Next task: {wf.get('next_task')}",
    ]
    if wf.get("tasks"):
        lines.append("Tasks:")
        lines.extend(
            f"- {t['id']} [{t.get('status')}] {t.get('description')}"
            for t in wf["tasks"]
        )
    if wf.get("events"):
        lines.append("Events:")
        lines.extend(f"- {e.get('type')}" for e in wf["events"])
    return "\n".join(lines)


__all__ = [
    "start_workflow",
    "run_research",
    "run_planning",
    "split_plan",
    "review_plan",
    "execute_one_task",
    "resume",
    "resume_from_path",
    "report",
    "RESUME_KEYWORDS",
]