"""Contract tests (part 1): enums, datetime awareness, money constraints."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

import pytest
from pydantic import ValidationError

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
    AuditEvent,
    Beneficiary,
    Consent,
    ConsentScope,
    PolicyConfig,
    Transfer,
)

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
