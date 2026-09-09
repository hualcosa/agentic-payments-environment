"""Contract validation tests. REQ-CON-01..09."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
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
    validate_json_payload,
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
from tests.conftest import START

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
            ),
            Customer(
                customer_id="cus_external",
                display_name="External",
                document_masked="***",
                kyc_level=KycLevel.NONE,
            ),
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


def test_datetime_rejects_non_utc_offset() -> None:
    sao_paulo = timezone(timedelta(hours=-3))
    with pytest.raises(ValidationError):
        Beneficiary(
            beneficiary_id="ben_001",
            customer_id="cus_001",
            nickname="Maria",
            pix_key="maria@example.com",
            created_at=datetime(2026, 3, 10, 14, 0, tzinfo=sao_paulo),
        )


def test_balance_history_seed_rejects_non_utc_and_bad_centavos() -> None:
    base = minimal_world()
    sao_paulo = timezone(timedelta(hours=-3))
    payload = base.model_dump()
    payload["balance_history_seed"] = {
        "acc_ana": [(datetime(2026, 3, 10, 14, 0, tzinfo=sao_paulo), 100)]
    }
    with pytest.raises(ValidationError):
        WorldFixture.model_validate(payload)
    payload["balance_history_seed"] = {"acc_ana": [(START.isoformat(), 100.5)]}
    with pytest.raises(ValidationError):
        WorldFixture.model_validate(payload)


def test_audit_payload_accepts_nested_json() -> None:
    event = AuditEvent(
        seq=1,
        timestamp=START,
        step_index=0,
        actor=ActorKind.SYSTEM,
        kind="RESET",
        payload={"nested": {"items": [1, "x", None], "ok": True}},
    )
    assert event.payload["nested"]["items"] == [1, "x", None]


def test_audit_payload_rejects_set_value() -> None:
    with pytest.raises(ValueError):
        validate_json_payload({"items": {1, 2}})  # type: ignore[dict-item]


def test_audit_payload_rejects_non_finite_float() -> None:
    with pytest.raises(ValueError):
        validate_json_payload({"nan": float("nan")})


def test_audit_event_rejects_callable_payload() -> None:
    with pytest.raises(ValidationError):
        AuditEvent(
            seq=1,
            timestamp=START,
            step_index=0,
            actor=ActorKind.SYSTEM,
            kind="RESET",
            payload={"fn": lambda: None},  # type: ignore[dict-item]
        )


@pytest.mark.parametrize(
    "result",
    [
        None,
        {"outcome": 1, "report": "ok"},
        {"outcome": "COMPLETED", "report": 1},
        {"outcome": "COMPLETED"},
    ],
)
def test_final_observation_requires_string_outcome_and_report(result: object) -> None:
    with pytest.raises(ValidationError):
        Observation(
            step_index=1,
            sim_time=START,
            kind="final",
            result=result,  # type: ignore[arg-type]
            observed_at=START,
        )


def test_final_observation_accepts_valid_shape() -> None:
    obs = Observation(
        step_index=1,
        sim_time=START,
        kind="final",
        result={"outcome": "COMPLETED", "report": "done"},
        observed_at=START,
    )
    assert obs.result == {"outcome": "COMPLETED", "report": "done"}


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


def _fixture_transfer(**overrides: object) -> dict[str, object]:
    base = {
        "transfer_id": "tx_fix",
        "from_account_id": "acc_ana",
        "to_pix_key": "maria@example.com",
        "to_account_id": "acc_external",
        "to_holder_name_snapshot": "MARIA",
        "amount_centavos": 100,
        "status": "COMPLETED",
        "idempotency_key": "fix-1",
        "consent_id": None,
        "created_at": START.isoformat(),
        "completed_at": START.isoformat(),
        "initiated_by": "FIXTURE",
    }
    base.update(overrides)
    return base


def _mutated_task(mutator: object) -> dict[str, object]:
    data = minimal_task().model_dump(mode="json")
    mutator(data)  # type: ignore[operator]
    return data


_FIXTURE_RULE_CASES: tuple[tuple[str, object], ...] = (
    (
        "duplicate_customer",
        lambda data: data["world"]["customers"].append(data["world"]["customers"][0]),
    ),
    (
        "duplicate_account",
        lambda data: data["world"]["accounts"].append(data["world"]["accounts"][0]),
    ),
    (
        "duplicate_pix_key",
        lambda data: data["world"]["pix_directory"].append(data["world"]["pix_directory"][0]),
    ),
    (
        "duplicate_beneficiary",
        lambda data: data["world"]["beneficiaries"].extend(
            [
                {
                    "beneficiary_id": "ben_x",
                    "customer_id": "cus_ana",
                    "nickname": "X",
                    "pix_key": "maria@example.com",
                    "created_at": START.isoformat(),
                    "trusted": True,
                },
                {
                    "beneficiary_id": "ben_x",
                    "customer_id": "cus_ana",
                    "nickname": "Y",
                    "pix_key": "maria@example.com",
                    "created_at": START.isoformat(),
                    "trusted": True,
                },
            ]
        ),
    ),
    (
        "duplicate_transfer",
        lambda data: data["world"]["transfers"].extend([_fixture_transfer(), _fixture_transfer()]),
    ),
    (
        "missing_acc_external",
        lambda data: data["world"].__setitem__(
            "accounts",
            [item for item in data["world"]["accounts"] if item["account_id"] != "acc_external"],
        ),
    ),
    (
        "acc_external_wrong_owner",
        lambda data: next(
            item.__setitem__("customer_id", "cus_ana")
            for item in data["world"]["accounts"]
            if item["account_id"] == "acc_external"
        ),
    ),
    (
        "missing_cus_external",
        lambda data: data["world"].__setitem__(
            "customers",
            [item for item in data["world"]["customers"] if item["customer_id"] != "cus_external"],
        ),
    ),
    (
        "missing_principal_customer",
        lambda data: data["world"].__setitem__("principal_customer_id", "cus_missing"),
    ),
    (
        "directory_account_missing",
        lambda data: data["world"]["pix_directory"][0].__setitem__("account_id", "acc_missing"),
    ),
    (
        "beneficiary_unknown_customer",
        lambda data: data["world"]["beneficiaries"].append(
            {
                "beneficiary_id": "ben_bad",
                "customer_id": "cus_missing",
                "nickname": "Bad",
                "pix_key": "maria@example.com",
                "created_at": START.isoformat(),
                "trusted": True,
            }
        ),
    ),
    (
        "beneficiary_unknown_pix_key",
        lambda data: data["world"]["beneficiaries"].append(
            {
                "beneficiary_id": "ben_bad",
                "customer_id": "cus_ana",
                "nickname": "Bad",
                "pix_key": "missing@example.com",
                "created_at": START.isoformat(),
                "trusted": True,
            }
        ),
    ),
    (
        "fixture_transfer_not_completed",
        lambda data: data["world"]["transfers"].append(_fixture_transfer(status="PENDING")),
    ),
    (
        "fixture_transfer_not_fixture_initiator",
        lambda data: data["world"]["transfers"].append(_fixture_transfer(initiated_by="AGENT")),
    ),
    (
        "fixture_transfer_bad_from_account",
        lambda data: data["world"]["transfers"].append(
            _fixture_transfer(from_account_id="acc_missing")
        ),
    ),
    (
        "fixture_transfer_key_account_mismatch",
        lambda data: data["world"]["transfers"].append(_fixture_transfer(to_account_id="acc_ana")),
    ),
    (
        "fixture_transfer_missing_completed_at",
        lambda data: data["world"]["transfers"].append(
            {key: value for key, value in _fixture_transfer().items() if key != "completed_at"}
        ),
    ),
)


@pytest.mark.parametrize(("rule_name", "mutator"), _FIXTURE_RULE_CASES)
def test_task_spec_rejects_invalid_fixture(rule_name: str, mutator: object) -> None:
    del rule_name
    with pytest.raises(ValidationError):
        TaskSpec.model_validate(_mutated_task(mutator))


@pytest.mark.parametrize(("rule_name", "mutator"), _FIXTURE_RULE_CASES)
def test_load_task_file_rejects_invalid_fixture(
    rule_name: str, mutator: object, tmp_path: object
) -> None:
    from pathlib import Path

    del rule_name
    path = Path(str(tmp_path)) / "bad-fixture.json"
    path.write_text(__import__("json").dumps(_mutated_task(mutator)), encoding="utf-8")
    with pytest.raises(ValidationError):
        load_task_file(path)


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


def _valid_grader_result(**overrides: object) -> GraderResult:
    base = GraderResult(
        dimension=Dimension.FINANCIAL_CORRECTNESS,
        applicable=True,
        score=1.0,
        passed=True,
    )
    if overrides:
        return base.model_copy(update=overrides)
    return base


def test_grader_result_rejects_applicability_mismatch() -> None:
    with pytest.raises(ValidationError):
        GraderResult(
            dimension=Dimension.RECOVERY,
            applicable=False,
            score=1.0,
            passed=True,
        )
    with pytest.raises(ValidationError):
        GraderResult(
            dimension=Dimension.RECOVERY,
            applicable=True,
            score=None,
            passed=True,
        )


@pytest.mark.parametrize("bad_score", [float("nan"), float("inf"), -0.1, 1.1])
def test_grader_result_rejects_out_of_range_score(bad_score: float) -> None:
    payload = _valid_grader_result().model_dump(mode="json")
    payload["score"] = bad_score
    with pytest.raises(ValidationError):
        GraderResult.model_validate(payload)


def test_episode_result_rejects_hidden_catastrophic_codes() -> None:
    payload = _valid_result_payload()
    payload["catastrophic_codes"] = []
    payload["violations"] = [
        {
            "code": "SAF-01",
            "severity": "CATASTROPHIC",
            "dimension": "SAFETY",
            "message": "bad",
        }
    ]
    with pytest.raises(ValidationError):
        EpisodeResult.model_validate(payload)


def test_episode_result_requires_all_dimensions() -> None:
    payload = _valid_result_payload()
    payload["dimensions"] = {
        key.value: value
        for key, value in EpisodeResult.model_validate(payload).dimensions.items()
        if key != Dimension.AUDITABILITY
    }
    with pytest.raises(ValidationError):
        EpisodeResult.model_validate(payload)


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
