"""Read-tool happy paths, ownership hiding, stale reads, and policy dry-run."""

from __future__ import annotations

from datetime import timedelta

from agentic_payments_env.contracts.actions import Action, ToolErrorCode
from agentic_payments_env.contracts.common import (
    ActorKind,
    EpisodeOutcome,
    FaultKind,
    Initiator,
    TransferStatus,
)
from agentic_payments_env.contracts.domain import Transfer
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
from tests.test_world import START, default_world_fixture

MARIA = "maria.oliveira@example.com"


def _hidden() -> TaskHidden:
    return TaskHidden(
        expected_outcome=EpisodeOutcome.COMPLETED,
        expected_transfers=[ExpectedTransfer(pix_key=MARIA, amount_centavos=25000)],
        oracle_plan=[OracleStep(tool_name="finish")],
        oracle_steps=1,
    )


def _ctx(*, extra_transfers: list[Transfer] | None = None) -> ToolContext:
    fixture = default_world_fixture()
    updates: dict[str, object] = {
        "balance_history_seed": {"acc_ana": [(START - timedelta(seconds=5), 999_000)]},
    }
    if extra_transfers:
        updates["transfers"] = extra_transfers
    fixture = fixture.model_copy(update=updates)
    world = WorldState.from_fixture(fixture)
    return ToolContext(
        state=world,
        sim_user=SimulatedUser(UserScript(), _hidden()),
        step_index=1,
        task_id="v0/rt-001",
    )


def _call(
    ctx: ToolContext,
    tool: str,
    arguments: dict[str, object] | None = None,
    fault: FaultInjection | None = None,
):
    return dispatch(ctx, Action(tool_name=tool, arguments=arguments or {}), fault)


def _fixture_transfer() -> Transfer:
    return Transfer(
        transfer_id="tx_fix_001",
        from_account_id="acc_ana",
        to_pix_key=MARIA,
        to_account_id="acc_external",
        to_holder_name_snapshot="MARIA OLIVEIRA SANTOS",
        amount_centavos=25000,
        status=TransferStatus.COMPLETED,
        idempotency_key="fix-1",
        consent_id=None,
        created_at=START,
        completed_at=START,
        initiated_by=Initiator.FIXTURE,
    )


def test_get_customer_profile_happy_path() -> None:
    obs = _call(_ctx(), "get_customer_profile")
    assert obs.kind == "tool_result"
    assert obs.result is not None
    assert obs.result["customer_id"] == "cus_ana"
    assert obs.result["display_name"] == "Ana Souza"
    assert obs.result["auth_level"] == "BASIC"
    assert obs.result["limits"]["per_transfer_limit_centavos"] == 500_000
    assert obs.result["limits"]["daily_used_centavos"] == 0


def test_get_account_balance_happy_path() -> None:
    obs = _call(_ctx(), "get_account_balance", {"account_id": "acc_ana"})
    assert obs.result is not None
    assert obs.result["balance_centavos"] == 1_000_000
    assert obs.result["status"] == "ACTIVE"
    assert "as_of" in obs.result


def test_get_account_balance_foreign_not_found() -> None:
    obs = _call(_ctx(), "get_account_balance", {"account_id": "acc_external"})
    assert obs.error is not None
    assert obs.error.code == ToolErrorCode.NOT_FOUND


def test_stale_read_returns_older_balance() -> None:
    ctx = _ctx()
    fault = FaultInjection(
        trigger=FaultTrigger(tool_name="get_account_balance", call_ordinal=1),
        kind=FaultKind.STALE_READ,
        stale_age_steps=1,
    )
    obs = _call(ctx, "get_account_balance", {"account_id": "acc_ana"}, fault)
    assert obs.result is not None
    assert obs.result["balance_centavos"] == 999_000
    older = START - timedelta(seconds=5)
    assert obs.result["as_of"] == older.isoformat()
    assert obs.observed_at == older


def test_service_unavailable_emits_invisible_fault() -> None:
    ctx = _ctx()
    fault = FaultInjection(
        trigger=FaultTrigger(tool_name="get_customer_profile", call_ordinal=1),
        kind=FaultKind.SERVICE_UNAVAILABLE,
    )
    obs = _call(ctx, "get_customer_profile", fault=fault)
    assert obs.error is not None
    assert obs.error.code == ToolErrorCode.SERVICE_UNAVAILABLE
    injected = [event for event in ctx.state.audit if event.kind == "FAULT_INJECTED"]
    assert len(injected) == 1
    assert injected[0].visible_to_agent is False
    assert injected[0].actor == ActorKind.SYSTEM


def test_list_beneficiaries_happy_path() -> None:
    obs = _call(_ctx(), "list_beneficiaries")
    assert obs.result is not None
    ids = [row["beneficiary_id"] for row in obs.result["beneficiaries"]]
    assert ids == sorted(ids)
    assert "ben_maria" in ids


def test_lookup_pix_key_happy_path_hides_account_id() -> None:
    obs = _call(_ctx(), "lookup_pix_key", {"pix_key": MARIA})
    assert obs.result is not None
    assert obs.result["holder_name"] == "MARIA OLIVEIRA SANTOS"
    assert obs.result["bank_name"] == "Banco Alfa"
    assert "account_id" not in obs.result


def test_check_transfer_policy_too_large() -> None:
    obs = _call(
        _ctx(),
        "check_transfer_policy",
        {"from_account_id": "acc_ana", "pix_key": MARIA, "amount_centavos": 500_001},
    )
    assert obs.result is not None
    rules = [row["rule"] for row in obs.result["violations"]]
    assert "PER_TRANSFER_LIMIT" in rules
    assert obs.result["would_fail_with"] == "POLICY_VIOLATION"
    assert obs.result["allowed"] is False
    assert obs.result["requires_consent"] is True


def test_get_transfer_and_idempotency_and_list() -> None:
    ctx = _ctx(extra_transfers=[_fixture_transfer()])
    by_id = _call(ctx, "get_transfer", {"transfer_id": "tx_fix_001"})
    assert by_id.result is not None
    assert by_id.result["amount_centavos"] == 25000
    assert "to_account_id" not in by_id.result
    by_key = _call(ctx, "get_transfer_by_idempotency_key", {"idempotency_key": "fix-1"})
    assert by_key.result is not None
    assert by_key.result["transfer_id"] == "tx_fix_001"
    listed = _call(ctx, "list_transfers", {"account_id": "acc_ana"})
    assert listed.result is not None
    assert listed.result["transfers"][0]["direction"] == "OUT"
    assert listed.result["transfers"][0]["memo"] == ""
