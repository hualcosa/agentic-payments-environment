"""Fault scheduler ordinal matching and uniqueness."""

from __future__ import annotations

import pytest

from agentic_payments_env.contracts.common import FaultKind
from agentic_payments_env.contracts.tasks import FaultInjection, FaultTrigger
from agentic_payments_env.errors import TaskValidationError
from agentic_payments_env.faults import FaultScheduler


def _fault(
    tool: str, ordinal: int, kind: FaultKind = FaultKind.SERVICE_UNAVAILABLE
) -> FaultInjection:
    return FaultInjection(trigger=FaultTrigger(tool_name=tool, call_ordinal=ordinal), kind=kind)


def test_scheduler_fires_on_exact_ordinal_once() -> None:
    fault = _fault("create_transfer", 2)
    scheduler = FaultScheduler([fault])
    assert scheduler.check("create_transfer") is None
    fired = scheduler.check("create_transfer")
    assert fired is fault
    assert scheduler.check("create_transfer") is None
    assert scheduler.fired == [fault]


def test_scheduler_counts_errors_as_calls() -> None:
    fault = _fault("get_account_balance", 2)
    scheduler = FaultScheduler([fault])
    scheduler.check("get_account_balance")
    assert scheduler.check("get_account_balance") is fault


def test_two_faults_on_same_call_raise_at_construction() -> None:
    with pytest.raises(TaskValidationError):
        FaultScheduler([_fault("create_transfer", 1), _fault("create_transfer", 1)])
