"""Tests for the problem_solver orchestrator agent."""

import problem_solver
from problem_solver.agent import (
    build_plan,
    complete_task,
    execute_step,
    review_step,
)


def test_agent_is_exported() -> None:
    assert problem_solver.agent.name == "Problem_Solver"


def test_agent_exposes_orchestration_tools() -> None:
    tool_names = {tool.__name__ for tool in problem_solver.agent.tools}
    assert tool_names == {
        "research_problem",
        "build_plan",
        "execute_step",
        "review_step",
        "complete_task",
    }


def test_review_gate_accepts_good_output() -> None:
    result = review_step(1, "done", acceptable=True, notes="matches spec")
    assert "ACCEPTED" in result
    assert "Continue to the next step" in result


def test_review_gate_rejects_and_blocks_progress() -> None:
    result = review_step(2, "broken", acceptable=False, notes="fails tests")
    assert "REJECTED" in result
    assert "Do NOT continue" in result
    assert "Redo step 2" in result


def test_plan_and_execute_are_sequential() -> None:
    plan = build_plan("solve FizzBuzz", "research notes")
    assert plan.count("Step ") == 4

    executed = execute_step(1, "clarify constraints")
    assert executed == "Executed step 1: clarify constraints"

    final = complete_task("solve FizzBuzz", "solution summary")
    assert final.startswith("Problem solved: solve FizzBuzz")