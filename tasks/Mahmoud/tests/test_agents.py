"""Tests for the ADK multi-agent structure: delegation, runner, and Exa tooling.

All tests are deterministic and require no API keys, network, or LLM calls.
The Exa client is monkeypatched with a fake where needed.
"""

from __future__ import annotations

from types import SimpleNamespace

import problem_solver
from problem_solver import runner as ps_runner
from problem_solver.research import research_problem


def test_research_agent_uses_exa_and_reports_sources(monkeypatch) -> None:
    from problem_solver import research

    def fake_search(*args, **kwargs):
        result = SimpleNamespace(
            title="Example Title",
            highlights=["A useful highlight."],
            url="https://example.com/a",
        )
        return SimpleNamespace(results=[result])

    monkeypatch.setattr(research, "exa", SimpleNamespace(search=fake_search))

    findings = research_problem("how to implement X")
    assert "Example Title" in findings
    assert "A useful highlight." in findings
    assert "https://example.com/a" in findings


def test_research_agent_degrades_without_key(monkeypatch) -> None:
    from problem_solver import research

    monkeypatch.setattr(research, "exa", None)
    assert "skipping research" in research_problem("anything")


def test_runner_targets_problem_solver_agent() -> None:
    assert ps_runner.runner.agent.name == "Problem_Solver"
    assert ps_runner.APP_NAME == "problem_solver"


def test_root_agent_has_no_direct_tools_it_delegates() -> None:
    assert problem_solver.agent.tools == []