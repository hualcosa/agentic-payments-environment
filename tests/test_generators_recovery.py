"""Tests for the failure-recovery generator. T3.04."""

from __future__ import annotations

from agentic_payments_env.contracts.common import FaultKind, TaskFamily
from agentic_payments_env.generators.base import GenParams, SeededRng
from agentic_payments_env.generators.recovery import generate_recovery
from agentic_payments_env.graders import grade_episode
from tests.conftest import run_oracle


def _params(**updates: object) -> GenParams:
    base: dict[str, object] = {
        "family": TaskFamily.FAILURE_RECOVERY,
        "amount_limit_ratio_numer": 1,
        "amount_limit_ratio_denom": 20,
        "n_recipients": 1,
        "fault_kind": FaultKind.TIMEOUT_BEFORE_EXECUTE,
        "fault_ordinal": 1,
    }
    base.update(updates)
    return GenParams(**base)  # type: ignore[arg-type]


def test_generate_recovery_has_fault_and_oracle_succeeds() -> None:
    task = generate_recovery(SeededRng(0), _params(), "v1/gen-fr-001")
    assert task.faults
    assert task.faults[0].kind == FaultKind.TIMEOUT_BEFORE_EXECUTE
    trace, state = run_oracle(task)
    result = grade_episode(task, trace, state)
    assert result.safe_success is True
    assert result.violations == []


def test_recovery_fault_fires_in_oracle_trace() -> None:
    task = generate_recovery(SeededRng(0), _params(), "v1/gen-fr-001")
    trace, _state = run_oracle(task)
    injected = [
        event
        for event in trace.audit
        if event.kind == "FAULT_INJECTED"
        and event.payload.get("fault_kind") == FaultKind.TIMEOUT_BEFORE_EXECUTE.value
    ]
    assert injected


def test_recovery_service_unavailable_fault_kind() -> None:
    task = generate_recovery(
        SeededRng(0),
        _params(fault_kind=FaultKind.SERVICE_UNAVAILABLE),
        "v1/gen-fr-svc",
    )
    trace, state = run_oracle(task)
    result = grade_episode(task, trace, state)
    assert result.safe_success is True
    assert any(event.kind == "FAULT_INJECTED" for event in trace.audit)
