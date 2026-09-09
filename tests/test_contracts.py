"""Contract validation tests. REQ-CON-01..09."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

import pytest
from pydantic import ValidationError

from agentic_payments_env.benchmark.loader import load_task_file
from agentic_payments_env.contracts import (
    Account,
    Action,
    Customer,
    EpisodeOutcome,
    EpisodeTrace,
    FaultInjection,
    FaultKind,
    FaultTrigger,
    KycLevel,
    Observation,
    OracleStep,
    PixKeyRecord,
    PixKeyType,
    StateTransition,
    Step,
    TaskFamily,
    TaskHidden,
    TaskPublic,
    TaskSpec,
    TerminationReason,
    ToolError,
    ToolErrorCode,
    WorldFixture,
)
from agentic_payments_env.contracts.common import (
    AccountStatus,
    ActorKind,
    AuthLevel,
    ChallengeStatus,
    ConsentStatus,
    EnforcementMode,
    Initiator,
    PolicyRuleId,
    TransferStatus,
)
from agentic_payments_env.contracts.common import (
    EpisodeOutcome as CommonEpisodeOutcome,
)
from agentic_payments_env.contracts.common import (
    FaultKind as CommonFaultKind,
)
from agentic_payments_env.contracts.common import (
    KycLevel as CommonKycLevel,
)
from agentic_payments_env.contracts.common import (
    PixKeyType as CommonPixKeyType,
)
from agentic_payments_env.contracts.common import (
    TaskFamily as CommonTaskFamily,
)
from agentic_payments_env.contracts.common import (
    TerminationReason as CommonTerminationReason,
)
from agentic_payments_env.contracts.domain import (
    AuditEvent,
    Beneficiary,
    Consent,
    ConsentScope,
    PolicyConfig,
    Transfer,
)
from agentic_payments_env.contracts.grading import (
    BenchmarkReport,
    Dimension,
    EpisodeResult,
    FamilySummary,
    GraderResult,
)

START = datetime(2026, 3, 10, 14, 0, tzinfo=UTC)

ENUMS: tuple[type[Enum], ...] = (
    CommonKycLevel,
    AccountStatus,
    AuthLevel,
    CommonPixKeyType,
    TransferStatus,
    ConsentStatus,
    ChallengeStatus,
    ActorKind,
    Initiator,
    EnforcementMode,
    PolicyRuleId,
    CommonEpisodeOutcome,
    CommonTerminationReason,
    CommonTaskFamily,
    CommonFaultKind,
)


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


@pytest.mark.parametrize("enum_cls", ENUMS)
def test_enum_values_equal_names(enum_cls: type[Enum]) -> None:
    for member in enum_cls:
        assert member.value == member.name


def test_beneficiary_rejects_naive_datetime() -> None:
    with pytest.raises(ValidationError):
        Beneficiary(
            beneficiary_id="ben_001",
            customer_id="cus_001",
            nickname="Maria",
            pix_key="maria@example.com",
            created_at=datetime(2026, 3, 10, 14, 0),
        )


def test_consent_rejects_naive_datetime() -> None:
    with pytest.raises(ValidationError):
        Consent(
            consent_id="cons_001",
            customer_id="cus_001",
            scope=ConsentScope(
                from_account_id="acc_001",
                pix_key="maria@example.com",
                amount_centavos=100,
            ),
            status=ConsentStatus.GRANTED,
            created_at=datetime(2026, 3, 10, 14, 0),
            expires_at=datetime(2026, 3, 10, 15, 0),
        )


def test_transfer_rejects_zero_amount() -> None:
    with pytest.raises(ValidationError):
        Transfer(
            transfer_id="tx_001",
            from_account_id="acc_001",
            to_pix_key="maria@example.com",
            to_account_id="acc_external",
            to_holder_name_snapshot="MARIA",
            amount_centavos=0,
            status=TransferStatus.PENDING,
            idempotency_key="key-1",
            consent_id=None,
            created_at=datetime(2026, 3, 10, 14, 0),
        )


def test_transfer_rejects_naive_datetime() -> None:
    with pytest.raises(ValidationError):
        Transfer(
            transfer_id="tx_001",
            from_account_id="acc_001",
            to_pix_key="maria@example.com",
            to_account_id="acc_external",
            to_holder_name_snapshot="MARIA",
            amount_centavos=100,
            status=TransferStatus.PENDING,
            idempotency_key="key-1",
            consent_id=None,
            created_at=datetime(2026, 3, 10, 14, 0),
        )


def test_audit_event_rejects_naive_datetime() -> None:
    with pytest.raises(ValidationError):
        AuditEvent(
            seq=1,
            timestamp=datetime(2026, 3, 10, 14, 0),
            step_index=0,
            actor=ActorKind.SYSTEM,
            kind="RESET",
        )


def test_extra_field_rejected() -> None:
    aware = datetime(2026, 3, 10, 14, 0, tzinfo=UTC)
    with pytest.raises(ValidationError):
        Beneficiary(
            beneficiary_id="ben_001",
            customer_id="cus_001",
            nickname="Maria",
            pix_key="maria@example.com",
            created_at=aware,
            extra_field="nope",
        )


@pytest.mark.parametrize("rule", list(PolicyRuleId))
def test_policy_config_default_mode_is_hard(rule: PolicyRuleId) -> None:
    assert PolicyConfig().mode(rule) == EnforcementMode.HARD


def test_observation_rejects_result_and_error() -> None:
    with pytest.raises(ValidationError):
        Observation(
            step_index=1,
            sim_time=START,
            kind="tool_result",
            tool_name="get_account_balance",
            result={"balance_centavos": 100},
            error=ToolError(code=ToolErrorCode.NOT_FOUND, message="missing"),
            observed_at=START,
        )


def test_task_spec_rejects_oracle_steps_mismatch() -> None:
    data = minimal_task().model_dump()
    data["hidden"]["oracle_steps"] = 2
    with pytest.raises(ValidationError):
        TaskSpec.model_validate(data)


def test_task_spec_rejects_unknown_expected_transfer_key() -> None:
    data = minimal_task().model_dump()
    data["hidden"]["expected_transfers"] = [
        {"pix_key": "missing@example.com", "amount_centavos": 100}
    ]
    with pytest.raises(ValidationError):
        TaskSpec.model_validate(data)


def test_task_spec_rejects_principal_account_mismatch() -> None:
    data = minimal_task().model_dump()
    data["world"]["principal_account_id"] = "acc_external"
    with pytest.raises(ValidationError):
        TaskSpec.model_validate(data)


def test_task_spec_rejects_stale_read_without_age() -> None:
    data = minimal_task().model_dump()
    data["faults"] = [
        {
            "trigger": {"tool_name": "get_account_balance", "call_ordinal": 1},
            "kind": "STALE_READ",
        }
    ]
    with pytest.raises(ValidationError):
        TaskSpec.model_validate(data)


def test_task_spec_rejects_stale_age_on_non_stale_fault() -> None:
    data = minimal_task().model_dump()
    data["faults"] = [
        {
            "trigger": {"tool_name": "create_transfer", "call_ordinal": 1},
            "kind": "TIMEOUT_BEFORE_EXECUTE",
            "stale_age_steps": 1,
        }
    ]
    with pytest.raises(ValidationError):
        TaskSpec.model_validate(data)


def test_fault_injection_stale_age_rules() -> None:
    with pytest.raises(ValidationError):
        FaultInjection(
            trigger=FaultTrigger(tool_name="get_account_balance", call_ordinal=1),
            kind=FaultKind.STALE_READ,
        )
    with pytest.raises(ValidationError):
        FaultInjection(
            trigger=FaultTrigger(tool_name="create_transfer", call_ordinal=1),
            kind=FaultKind.TIMEOUT_BEFORE_EXECUTE,
            stale_age_steps=1,
        )


def test_episode_trace_json_round_trip() -> None:
    reset = sample_observation("reset")
    tool_obs = Observation(
        step_index=1,
        sim_time=START,
        kind="tool_result",
        tool_name="finish",
        result={"outcome": "DECLINED", "report": "done"},
        observed_at=START,
    )
    step = Step(
        step_index=1,
        action=Action(tool_name="finish", arguments={"outcome": "DECLINED", "report": "done"}),
        observation=tool_obs,
        transition=StateTransition(
            step_index=1,
            state_hash_before="a" * 64,
            state_hash_after="b" * 64,
            audit_seq_range=(1, 1),
            balances_after={"acc_ana": 1_000_000},
        ),
    )
    trace = EpisodeTrace(
        task_id="v0/test",
        seed=0,
        agent_name="oracle",
        reset_observation=reset,
        steps=[step],
        termination=TerminationReason.FINISHED,
        declared_outcome=EpisodeOutcome.DECLINED,
        final_report="done",
        final_state_hash="b" * 64,
        audit=[],
    )
    payload = trace.model_dump(mode="json")
    restored = EpisodeTrace.model_validate(payload)
    assert restored == trace


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


def test_contracts_star_import_exposes_named_types() -> None:
    import agentic_payments_env.contracts as contracts

    for name in (
        "WorldFixture",
        "WorldState",
        "Action",
        "Observation",
        "TaskSpec",
        "EpisodeTrace",
        "EpisodeResult",
        "BenchmarkReport",
    ):
        assert hasattr(contracts, name)
