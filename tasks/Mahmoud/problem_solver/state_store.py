"""Persistent workflow state store for the Problem Solver Agent.

A JSON-file-backed persistence layer recording the full lifecycle of a
problem-solving workflow: problem, context, research, plan, plan review,
task list, assigned agents, execution results, test results, Git commit
hashes, task reviews, workflow status, current/next task, and a
chronological event history.

Secrets (API keys, tokens, passwords) are never persisted: any key whose
name looks sensitive is dropped when saving.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_WORKFLOWS_DIR = Path(__file__).resolve().parent / "workflows"

_SENSITIVE_NAME_TOKENS = ("api_key", "apikey", "key", "secret", "token", "password", "credential")


def _utc_now() -> str:
    """ISO-8601 UTC timestamp (second precision, Z-suffixed)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _default_workflow(problem: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """A fresh workflow dict with the full persisted schema filled in."""
    now = _utc_now()
    return {
        "workflow_id": uuid.uuid4().hex,
        "status": "created",
        "problem": problem,
        "context": context or {},
        "research": {"queries": [], "results": [], "sources": []},
        "plan": None,
        "plan_review": None,
        "tasks": [],
        "current_task": None,
        "next_task": None,
        "execution": {
            "results": [],
            "test_results": [],
            "git_commit_hashes": [],
            "reviews": [],
        },
        "events": [],
        "created_at": now,
        "updated_at": now,
    }


def _default_path(workflow: Dict[str, Any]) -> Path:
    workflow_id = workflow.get("workflow_id", "workflow")
    return DEFAULT_WORKFLOWS_DIR / f"{workflow_id}.json"


def _is_sensitive(name: str) -> bool:
    lowered = name.lower().lstrip("_")
    if lowered in {"path", "file", "dir", "directory"}:
        return True
    return any(token in lowered for token in _SENSITIVE_NAME_TOKENS)


def _sanitize(value: Any) -> Any:
    """Recursively drop any key that is private (leading underscore) or looks
    like a secret (e.g. ``api_key``, ``token``, ``password``)."""
    if isinstance(value, dict):
        return {
            key: _sanitize(item)
            for key, item in value.items()
            if not key.startswith("_") and not _is_sensitive(key)
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    """Atomically write the workflow to ``path`` (temp file + replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(_sanitize(data), indent=2, ensure_ascii=False)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.write("\n")
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def create_workflow(
    problem: str,
    context: Optional[Dict[str, Any]] = None,
    path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """Create a new workflow for ``problem`` and persist it.

    Args:
        problem: The original user problem this workflow will solve.
        context: Optional additional context (constraints, references, ...).
        path: Where to persist. Defaults to
            ``problem_solver/workflows/<workflow_id>.json``.

    Returns:
        The persisted workflow dict (also the active in-memory copy).
    """
    workflow = _default_workflow(problem, context)
    workflow["events"].append(
        {"seq": 1, "ts": _utc_now(), "type": "created", "data": {"problem": problem}}
    )
    save_workflow(workflow, path=path)
    return workflow


def load_workflow(path: str | Path) -> Dict[str, Any]:
    """Load a workflow from its JSON file.

    Args:
        path: The workflow JSON file to read.

    Returns:
        The workflow dict.

    Raises:
        FileNotFoundError: if ``path`` does not exist.
        ValueError: if the file is not valid JSON or not a dict.
    """
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(f"workflow file not found: {target}")
    with target.open("r", encoding="utf-8") as handle:
        workflow = json.load(handle)
    if not isinstance(workflow, dict):
        raise ValueError(f"workflow file is not a JSON object: {target}")
    return workflow


def save_workflow(workflow: Dict[str, Any], path: Optional[str | Path] = None) -> None:
    """Persist ``workflow`` to disk.

    Args:
        workflow: The workflow dict to save.
        path: Override target path. Defaults to
            ``problem_solver/workflows/<workflow_id>.json``.
    """
    _write_json(_default_path(workflow) if path is None else Path(path), workflow)


def update_workflow(
    workflow: Dict[str, Any],
    path: Optional[str | Path] = None,
    event_note: Optional[str] = None,
    **fields: Any,
) -> Dict[str, Any]:
    """Apply ``fields`` to the workflow and persist the change.

    Each update is recorded as an ``update`` event describing which fields
    changed. Do not pass secrets via ``fields``; they are stripped on save.

    Args:
        workflow: The workflow dict to mutate in place.
        path: Override target path (see :func:`save_workflow`).
        event_note: Optional human-readable reason for the update.
        **fields: Field names mapped to new values.

    Returns:
        The updated workflow dict.
    """
    changed = sorted(name for name in fields if not _is_sensitive(name))
    workflow.update(fields)
    workflow["updated_at"] = _utc_now()
    append_event(
        workflow,
        event_type="update",
        data={"fields": changed, "note": event_note} if event_note else {"fields": changed},
        path=path,
    )
    return workflow


def append_event(
    workflow: Dict[str, Any],
    event_type: str,
    data: Optional[Dict[str, Any]] = None,
    path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """Append a chronological event to the workflow and persist it.

    Events get a monotonic ``seq`` and an ISO-8601 ``ts`` timestamp.

    Args:
        workflow: The workflow dict to mutate in place.
        event_type: Machine-readable event kind (e.g. ``created``, ``plan``,
            ``task_executed``, ``task_reviewed``, ``commit``).
        data: Optional structured payload for the event.
        path: Override target path (see :func:`save_workflow`).

    Returns:
        The workflow dict with the new event appended.
    """
    events = workflow.setdefault("events", [])
    seq = (events[-1]["seq"] + 1) if events else 1
    events.append({"seq": seq, "ts": _utc_now(), "type": event_type, "data": data or {}})
    workflow["updated_at"] = _utc_now()
    save_workflow(workflow, path=path)
    return workflow