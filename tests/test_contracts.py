"""Contract tests (part 1): enums, datetime awareness, money constraints."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

import pytest
from pydantic import ValidationError

from agentic_payments_env.contracts.actions import Observation, ToolError, ToolErrorCode
from agentic_payments_env.contracts.common import (
    AccountStatus,
    ActorKind,
    AuthLevel,
    ChallengeStatus,
    ConsentStatus,
    EnforcementMode,
    EpisodeOutcome,
    FaultKind,
    Initiator,
    KycLevel,
    PixKeyType,
    PolicyRuleId,
    TaskFamily,
    TerminationReason,
    TransferStatus,
)
from agentic_payments_env.contracts.domain import (
    Account,
    AuditEvent,
    Beneficiary,
    Consent,
    ConsentScope,
    Customer,
    PixKeyRecord,
    PolicyConfig,
    Transfer,
)
from agentic_payments_env.contracts.grading import Dimension, Severity
from agentic_payments_env.contracts.tasks import (
    ConsentResponse,
    ExpectedTransfer,
    FaultInjection,
    FaultTrigger,
    OracleStep,
    StepUpResponse,
    TaskHidden,
    TaskPublic,
    TaskSpec,
    UserVigilance,
)
from agentic_payments_env.contracts.trace import EpisodeTrace, StateTransition
from agentic_payments_env.contracts.world import WorldFixture

AWARE = datetime(2024, 1, 15, 12, 0, tzinfo=UTC)
NAIVE = datetime(2024, 1, 15, 12, 0)

ENUMS: tuple[type[Enum], ...] = (
    KycLevel,
    AccountStatus,
    AuthLevel,
    PixKeyType,
    TransferStatus,
    ConsentStatus,
    ChallengeStatus,
    ActorKind,
    Initiator,
    EnforcementMode,
    PolicyRuleId,
    EpisodeOutcome,
    TerminationReason,
    TaskFamily,
    FaultKind,
    ToolErrorCode,
    ConsentResponse,
    StepUpResponse,
    UserVigilance,
    Dimension,
    Severity,
)


@pytest.mark.parametrize("enum_cls", ENUMS)
def test_enum_values_equal_names(enum_cls: type[Enum]) -> None:
    for member in enum_cls:
        assert member.value == member.name


def test_naive_datetime_rejected_in_beneficiary() -> None:
    with pytest.raises(ValidationError):
        Beneficiary(
            beneficiary_id="ben_000001",
            customer_id="cus_000001",
            nickname="Ana",
            pix_key="ana@example.com",
            created_at=NAIVE,
        )


def test_naive_datetime_rejected_in_consent() -> None:
    scope = ConsentScope(from_account_id="acc_ana", pix_key="k", amount_centavos=100)
    with pytest.raises(ValidationError):
        Consent(
            consent_id="cons_000001",
            customer_id="cus_000001",
            scope=scope,
            status=ConsentStatus.GRANTED,
            created_at=NAIVE,
            expires_at=AWARE,
        )


def test_naive_datetime_rejected_in_transfer() -> None:
    with pytest.raises(ValidationError):
        Transfer(
            transfer_id="tx_000001",
            from_account_id="acc_ana",
            to_pix_key="k",
            to_account_id="acc_external",
            to_holder_name_snapshot="Bob",
            amount_centavos=100,
            status=TransferStatus.PENDING,
            idempotency_key="idem-1",
            consent_id=None,
            created_at=NAIVE,
        )


def test_naive_datetime_rejected_in_audit_event() -> None:
    with pytest.raises(ValidationError):
        AuditEvent(
            seq=1,
            timestamp=NAIVE,
            step_index=0,
            actor=ActorKind.SYSTEM,
            kind="RESET",
        )


def test_transfer_amount_zero_rejected() -> None:
    with pytest.raises(ValidationError):
        Transfer(
            transfer_id="tx_000001",
            from_account_id="acc_ana",
            to_pix_key="k",
            to_account_id="acc_external",
            to_holder_name_snapshot="Bob",
            amount_centavos=0,
            status=TransferStatus.PENDING,
            idempotency_key="idem-1",
            consent_id=None,
            created_at=AWARE,
        )


def test_extra_field_forbidden() -> None:
    with pytest.raises(ValidationError):
        PolicyConfig.model_validate({"unexpected": True})


@pytest.mark.parametrize("rule", list(PolicyRuleId))
def test_policy_config_default_mode_is_hard(rule: PolicyRuleId) -> None:
    assert PolicyConfig().mode(rule) == EnforcementMode.HARD


def _world(*, extra_account_customer: str | None = None) -> WorldFixture:
    principal_customer = extra_account_customer or "cus_ana"
    return WorldFixture(
        start_time=AWARE,
        customers=[
            Customer(
                customer_id="cus_ana",
                display_name="Ana",
                document_masked="***.456.789-**",
                kyc_level=KycLevel.FULL,
            ),
            Customer(
                customer_id="cus_external",
                display_name="External",
                document_masked="***",
                kyc_level=KycLevel.NONE,
            ),
        ],
        accounts=[
            Account(account_id="acc_ana", customer_id=principal_customer, balance_centavos=100_000),
            Account(
                account_id="acc_external",
                customer_id="cus_external",
                balance_centavos=10_000_000_000,
            ),
        ],
        pix_directory=[
            PixKeyRecord(
                pix_key="bob@example.com",
                key_type=PixKeyType.EMAIL,
                holder_name="Bob",
                holder_document_masked="***",
                bank_name="Bank",
                account_id="acc_external",
            )
        ],
        principal_customer_id="cus_ana",
        principal_account_id="acc_ana",
    )


def _task(
    *,
    oracle_steps: int | None = None,
    expected_pix_key: str = "bob@example.com",
    extra_account_customer: str | None = None,
    faults: list[FaultInjection] | None = None,
) -> TaskSpec:
    plan = [OracleStep(tool_name="finish", arguments={"outcome": "COMPLETED", "report": "ok"})]
    return TaskSpec(
        task_id="v0/rt-test",
        family=TaskFamily.ROUTINE_TRANSFER,
        title="test",
        world=_world(extra_account_customer=extra_account_customer),
        public=TaskPublic(instruction="pay Bob"),
        faults=faults or [],
        hidden=TaskHidden(
            expected_outcome=EpisodeOutcome.COMPLETED,
            expected_transfers=[ExpectedTransfer(pix_key=expected_pix_key, amount_centavos=100)],
            oracle_plan=plan,
            oracle_steps=len(plan) if oracle_steps is None else oracle_steps,
        ),
    )


def test_req_con_09_oracle_steps_must_match_plan() -> None:
    with pytest.raises(ValidationError):
        _task(oracle_steps=2)


def test_req_con_09_expected_pix_key_must_exist() -> None:
    with pytest.raises(ValidationError):
        _task(expected_pix_key="missing@example.com")


def test_req_con_09_principal_account_must_belong_to_principal() -> None:
    with pytest.raises(ValidationError):
        _task(extra_account_customer="cus_external")


def test_req_con_09_stale_read_requires_stale_age_steps() -> None:
    with pytest.raises(ValidationError):
        _task(
            faults=[
                FaultInjection(
                    trigger=FaultTrigger(tool_name="get_account_balance", call_ordinal=1),
                    kind=FaultKind.STALE_READ,
                )
            ]
        )


def test_req_con_09_non_stale_fault_rejects_stale_age_steps() -> None:
    with pytest.raises(ValidationError):
        _task(
            faults=[
                FaultInjection(
                    trigger=FaultTrigger(tool_name="create_transfer", call_ordinal=1),
                    kind=FaultKind.TIMEOUT_BEFORE_EXECUTE,
                    stale_age_steps=1,
                )
            ]
        )


def test_observation_rejects_both_result_and_error() -> None:
    with pytest.raises(ValidationError):
        Observation(
            step_index=1,
            sim_time=AWARE,
            kind="tool_result",
            tool_name="get_account_balance",
            result={"balance_centavos": 1},
            error=ToolError(code=ToolErrorCode.NOT_FOUND, message="no"),
            observed_at=AWARE,
        )


def test_episode_trace_json_round_trip() -> None:
    reset = Observation(
        step_index=0,
        sim_time=AWARE,
        kind="reset",
        observed_at=AWARE,
        instruction="pay Bob",
        principal={"customer_id": "cus_ana", "account_id": "acc_ana", "display_name": "Ana"},
        available_tools=["finish"],
    )
    event = AuditEvent(
        seq=1,
        timestamp=AWARE,
        step_index=0,
        actor=ActorKind.SYSTEM,
        kind="RESET",
    )
    trace = EpisodeTrace(
        task_id="v0/rt-test",
        seed=0,
        agent_name="oracle",
        reset_observation=reset,
        steps=[],
        termination=TerminationReason.FINISHED,
        declared_outcome=EpisodeOutcome.COMPLETED,
        final_report="ok",
        final_state_hash="abc",
        audit=[event],
        schema_version="0.1",
    )
    dumped = trace.model_dump(mode="json")
    restored = EpisodeTrace.model_validate(dumped)
    assert restored.model_dump(mode="json") == dumped
    assert StateTransition(
        step_index=1,
        state_hash_before="a",
        state_hash_after="b",
        audit_seq_range=(0, 0),
        balances_after={"acc_ana": 1},
    )


def test_star_import_exposes_every_named_contract() -> None:
    namespace: dict[str, object] = {}
    exec("from agentic_payments_env.contracts import *", namespace)
    required = {
        "FrozenModel",
        "MutableModel",
        "AuthState",
        "Customer",
        "Account",
        "PixKeyRecord",
        "Beneficiary",
        "ConsentScope",
        "Consent",
        "StepUpChallenge",
        "Transfer",
        "LedgerEntry",
        "AuditEvent",
        "NightWindow",
        "PolicyConfig",
        "WorldFixture",
        "WorldState",
        "Action",
        "ToolErrorCode",
        "PolicyWarning",
        "ToolError",
        "Observation",
        "ExpectedTransfer",
        "InjectionTarget",
        "ConsentResponse",
        "StepUpResponse",
        "UserVigilance",
        "UserScript",
        "FaultTrigger",
        "FaultInjection",
        "TaskPublic",
        "OracleStep",
        "TaskHidden",
        "TaskSpec",
        "StateTransition",
        "Step",
        "EpisodeTrace",
        "Dimension",
        "Severity",
        "Violation",
        "GraderResult",
        "EpisodeResult",
        "FamilySummary",
        "BenchmarkReport",
    }
    missing = sorted(required - namespace.keys())
    assert missing == []
