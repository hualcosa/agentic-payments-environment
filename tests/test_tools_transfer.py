"""create_transfer and reverse_transfer step-order tests."""

from __future__ import annotations

from datetime import timedelta

import pytest

from agentic_payments_env.contracts.actions import Action, ToolErrorCode
from agentic_payments_env.contracts.common import (
    AccountStatus,
    ActorKind,
    ConsentStatus,
    EnforcementMode,
    EpisodeOutcome,
    FaultKind,
    KycLevel,
    PolicyRuleId,
)
from agentic_payments_env.contracts.domain import Consent, ConsentScope, PolicyConfig
from agentic_payments_env.contracts.tasks import (
    ExpectedTransfer,
    FaultInjection,
    FaultTrigger,
    OracleStep,
    TaskHidden,
    UserScript,
)
from agentic_payments_env.simulated_user import SimulatedUser
from agentic_payments_env.tools.dispatch import ToolContext, dispatch
from agentic_payments_env.world import WorldState
from tests.conftest import START, default_world_fixture

MARIA = "maria.oliveira@example.com"
_STATES: list[WorldState] = []


@pytest.fixture(autouse=True)
def _invariants():
    _STATES.clear()
    yield
    for state in _STATES:
        state.check_invariants()


def _hidden() -> TaskHidden:
    return TaskHidden(
        expected_outcome=EpisodeOutcome.COMPLETED,
        expected_transfers=[ExpectedTransfer(pix_key=MARIA, amount_centavos=100)],
        oracle_plan=[OracleStep(tool_name="finish")],
        oracle_steps=1,
    )


def _ctx(*, policy: PolicyConfig | None = None, blocked: bool = False) -> ToolContext:
    fixture = default_world_fixture()
    updates: dict[str, object] = {}
    if policy is not None:
        updates["policy"] = policy
    if blocked:
        accounts = [
            account.model_copy(update={"status": AccountStatus.BLOCKED})
            if account.account_id == "acc_ana"
            else account
            for account in fixture.accounts
        ]
        updates["accounts"] = accounts
    if updates:
        fixture = fixture.model_copy(update=updates)
    ctx = ToolContext(
        state=WorldState.from_fixture(fixture),
        sim_user=SimulatedUser(UserScript(), _hidden()),
        step_index=1,
        task_id="v0/tx",
    )
    _STATES.append(ctx.state)
    return ctx


def _call(
    ctx: ToolContext,
    tool: str,
    arguments: dict[str, object],
    fault: FaultInjection | None = None,
):
    return dispatch(ctx, Action(tool_name=tool, arguments=arguments), fault)


def _grant(ctx: ToolContext, amount: int = 100) -> str:
    consent_id = ctx.state.next_id("cons")
    ctx.state.consents[consent_id] = Consent(
        consent_id=consent_id,
        customer_id="cus_ana",
        scope=ConsentScope(from_account_id="acc_ana", pix_key=MARIA, amount_centavos=amount),
        status=ConsentStatus.GRANTED,
        created_at=START,
        expires_at=START + timedelta(seconds=300),
    )
    ctx.state._record_creation(
        entity_id=consent_id,
        step_index=ctx.step_index,
        kind="CONSENT_REQUESTED",
    )
    ctx.state.emit(
        step_index=ctx.step_index,
        actor=ActorKind.SYSTEM,
        kind="CONSENT_REQUESTED",
        entity_ids=[consent_id],
    )
    ctx.state.emit(
        step_index=ctx.step_index,
        actor=ActorKind.SYSTEM,
        kind="CONSENT_GRANTED",
        entity_ids=[consent_id],
    )
    return consent_id


def _open_policy(**enforcement: EnforcementMode) -> PolicyConfig:
    modes = dict(enforcement)
    return PolicyConfig(
        consent_required=False,
        step_up_threshold_centavos=None,
        per_transfer_limit_centavos=None,
        daily_limit_centavos=None,
        night_limit_centavos=None,
        kyc_caps_centavos={level: None for level in KycLevel},
        enforcement=modes,
    )


def test_step0_before_fault_timeout_no_transfer() -> None:
    ctx = _ctx()
    fault = FaultInjection(
        trigger=FaultTrigger(tool_name="create_transfer", call_ordinal=1),
        kind=FaultKind.TIMEOUT_BEFORE_EXECUTE,
    )
    obs = _call(
        ctx,
        "create_transfer",
        {
            "from_account_id": "acc_ana",
            "pix_key": MARIA,
            "amount_centavos": 100,
            "idempotency_key": "k1",
        },
        fault,
    )
    assert obs.error is not None
    assert obs.error.code == ToolErrorCode.TIMEOUT
    assert ctx.state.transfers == {}


def test_step3_account_blocked_always_hard() -> None:
    ctx = _ctx(policy=_open_policy(), blocked=True)
    obs = _call(
        ctx,
        "create_transfer",
        {
            "from_account_id": "acc_ana",
            "pix_key": MARIA,
            "amount_centavos": 100,
            "idempotency_key": "k1",
        },
    )
    assert obs.error is not None
    assert obs.error.code == ToolErrorCode.ACCOUNT_BLOCKED


def test_step4_pix_not_found_always_hard() -> None:
    ctx = _ctx(policy=_open_policy())
    obs = _call(
        ctx,
        "create_transfer",
        {
            "from_account_id": "acc_ana",
            "pix_key": "missing@example.com",
            "amount_centavos": 100,
            "idempotency_key": "k1",
        },
    )
    assert obs.error is not None
    assert obs.error.code == ToolErrorCode.NOT_FOUND


def test_step8_insufficient_funds_always_hard() -> None:
    ctx = _ctx(policy=_open_policy())
    obs = _call(
        ctx,
        "create_transfer",
        {
            "from_account_id": "acc_ana",
            "pix_key": MARIA,
            "amount_centavos": 2_000_000,
            "idempotency_key": "k1",
        },
    )
    assert obs.error is not None
    assert obs.error.code == ToolErrorCode.INSUFFICIENT_FUNDS


def test_step5_idempotent_replay_and_conflict() -> None:
    ctx = _ctx(policy=_open_policy())
    args = {
        "from_account_id": "acc_ana",
        "pix_key": MARIA,
        "amount_centavos": 100,
        "idempotency_key": "same",
        "memo": "x",
    }
    first = _call(ctx, "create_transfer", args)
    assert first.result is not None
    balance = ctx.state.accounts["acc_ana"].balance_centavos
    replay = _call(ctx, "create_transfer", args)
    assert replay.result is not None
    assert replay.result["idempotent_replay"] is True
    assert replay.result["transfer_id"] == first.result["transfer_id"]
    assert ctx.state.accounts["acc_ana"].balance_centavos == balance
    conflict = _call(ctx, "create_transfer", {**args, "amount_centavos": 200})
    assert conflict.error is not None
    assert conflict.error.code == ToolErrorCode.IDEMPOTENCY_CONFLICT


def test_step7_hard_step_up_consent_and_limit() -> None:
    ctx = _ctx()
    auth = _call(
        ctx,
        "create_transfer",
        {
            "from_account_id": "acc_ana",
            "pix_key": MARIA,
            "amount_centavos": 100_000,
            "idempotency_key": "a",
            "consent_id": _grant(ctx, 100_000),
        },
    )
    assert auth.error is not None
    assert auth.error.code == ToolErrorCode.AUTH_REQUIRED

    ctx2 = _ctx()
    missing = _call(
        ctx2,
        "create_transfer",
        {
            "from_account_id": "acc_ana",
            "pix_key": MARIA,
            "amount_centavos": 100,
            "idempotency_key": "b",
        },
    )
    assert missing.error is not None
    assert missing.error.code == ToolErrorCode.CONSENT_REQUIRED

    ctx3 = _ctx()
    invalid = _call(
        ctx3,
        "create_transfer",
        {
            "from_account_id": "acc_ana",
            "pix_key": MARIA,
            "amount_centavos": 100,
            "idempotency_key": "c",
            "consent_id": "cons_missing",
        },
    )
    assert invalid.error is not None
    assert invalid.error.code == ToolErrorCode.CONSENT_INVALID
    assert invalid.error.details["reason"] == "NOT_FOUND"


@pytest.mark.parametrize(
    ("update", "reason"),
    [
        ({"status": ConsentStatus.PENDING}, "NOT_GRANTED"),
        ({"expires_at": START}, "EXPIRED"),
        ({"status": ConsentStatus.USED, "used_by_transfer_id": "tx_x"}, "ALREADY_USED"),
        (
            {
                "scope": ConsentScope(
                    from_account_id="acc_external", pix_key=MARIA, amount_centavos=100
                )
            },
            "SCOPE_MISMATCH",
        ),
    ],
)
def test_step7_consent_invalid_each_reason(update: dict[str, object], reason: str) -> None:
    ctx = _ctx()
    consent_id = _grant(ctx, 100)
    consent = ctx.state.consents[consent_id].model_copy(update=update)
    ctx.state.consents[consent_id] = consent
    obs = _call(
        ctx,
        "create_transfer",
        {
            "from_account_id": "acc_ana",
            "pix_key": MARIA,
            "amount_centavos": 100,
            "idempotency_key": "inv",
            "consent_id": consent_id,
        },
    )
    assert obs.error is not None
    assert obs.error.code == ToolErrorCode.CONSENT_INVALID
    assert obs.error.details["reason"] == reason

    ctx4 = _ctx()
    limit = _call(
        ctx4,
        "create_transfer",
        {
            "from_account_id": "acc_ana",
            "pix_key": MARIA,
            "amount_centavos": 500_001,
            "idempotency_key": "d",
            "consent_id": _grant(ctx4, 500_001),
        },
    )
    assert limit.error is not None
    assert limit.error.code == ToolErrorCode.POLICY_VIOLATION
    assert any(row["rule"] == "PER_TRANSFER_LIMIT" for row in limit.error.details["violations"])


def test_soft_and_silent_limit_execute() -> None:
    soft = _ctx(
        policy=PolicyConfig(
            consent_required=False,
            step_up_threshold_centavos=None,
            enforcement={PolicyRuleId.PER_TRANSFER_LIMIT: EnforcementMode.SOFT},
        )
    )
    obs = _call(
        soft,
        "create_transfer",
        {
            "from_account_id": "acc_ana",
            "pix_key": MARIA,
            "amount_centavos": 500_001,
            "idempotency_key": "soft",
        },
    )
    assert obs.kind == "tool_result"
    assert obs.warnings
    assert any(event.kind == "POLICY_VIOLATION_EXECUTED" for event in soft.state.audit)

    silent = _ctx(
        policy=PolicyConfig(
            consent_required=False,
            step_up_threshold_centavos=None,
            enforcement={PolicyRuleId.PER_TRANSFER_LIMIT: EnforcementMode.SILENT},
        )
    )
    obs_s = _call(
        silent,
        "create_transfer",
        {
            "from_account_id": "acc_ana",
            "pix_key": MARIA,
            "amount_centavos": 500_001,
            "idempotency_key": "silent",
        },
    )
    assert obs_s.kind == "tool_result"
    assert obs_s.warnings == []
    assert any(event.kind == "POLICY_VIOLATION_EXECUTED" for event in silent.state.audit)


def test_step9_balances_ledger_consent_and_completed_payload() -> None:
    ctx = _ctx()
    consent_id = _grant(ctx, 100)
    obs = _call(
        ctx,
        "create_transfer",
        {
            "from_account_id": "acc_ana",
            "pix_key": MARIA,
            "amount_centavos": 100,
            "idempotency_key": "ok",
            "consent_id": consent_id,
        },
    )
    assert obs.result is not None
    assert ctx.state.accounts["acc_ana"].balance_centavos == 1_000_000 - 100
    runtime = ctx.state.ledger[ctx.state._fixture_entry_count :]
    assert sum(entry.delta_centavos for entry in runtime) == 0
    assert ctx.state.consents[consent_id].status == ConsentStatus.USED
    kinds = [event.kind for event in ctx.state.audit]
    assert kinds.index("TRANSFER_CREATED") < kinds.index("TRANSFER_COMPLETED")
    completed = next(event for event in ctx.state.audit if event.kind == "TRANSFER_COMPLETED")
    assert completed.payload["consent_id"] == consent_id
    assert completed.payload["consent_status_at_execution"] == "GRANTED"
    assert completed.payload["consent_scope_matched"] is True
    assert "auth_level_at_execution" in completed.payload


def test_step10_after_fault_timeout_but_transfer_exists() -> None:
    ctx = _ctx(policy=_open_policy())
    fault = FaultInjection(
        trigger=FaultTrigger(tool_name="create_transfer", call_ordinal=1),
        kind=FaultKind.TIMEOUT_AFTER_EXECUTE,
    )
    obs = _call(
        ctx,
        "create_transfer",
        {
            "from_account_id": "acc_ana",
            "pix_key": MARIA,
            "amount_centavos": 100,
            "idempotency_key": "after",
        },
        fault,
    )
    assert obs.error is not None
    assert obs.error.code == ToolErrorCode.TIMEOUT
    found = _call(ctx, "get_transfer_by_idempotency_key", {"idempotency_key": "after"})
    assert found.result is not None
    assert found.result["status"] == "COMPLETED"


def test_reversal_happy_and_errors() -> None:
    ctx = _ctx(policy=_open_policy())
    created = _call(
        ctx,
        "create_transfer",
        {
            "from_account_id": "acc_ana",
            "pix_key": MARIA,
            "amount_centavos": 100,
            "idempotency_key": "orig",
        },
    )
    assert created.result is not None
    tid = created.result["transfer_id"]
    rev = _call(ctx, "reverse_transfer", {"transfer_id": tid, "reason": "undo"})
    assert rev.result is not None
    assert ctx.state.accounts["acc_ana"].balance_centavos == 1_000_000
    assert ctx.state.transfers[tid].status.value == "REVERSED"
    assert ctx.state.transfers[tid].reversed_by == rev.result["transfer_id"]
    again = _call(ctx, "reverse_transfer", {"transfer_id": tid, "reason": "undo"})
    assert again.error is not None
    assert again.error.details["reason"] == "ALREADY_REVERSED"

    ctx2 = _ctx(policy=_open_policy())
    created2 = _call(
        ctx2,
        "create_transfer",
        {
            "from_account_id": "acc_ana",
            "pix_key": MARIA,
            "amount_centavos": 100,
            "idempotency_key": "orig2",
        },
    )
    assert created2.result is not None
    ctx2.state.now = ctx2.state.now + timedelta(
        seconds=ctx2.state.policy.reversal_window_seconds + 1
    )
    expired = _call(
        ctx2, "reverse_transfer", {"transfer_id": created2.result["transfer_id"], "reason": "late"}
    )
    assert expired.error is not None
    assert expired.error.details["reason"] == "WINDOW_EXPIRED"

    ctx3 = _ctx(policy=_open_policy())
    created3 = _call(
        ctx3,
        "create_transfer",
        {
            "from_account_id": "acc_ana",
            "pix_key": MARIA,
            "amount_centavos": 100,
            "idempotency_key": "orig3",
        },
    )
    assert created3.result is not None
    ctx3.state.principal_customer_id = "cus_external"
    not_sender = _call(
        ctx3, "reverse_transfer", {"transfer_id": created3.result["transfer_id"], "reason": "no"}
    )
    assert not_sender.error is not None
    assert not_sender.error.details["reason"] == "NOT_SENDER"

    ctx4 = _ctx(policy=_open_policy())
    created4 = _call(
        ctx4,
        "create_transfer",
        {
            "from_account_id": "acc_ana",
            "pix_key": MARIA,
            "amount_centavos": 100,
            "idempotency_key": "orig4",
        },
    )
    assert created4.result is not None
    rev4 = _call(
        ctx4, "reverse_transfer", {"transfer_id": created4.result["transfer_id"], "reason": "undo"}
    )
    assert rev4.result is not None
    is_rev = _call(
        ctx4, "reverse_transfer", {"transfer_id": rev4.result["transfer_id"], "reason": "no"}
    )
    assert is_rev.error is not None
    assert is_rev.error.details["reason"] == "IS_REVERSAL"
