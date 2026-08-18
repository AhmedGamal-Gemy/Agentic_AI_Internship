"""Tests for the problem_solver orchestrator and its sub-agents."""

import problem_solver
from problem_solver.implementer import execute_step
from problem_solver.planning import build_plan
from problem_solver.review import complete_task, review_step


def test_agent_is_exported() -> None:
    assert problem_solver.agent.name == "Problem_Solver"


def test_root_agent_delegates_to_sub_agents() -> None:
    names = {sub.name for sub in problem_solver.agent.sub_agents}
    assert names == {
        "Research_Agent",
        "Planning_Agent",
        "Implementer_Agent",
        "Review_Agent",
    }


def test_sub_agents_have_expected_tools() -> None:
    assert {t.__name__ for t in problem_solver.research_agent.tools} == {"research_problem"}
    assert {t.__name__ for t in problem_solver.planning_agent.tools} == {"build_plan"}
    assert {t.__name__ for t in problem_solver.implementer_agent.tools} == {"execute_step"}
    assert {t.__name__ for t in problem_solver.review_agent.tools} == {"review_step", "complete_task"}


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