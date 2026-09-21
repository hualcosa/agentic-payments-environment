"""Fault scheduler ordinal matching and uniqueness."""

from __future__ import annotations

import pytest

from agentic_payments_env.contracts.actions import Action, ToolErrorCode
from agentic_payments_env.contracts.common import FaultKind
from agentic_payments_env.contracts.tasks import FaultInjection, FaultTrigger
from agentic_payments_env.environment import PaymentsEnvironment
from agentic_payments_env.errors import TaskValidationError
from agentic_payments_env.faults import FaultScheduler
from agentic_payments_env.tools.dispatch import ToolContext, dispatch
from agentic_payments_env.world import WorldState
from tests.test_invariants import _permissive_task


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


def _dispatch_ctx() -> ToolContext:
    from agentic_payments_env.simulated_user import SimulatedUser

    task = _permissive_task()
    return ToolContext(
        state=WorldState.from_fixture(task.world),
        sim_user=SimulatedUser(task.user, task.hidden),
        step_index=1,
        task_id=task.task_id,
    )


@pytest.mark.parametrize(
    "kind",
    [FaultKind.TIMEOUT_BEFORE_EXECUTE, FaultKind.SERVICE_UNAVAILABLE],
)
def test_before_fault_preempts_invalid_arguments(kind: FaultKind) -> None:
    ctx = _dispatch_ctx()
    fault = _fault("create_transfer", 1, kind=kind)
    obs = dispatch(
        ctx,
        Action(tool_name="create_transfer", arguments={"amount_centavos": "bad"}),
        fault,
    )
    assert obs.error is not None
    assert obs.error.code in {ToolErrorCode.TIMEOUT, ToolErrorCode.SERVICE_UNAVAILABLE}
    assert obs.error.code != ToolErrorCode.INVALID_ARGUMENT
    assert ctx.state.transfers == {}


def test_after_fault_emits_single_terminal_tool_audit() -> None:
    ctx = _dispatch_ctx()
    fault = _fault("create_transfer", 1, kind=FaultKind.TIMEOUT_AFTER_EXECUTE)
    obs = dispatch(
        ctx,
        Action(
            tool_name="create_transfer",
            arguments={
                "from_account_id": "acc_ana",
                "pix_key": "maria.oliveira@example.com",
                "amount_centavos": 100,
                "idempotency_key": "after-one",
            },
        ),
        fault,
    )
    assert obs.error is not None
    assert obs.error.code == ToolErrorCode.TIMEOUT
    terminal = [
        event
        for event in ctx.state.audit
        if event.kind in {"TOOL_RESULT", "TOOL_ERROR"} and event.step_index == 1
    ]
    assert len(terminal) == 1
    assert terminal[0].kind == "TOOL_ERROR"


def test_strict_false_sanitized_error_is_audited(monkeypatch: pytest.MonkeyPatch) -> None:
    task = _permissive_task()
    task = task.model_copy(
        update={
            "faults": [
                FaultInjection(
                    trigger=FaultTrigger(tool_name="create_transfer", call_ordinal=1),
                    kind=FaultKind.TIMEOUT_AFTER_EXECUTE,
                )
            ]
        }
    )
    env = PaymentsEnvironment(task, 0, strict=False)

    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("bug")

    monkeypatch.setattr(
        "agentic_payments_env.tools.transfer.handle_create_transfer",
        boom,
    )
    env.reset()
    env.step(
        Action(
            tool_name="create_transfer",
            arguments={
                "from_account_id": "acc_ana",
                "pix_key": "maria.oliveira@example.com",
                "amount_centavos": 100,
                "idempotency_key": "strict-false",
            },
        )
    )
    terminal = [
        event
        for event in env.state.audit
        if event.kind in {"TOOL_RESULT", "TOOL_ERROR"} and event.step_index == 1
    ]
    assert len(terminal) == 1
    assert terminal[0].kind == "TOOL_ERROR"
