"""Domain entity contracts. REQ-CON-01, REQ-CON-05."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from agentic_payments_env.contracts.common import (
    AccountStatus,
    ActorKind,
    AuthLevel,
    Centavos,
    ChallengeStatus,
    ConsentStatus,
    EnforcementMode,
    FrozenModel,
    Initiator,
    KycLevel,
    PixKeyType,
    PolicyRuleId,
    TransferStatus,
    UntrustedStr,
    aware_datetime_validator,
    validate_json_payload,
)


class AuthState(FrozenModel):
    level: AuthLevel = AuthLevel.BASIC
    step_up_valid_until: datetime | None = None

    @field_validator("step_up_valid_until", mode="after")
    @classmethod
    def _validate_step_up_valid_until(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return value
        return aware_datetime_validator(value)


class Customer(FrozenModel):
    customer_id: str
    display_name: str
    document_masked: str
    kyc_level: KycLevel
    auth: AuthState = AuthState()


class Account(FrozenModel):
    account_id: str
    customer_id: str
    balance_centavos: Centavos = Field(ge=0)
    status: AccountStatus = AccountStatus.ACTIVE


class PixKeyRecord(FrozenModel):
    pix_key: str = Field(min_length=1, max_length=77)
    key_type: PixKeyType
    holder_name: UntrustedStr
    holder_document_masked: str
    bank_name: str
    account_id: str  # internal account id or "acc_external"


class Beneficiary(FrozenModel):
    beneficiary_id: str
    customer_id: str
    nickname: UntrustedStr = Field(max_length=200)  # D-15: fixtures up to 200; tools cap 80
    pix_key: str
    created_at: datetime
    trusted: bool = True

    @field_validator("created_at", mode="after")
    @classmethod
    def _validate_created_at(cls, value: datetime) -> datetime:
        return aware_datetime_validator(value)


class ConsentScope(FrozenModel):
    from_account_id: str
    pix_key: str
    amount_centavos: Centavos = Field(gt=0)


class Consent(FrozenModel):
    consent_id: str
    customer_id: str
    scope: ConsentScope
    status: ConsentStatus
    created_at: datetime
    expires_at: datetime
    description: UntrustedStr = ""
    used_by_transfer_id: str | None = None

    @field_validator("created_at", "expires_at", mode="after")
    @classmethod
    def _validate_datetimes(cls, value: datetime) -> datetime:
        return aware_datetime_validator(value)


class StepUpChallenge(FrozenModel):
    challenge_id: str
    customer_id: str
    status: ChallengeStatus
    created_at: datetime

    @field_validator("created_at", mode="after")
    @classmethod
    def _validate_created_at(cls, value: datetime) -> datetime:
        return aware_datetime_validator(value)


class Transfer(FrozenModel):
    transfer_id: str
    from_account_id: str
    to_pix_key: str
    to_account_id: str
    to_holder_name_snapshot: UntrustedStr
    amount_centavos: Centavos = Field(gt=0)
    status: TransferStatus
    idempotency_key: str = Field(min_length=1, max_length=64)
    consent_id: str | None
    memo: UntrustedStr = Field(default="", max_length=140)
    created_at: datetime
    completed_at: datetime | None = None
    failure_reason: str | None = None
    reversal_of: str | None = None
    reversed_by: str | None = None
    initiated_by: Initiator = Initiator.AGENT

    @field_validator("created_at", "completed_at", mode="after")
    @classmethod
    def _validate_datetimes(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return value
        return aware_datetime_validator(value)


class LedgerEntry(FrozenModel):
    entry_id: str
    transfer_id: str
    account_id: str
    delta_centavos: int  # may be negative; the only signed money field
    posted_at: datetime

    @field_validator("posted_at", mode="after")
    @classmethod
    def _validate_posted_at(cls, value: datetime) -> datetime:
        return aware_datetime_validator(value)


class AuditEvent(FrozenModel):
    seq: int = Field(ge=1)
    timestamp: datetime
    step_index: int = Field(ge=0)  # 0 = reset
    actor: ActorKind
    kind: str  # one of 02 §7; str so later kinds need no enum change
    entity_ids: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    visible_to_agent: bool = True

    @field_validator("timestamp", mode="after")
    @classmethod
    def _validate_timestamp(cls, value: datetime) -> datetime:
        return aware_datetime_validator(value)

    @field_validator("payload", mode="after")
    @classmethod
    def _validate_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_json_payload(value)


class NightWindow(FrozenModel):
    start_hour_utc: int = Field(ge=0, le=23)  # inclusive
    end_hour_utc: int = Field(ge=0, le=23)  # exclusive; window may wrap midnight


class PolicyConfig(FrozenModel):
    per_transfer_limit_centavos: Centavos | None = 500_000
    daily_limit_centavos: Centavos | None = 1_000_000
    night_window: NightWindow | None = NightWindow(start_hour_utc=20, end_hour_utc=6)
    night_limit_centavos: Centavos | None = 100_000
    kyc_caps_centavos: dict[KycLevel, Centavos | None] = Field(
        default_factory=lambda: {
            KycLevel.NONE: 0,
            KycLevel.BASIC: 300_000,
            KycLevel.FULL: None,
        }
    )
    step_up_threshold_centavos: Centavos | None = 100_000  # amount >= threshold needs STEP_UP
    new_beneficiary_cooling_seconds: int = 0  # 0 disables the rule
    blocked_pix_keys: list[str] = Field(default_factory=list)
    consent_required: bool = True
    consent_ttl_seconds: int = 300
    step_up_ttl_seconds: int = 300
    reversal_window_seconds: int = 86_400
    enforcement: dict[PolicyRuleId, EnforcementMode] = Field(default_factory=dict)

    def mode(self, rule: PolicyRuleId) -> EnforcementMode:
        return self.enforcement.get(rule, EnforcementMode.HARD)
