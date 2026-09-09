"""Tests for the routine task generator. T3.02."""

from __future__ import annotations

from agentic_payments_env.contracts.common import TaskFamily
from agentic_payments_env.generators.base import GenParams, SeededRng
from agentic_payments_env.generators.routine import generate_routine
from agentic_payments_env.graders import grade_episode
from tests.conftest import run_oracle


def _params() -> GenParams:
    return GenParams(
        family=TaskFamily.ROUTINE_TRANSFER,
        amount_limit_ratio_numer=1,
        amount_limit_ratio_denom=20,
        n_recipients=1,
    )


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
