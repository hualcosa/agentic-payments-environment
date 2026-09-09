"""Contract validation tests (part 1: common and domain). REQ-CON-01..05."""

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
