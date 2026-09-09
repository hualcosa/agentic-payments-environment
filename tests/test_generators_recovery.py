"""Tests for the failure-recovery generator. T3.04."""

from __future__ import annotations

from agentic_payments_env.contracts.common import FaultKind, TaskFamily
from agentic_payments_env.generators.base import GenParams, SeededRng
from agentic_payments_env.generators.recovery import generate_recovery
from agentic_payments_env.graders import grade_episode
from tests.conftest import run_oracle


def _params() -> GenParams:
    return GenParams(
        family=TaskFamily.FAILURE_RECOVERY,
        amount_limit_ratio_numer=1,
        amount_limit_ratio_denom=20,
        n_recipients=1,
        fault_kind=FaultKind.TIMEOUT_BEFORE_EXECUTE,
        fault_ordinal=1,
    )


def test_generate_recovery_has_fault_and_oracle_succeeds() -> None:
    task = generate_recovery(SeededRng(0), _params(), "v1/gen-fr-001")
    assert task.faults
    assert task.faults[0].kind == FaultKind.TIMEOUT_BEFORE_EXECUTE
    trace, state = run_oracle(task)
    result = grade_episode(task, trace, state)
    assert result.safe_success is True
