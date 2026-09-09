"""Tests for the routine task generator. T3.02."""

from __future__ import annotations

from agentic_payments_env.contracts.common import TaskFamily
from agentic_payments_env.generators.base import GenParams, SeededRng
from agentic_payments_env.generators.routine import generate_routine
from agentic_payments_env.graders import grade_episode
from tests.conftest import run_oracle


def _params(**updates: object) -> GenParams:
    base = {
        "family": TaskFamily.ROUTINE_TRANSFER,
        "amount_limit_ratio_numer": 1,
        "amount_limit_ratio_denom": 20,
        "n_recipients": 1,
    }
    base.update(updates)
    return GenParams(**base)  # type: ignore[arg-type]


def test_generate_routine_is_deterministic() -> None:
    params = _params()
    first = generate_routine(SeededRng(0), params, "v1/gen-rt-001")
    second = generate_routine(SeededRng(0), params, "v1/gen-rt-001")
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    amount = first.hidden.expected_transfers[0].amount_centavos
    assert isinstance(amount, int)
    assert amount > 0


def test_generate_routine_oracle_safe_success() -> None:
    task = generate_routine(SeededRng(0), _params(), "v1/gen-rt-001")
    trace, state = run_oracle(task)
    result = grade_episode(task, trace, state)
    assert result.safe_success is True
    assert result.violations == []


def test_routine_oracle_includes_check_transfer_policy() -> None:
    task = generate_routine(SeededRng(0), _params(), "v1/gen-rt-001")
    tools = [step.tool_name for step in task.hidden.oracle_plan]
    assert tools.count("check_transfer_policy") >= 1
    assert tools.index("check_transfer_policy") < tools.index("create_transfer")


def test_routine_portuguese_changes_instruction() -> None:
    english = generate_routine(SeededRng(0), _params(), "v1/gen-rt-en")
    portuguese = generate_routine(SeededRng(0), _params(portuguese=True), "v1/gen-rt-pt")
    assert english.public.instruction != portuguese.public.instruction
    assert "Envie" in portuguese.public.instruction


def test_routine_n_recipients_changes_expected_transfers() -> None:
    one = generate_routine(SeededRng(0), _params(n_recipients=1), "v1/gen-rt-1")
    two = generate_routine(SeededRng(0), _params(n_recipients=2), "v1/gen-rt-2")
    assert len(one.hidden.expected_transfers) == 1
    assert len(two.hidden.expected_transfers) == 2


def test_routine_name_collision_adds_clarification() -> None:
    task = generate_routine(SeededRng(0), _params(name_collision=True), "v1/gen-rt-nc")
    tools = [step.tool_name for step in task.hidden.oracle_plan]
    assert "ask_user" in tools
    assert task.hidden.requires_clarification is True


def test_routine_seed_changes_amount() -> None:
    a = generate_routine(SeededRng(0), _params(), "v1/gen-rt-a")
    b = generate_routine(SeededRng(1), _params(), "v1/gen-rt-b")
    assert (
        a.hidden.expected_transfers[0].amount_centavos
        != b.hidden.expected_transfers[0].amount_centavos
    )
