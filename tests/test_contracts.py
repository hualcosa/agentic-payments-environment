"""Contract tests (part 1): enums, datetime awareness, money constraints."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

import pytest
from pydantic import ValidationError

from agentic_payments_env.benchmark.loader import load_task_file
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
from agentic_payments_env.contracts.grading import (
    BenchmarkReport,
    Dimension,
    EpisodeResult,
    FamilySummary,
    GraderResult,
    Severity,
)
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


START = datetime(2026, 3, 10, 14, 0, tzinfo=UTC)


def minimal_world(**overrides: object) -> WorldFixture:
    world = WorldFixture(
        start_time=START,
        customers=[
            Customer(
                customer_id="cus_ana",
                display_name="Ana",
                document_masked="***",
                kyc_level=KycLevel.FULL,
            )
        ],
        accounts=[
            Account(
                account_id="acc_ana",
                customer_id="cus_ana",
                balance_centavos=1_000_000,
            ),
            Account(
                account_id="acc_external",
                customer_id="cus_external",
                balance_centavos=10_000_000_000,
            ),
        ],
        pix_directory=[
            PixKeyRecord(
                pix_key="maria@example.com",
                key_type=PixKeyType.EMAIL,
                holder_name="MARIA",
                holder_document_masked="***",
                bank_name="Bank",
                account_id="acc_external",
            )
        ],
        principal_customer_id="cus_ana",
        principal_account_id="acc_ana",
    )
    if overrides:
        return world.model_copy(update=overrides)
    return world


def minimal_task(**overrides: object) -> TaskSpec:
    hidden = TaskHidden(
        expected_outcome=EpisodeOutcome.DECLINED,
        oracle_plan=[
            OracleStep(tool_name="finish", arguments={"outcome": "DECLINED", "report": "x"})
        ],
        oracle_steps=1,
    )
    task = TaskSpec(
        task_id="v0/test",
        family=TaskFamily.ROUTINE_TRANSFER,
        title="test",
        world=minimal_world(),
        public=TaskPublic(instruction="Do something."),
        hidden=hidden,
    )
    if overrides:
        return task.model_copy(update=overrides)
    return task


def sample_observation(kind: str = "reset") -> Observation:
    return Observation(
        step_index=0,
        sim_time=START,
        kind=kind,  # type: ignore[arg-type]
        observed_at=START,
        instruction="Do something." if kind == "reset" else None,
    )


def _valid_task_payload() -> dict[str, object]:
    return minimal_task().model_dump(mode="json")


def _valid_trace_payload() -> dict[str, object]:
    reset = sample_observation("reset")
    return EpisodeTrace(
        task_id="v0/test",
        seed=0,
        agent_name="oracle",
        reset_observation=reset,
        steps=[],
        termination=TerminationReason.FINISHED,
        declared_outcome=EpisodeOutcome.DECLINED,
        final_report="done",
        final_state_hash="b" * 64,
        audit=[],
    ).model_dump(mode="json")


def _valid_result_payload() -> dict[str, object]:
    dimensions = {
        dimension: GraderResult(dimension=dimension, applicable=True, score=1.0, passed=True)
        for dimension in Dimension
    }
    return EpisodeResult(
        task_id="v0/test",
        family=TaskFamily.ROUTINE_TRANSFER,
        seed=0,
        agent_name="oracle",
        termination=TerminationReason.FINISHED,
        declared_outcome=EpisodeOutcome.COMPLETED,
        expected_outcome=EpisodeOutcome.COMPLETED,
        steps_used=1,
        dimensions=dimensions,
        violations=[],
        catastrophic_codes=[],
        task_success=True,
        safe_success=True,
    ).model_dump(mode="json")


def _valid_report_payload() -> dict[str, object]:
    result_payload = _valid_result_payload()
    summary = FamilySummary(
        family=TaskFamily.ROUTINE_TRANSFER,
        episodes=1,
        task_success_rate=1.0,
        catastrophic_rate=0.0,
        safe_success_rate=1.0,
        mean_dimension_scores={dimension: 1.0 for dimension in Dimension},
        violation_counts={},
        catastrophic_counts={},
    )
    return BenchmarkReport(
        benchmark_id="v0",
        agent_name="oracle",
        seeds=[0],
        episodes=[EpisodeResult.model_validate(result_payload)],
        summaries=[summary],
    ).model_dump(mode="json")


_ARTIFACT_CASES: tuple[tuple[str, type[object], object], ...] = (
    ("TaskSpec", TaskSpec, _valid_task_payload),
    ("EpisodeTrace", EpisodeTrace, _valid_trace_payload),
    ("EpisodeResult", EpisodeResult, _valid_result_payload),
    ("BenchmarkReport", BenchmarkReport, _valid_report_payload),
)


@pytest.mark.parametrize(("name", "model", "payload_fn"), _ARTIFACT_CASES)
def test_schema_version_accepts_0_1(name: str, model: type[object], payload_fn: object) -> None:
    del name
    payload = payload_fn()  # type: ignore[operator]
    payload["schema_version"] = "0.1"
    validated = model.model_validate(payload)  # type: ignore[attr-defined]
    assert validated.model_dump(mode="json")["schema_version"] == "0.1"


@pytest.mark.parametrize(
    "bad_version",
    ["0", "1.0", "0.1.0", "abc", "", "0.x", "x.1"],
)
@pytest.mark.parametrize(("name", "model", "payload_fn"), _ARTIFACT_CASES)
def test_schema_version_rejects_malformed_or_unknown_major(
    bad_version: str,
    name: str,
    model: type[object],
    payload_fn: object,
) -> None:
    del name
    payload = payload_fn()  # type: ignore[operator]
    payload["schema_version"] = bad_version
    with pytest.raises(ValidationError):
        model.model_validate(payload)  # type: ignore[attr-defined]


@pytest.mark.parametrize("missing_field", ["audit"])
def test_episode_trace_requires_field(missing_field: str) -> None:
    payload = _valid_trace_payload()
    del payload[missing_field]
    with pytest.raises(ValidationError):
        EpisodeTrace.model_validate(payload)


@pytest.mark.parametrize("missing_field", ["violations", "catastrophic_codes"])
def test_episode_result_requires_field(missing_field: str) -> None:
    payload = _valid_result_payload()
    del payload[missing_field]
    with pytest.raises(ValidationError):
        EpisodeResult.model_validate(payload)


@pytest.mark.parametrize("missing_field", ["violation_counts", "catastrophic_counts"])
def test_family_summary_requires_field(missing_field: str) -> None:
    payload = {
        "family": TaskFamily.ROUTINE_TRANSFER.value,
        "episodes": 0,
        "task_success_rate": 0.0,
        "catastrophic_rate": 0.0,
        "safe_success_rate": 0.0,
        "mean_dimension_scores": {dimension.value: None for dimension in Dimension},
        "violation_counts": {},
        "catastrophic_counts": {},
    }
    del payload[missing_field]
    with pytest.raises(ValidationError):
        FamilySummary.model_validate(payload)


def test_benchmark_report_requires_summaries() -> None:
    payload = _valid_report_payload()
    del payload["summaries"]
    with pytest.raises(ValidationError):
        BenchmarkReport.model_validate(payload)


def test_load_task_file_rejects_unknown_major(tmp_path: object) -> None:
    from pathlib import Path

    path = Path(str(tmp_path)) / "bad.json"
    payload = _valid_task_payload()
    payload["schema_version"] = "1.0"
    path.write_text(__import__("json").dumps(payload), encoding="utf-8")
    with pytest.raises(ValidationError):
        load_task_file(path)
