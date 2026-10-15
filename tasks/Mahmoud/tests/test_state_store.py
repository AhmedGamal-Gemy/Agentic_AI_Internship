"""Tests for the problem_solver persistent workflow state store."""

import json

import pytest

from problem_solver.state_store import (
    DEFAULT_WORKFLOWS_DIR,
    append_event,
    create_workflow,
    load_workflow,
    save_workflow,
    update_workflow,
)


def test_create_workflow_initializes_schema(tmp_path) -> None:
    path = tmp_path / "wf.json"
    workflow = create_workflow("solve FizzBuzz", context={"lang": "python"}, path=path)

    assert workflow["workflow_id"]
    assert workflow["status"] == "created"
    assert workflow["problem"] == "solve FizzBuzz"
    assert workflow["context"] == {"lang": "python"}
    assert workflow["plan"] is None
    assert workflow["tasks"] == []
    assert workflow["current_task"] is None
    assert workflow["next_task"] is None
    assert workflow["research"] == {"queries": [], "results": [], "sources": []}
    assert workflow["execution"] == {
        "results": [],
        "test_results": [],
        "git_commit_hashes": [],
        "reviews": [],
    }
    assert path.is_file()


def test_save_and_load_round_trip(tmp_path) -> None:
    path = tmp_path / "wf.json"
    workflow = create_workflow("solve FizzBuzz", path=path)
    workflow["status"] = "planned"
    save_workflow(workflow, path=path)

    loaded = load_workflow(path)
    assert loaded["status"] == "planned"
    assert loaded["problem"] == "solve FizzBuzz"
    assert loaded == workflow


def test_update_workflow_changes_fields_and_records_event(tmp_path) -> None:
    path = tmp_path / "wf.json"
    workflow = create_workflow("solve FizzBuzz", path=path)

    update_workflow(workflow, path=path, status="planned", plan=["a", "b"])

    assert workflow["status"] == "planned"
    assert workflow["plan"] == ["a", "b"]
    event = workflow["events"][-1]
    assert event["type"] == "update"
    assert event["data"]["fields"] == ["plan", "status"]


def test_append_event_is_chronological_and_monotonic(tmp_path) -> None:
    path = tmp_path / "wf.json"
    workflow = create_workflow("solve FizzBuzz", path=path)

    append_event(workflow, event_type="researched", data={"queries": 2}, path=path)
    append_event(workflow, event_type="task_executed", data={"task": 1}, path=path)
    append_event(workflow, event_type="task_reviewed", data={"verdict": "approved"}, path=path)

    events = workflow["events"]
    assert [e["seq"] for e in events] == [1, 2, 3, 4]
    assert [e["type"] for e in events] == ["created", "researched", "task_executed", "task_reviewed"]
    assert all(e["ts"] for e in events)

    loaded = load_workflow(path)
    assert loaded["events"] == events


def test_secrets_are_never_persisted(tmp_path) -> None:
    path = tmp_path / "wf.json"
    workflow = create_workflow("solve FizzBuzz", path=path)

    append_event(
        workflow,
        event_type="research",
        data={"query": "solutions", "api_key": "sk-123", "token": "abc"},
        path=path,
    )
    update_workflow(workflow, path=path, api_key="should-not-save")

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert "sk-123" not in raw
    assert "abc" not in raw
    assert "should-not-save" not in raw
    assert "api_key" not in json.dumps(raw)


def test_private_keys_are_not_persisted(tmp_path) -> None:
    path = tmp_path / "wf.json"
    workflow = create_workflow("solve FizzBuzz", path=path)
    workflow["_internal_note"] = "runtime only"
    save_workflow(workflow, path=path)

    loaded = load_workflow(path)
    assert "_internal_note" not in loaded


def test_load_missing_file_raises(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        load_workflow(tmp_path / "missing.json")


def test_default_path_is_workflows_dir() -> None:
    assert DEFAULT_WORKFLOWS_DIR.name == "workflows"