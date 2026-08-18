"""Deterministic tests for the human-in-the-loop workflow controller.

No API keys, LLM calls, Exa calls, git, or subprocess are used: the ADK
invocation, test runner, and git commit seams are monkeypatched.
"""

from __future__ import annotations

import json

import pytest

import problem_solver
from problem_solver import workflow
from problem_solver.state_store import load_workflow

PLAN = "Step 1: Clarify the problem.\nStep 2: Draft a solution approach.\nStep 3: Verify the deliverable."


def _patch_seams(monkeypatch, reviews=("Step 1 ACCEPTED (ok).",)) -> None:
    calls = {"count": 0, "by_agent": []}

    def fake_invoke(agent, prompt, user_id="default"):
        calls["count"] += 1
        calls["by_agent"].append(agent.name)
        if agent.name == "Research_Agent":
            return "Findings: use the standard library.\n- https://example.com/a"
        if agent.name == "Planning_Agent":
            return PLAN
        if agent.name == "Implementer_Agent":
            return f"Executed {prompt.split(': ')[1]}"
        return reviews[0]

    monkeypatch.setattr(workflow, "_invoke_agent", fake_invoke)
    monkeypatch.setattr(
        workflow,
        "_run_tests",
        lambda wf: {"returncode": 0, "output": "5 passed"},
    )
    monkeypatch.setattr(workflow, "_git_commit", lambda msg: "abc1234")
    return calls


def test_resume_keywords() -> None:
    assert workflow.RESUME_KEYWORDS == ("resume", "approved", "continue")


def test_start_workflow_has_required_fields(tmp_path) -> None:
    path = tmp_path / "wf.json"
    wf = workflow.start_workflow(
        "solve FizzBuzz", context={"lang": "python"}, assumptions=["3.12"], path=path
    )
    assert wf["status"] == "researching"
    assert wf["assumptions"] == ["3.12"]
    for key in (
        "workflow_id",
        "problem",
        "context",
        "research",
        "plan",
        "plan_review",
        "tasks",
        "current_task",
        "next_task",
        "status",
        "events",
    ):
        assert key in wf
    assert any(e["type"] == "workflow_started" for e in wf["events"])


def test_split_plan_creates_tasks_with_dependencies() -> None:
    tasks = workflow.split_plan(PLAN)
    assert [t["id"] for t in tasks] == ["task-1", "task-2", "task-3"]
    assert tasks[0]["dependencies"] == []
    assert tasks[1]["dependencies"] == ["task-1"]
    assert tasks[2]["assigned_agent"] == "Implementer_Agent"
    assert all(t["status"] == "pending" for t in tasks)


def test_full_flow_one_approval_one_task(tmp_path, monkeypatch) -> None:
    calls = _patch_seams(monkeypatch)
    path = tmp_path / "wf.json"

    wf = workflow.start_workflow("solve FizzBuzz", path=path)
    workflow.run_research(wf, "solve FizzBuzz", path=path)
    workflow.run_planning(wf, "solve FizzBuzz", path=path)
    workflow.review_plan(wf, approved=True, path=path)

    assert wf["status"] == "ready"
    assert wf["current_task"] == "task-1"
    assert wf["next_task"] == "task-2"
    assert len(wf["tasks"]) == 3

    workflow.execute_one_task(wf, path=path)
    assert wf["status"] == "awaiting_approval"
    assert wf["tasks"][0]["status"] == "reviewed"
    assert wf["tasks"][0]["git_commit_hash"] == "abc1234"
    assert wf["tasks"][0]["test_results"]["returncode"] == 0
    assert wf["current_task"] == "task-1"

    executed_before = calls["count"]
    workflow.resume(wf, "no", path=path)
    assert wf["status"] == "awaiting_approval"
    assert calls["count"] == executed_before

    workflow.resume(wf, "resume", path=path)
    assert wf["tasks"][0]["status"] == "approved"
    assert wf["tasks"][1]["status"] == "reviewed"
    assert wf["status"] == "awaiting_approval"
    assert wf["current_task"] == "task-2"

    workflow.resume(wf, "APPROVED", path=path)
    assert wf["tasks"][2]["status"] == "reviewed"

    workflow.resume(wf, "continue", path=path)
    assert wf["status"] == "completed"
    assert all(t["status"] == "approved" for t in wf["tasks"])


def test_resume_from_path_after_restart(tmp_path, monkeypatch) -> None:
    _patch_seams(monkeypatch)
    path = tmp_path / "wf.json"

    wf = workflow.start_workflow("solve FizzBuzz", path=path)
    workflow.run_research(wf, "solve FizzBuzz", path=path)
    workflow.run_planning(wf, "solve FizzBuzz", path=path)
    workflow.review_plan(wf, approved=True, path=path)
    workflow.execute_one_task(wf, path=path)

    restarted = load_workflow(path)
    assert restarted["status"] == "awaiting_approval"
    assert restarted["tasks"][0]["status"] == "reviewed"

    workflow.resume_from_path(path, "resume")
    refreshed = load_workflow(path)
    assert refreshed["tasks"][0]["status"] == "approved"
    assert refreshed["tasks"][1]["status"] == "reviewed"
    assert refreshed["status"] == "awaiting_approval"


def test_rejected_plan_stops_workflow(tmp_path, monkeypatch) -> None:
    _patch_seams(monkeypatch)
    path = tmp_path / "wf.json"
    wf = workflow.start_workflow("solve FizzBuzz", path=path)
    workflow.run_research(wf, "solve FizzBuzz", path=path)
    workflow.run_planning(wf, "solve FizzBuzz", path=path)
    workflow.review_plan(wf, approved=False, notes="too vague", path=path)

    assert wf["status"] == "rejected"
    assert wf["plan_review"]["approved"] is False
    resume_after = workflow.resume(wf, "resume", path=path)
    assert resume_after["status"] == "rejected"


def test_failing_tests_reject_task(tmp_path, monkeypatch) -> None:
    _patch_seams(monkeypatch)
    monkeypatch.setattr(
        workflow, "_run_tests", lambda wf: {"returncode": 1, "output": "1 failed"}
    )
    path = tmp_path / "wf.json"
    wf = workflow.start_workflow("solve FizzBuzz", path=path)
    workflow.run_research(wf, "solve FizzBuzz", path=path)
    workflow.run_planning(wf, "solve FizzBuzz", path=path)
    workflow.review_plan(wf, approved=True, path=path)
    workflow.execute_one_task(wf, path=path)

    assert wf["status"] == "rejected"
    assert wf["tasks"][0]["status"] == "rejected"
    assert any(e["type"] == "task_rejected" for e in wf["events"])


def test_review_rejection_stops_workflow(tmp_path, monkeypatch) -> None:
    _patch_seams(monkeypatch, reviews=("Step 1 REJECTED (fails spec).",))
    path = tmp_path / "wf.json"
    wf = workflow.start_workflow("solve FizzBuzz", path=path)
    workflow.run_research(wf, "solve FizzBuzz", path=path)
    workflow.run_planning(wf, "solve FizzBuzz", path=path)
    workflow.review_plan(wf, approved=True, path=path)
    workflow.execute_one_task(wf, path=path)

    assert wf["status"] == "rejected"
    assert wf["tasks"][0]["review"]["verdict"] == "rejected"
    workflow.resume(wf, "resume", path=path)
    assert wf["status"] == "rejected"


def test_make_verdict() -> None:
    assert workflow._make_verdict("ACCEPTED") == "accepted"
    assert workflow._make_verdict("REJECTED") == "rejected"
    assert workflow._make_verdict("hmm") == "rejected"


def test_secrets_are_redacted_before_persist(tmp_path, monkeypatch) -> None:
    def fake_invoke(agent, prompt, user_id="default"):
        if agent.name == "Planning_Agent":
            return PLAN
        if agent.name == "Implementer_Agent":
            return "used api_key=sk-test123456789012 and token=abc"
        if agent.name == "Review_Agent":
            return "Step 1 ACCEPTED (ok)."
        return "ok"

    monkeypatch.setattr(workflow, "_invoke_agent", fake_invoke)
    monkeypatch.setattr(
        workflow, "_run_tests", lambda wf: {"returncode": 0, "output": "5 passed"}
    )
    monkeypatch.setattr(workflow, "_git_commit", lambda msg: "abc1234")

    path = tmp_path / "wf.json"
    wf = workflow.start_workflow("solve FizzBuzz", path=path)
    workflow.run_research(wf, "solve FizzBuzz", path=path)
    workflow.run_planning(wf, "solve FizzBuzz", path=path)
    workflow.review_plan(wf, approved=True, path=path)
    workflow.execute_one_task(wf, path=path)

    raw = path.read_text(encoding="utf-8")
    assert "sk-test123456789012" not in raw
    assert "token=abc" not in raw
    assert "[REDACTED]" in raw


def test_report_includes_state_snapshot(tmp_path, monkeypatch) -> None:
    _patch_seams(monkeypatch)
    path = tmp_path / "wf.json"
    wf = workflow.start_workflow("solve FizzBuzz", path=path)
    text = workflow.report(wf)
    assert "Workflow:" in text
    assert "Status: researching" in text
    assert "solve FizzBuzz" in text