"""Shared types, enums, and model bases for contracts.

Satisfies: REQ-CON-01, REQ-CON-02, REQ-CON-04, REQ-CON-05.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

# Spec requires `class X(str, Enum)` with values equal to member names (REQ-CON-02).
# ruff: noqa: UP042

Centavos = int  # integer minor units of BRL; never float
UntrustedStr = str  # may contain adversarial content; see 02 §8

SCHEMA_VERSION = "0.1"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class MutableModel(BaseModel):
    model_config = ConfigDict(frozen=False, extra="forbid", validate_assignment=True)


def _require_aware(dt: datetime) -> datetime:
    """Reject naive datetimes. REQ-CON-05."""
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError("datetime must be timezone-aware")
    return dt


def aware_datetime_validator(*fields: str) -> Any:
    """Pydantic validator factory that applies `_require_aware` to datetime fields. REQ-CON-05."""

    def _validate(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _require_aware(value)

    return field_validator(*fields, mode="after")(_validate)


class KycLevel(str, Enum):
    NONE = "NONE"
    BASIC = "BASIC"
    FULL = "FULL"


class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"


class AuthLevel(str, Enum):
    BASIC = "BASIC"
    STEP_UP = "STEP_UP"


class PixKeyType(str, Enum):
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    CPF = "CPF"
    RANDOM = "RANDOM"


class TransferStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVERSED = "REVERSED"


class ConsentStatus(str, Enum):
    PENDING = "PENDING"
    GRANTED = "GRANTED"
    DENIED = "DENIED"
    EXPIRED = "EXPIRED"
    USED = "USED"


class ChallengeStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"


class ActorKind(str, Enum):
    AGENT = "AGENT"
    SYSTEM = "SYSTEM"
    USER = "USER"


class Initiator(str, Enum):
    AGENT = "AGENT"
    FIXTURE = "FIXTURE"


class EnforcementMode(str, Enum):
    HARD = "HARD"
    SOFT = "SOFT"
    SILENT = "SILENT"


class PolicyRuleId(str, Enum):
    PER_TRANSFER_LIMIT = "PER_TRANSFER_LIMIT"
    DAILY_LIMIT = "DAILY_LIMIT"
    NIGHT_LIMIT = "NIGHT_LIMIT"
    KYC_AMOUNT_CAP = "KYC_AMOUNT_CAP"
    BLOCKED_RECIPIENT = "BLOCKED_RECIPIENT"
    NEW_BENEFICIARY_COOLING = "NEW_BENEFICIARY_COOLING"
    STEP_UP_REQUIRED = "STEP_UP_REQUIRED"
    CONSENT_REQUIRED = "CONSENT_REQUIRED"


class EpisodeOutcome(str, Enum):
    COMPLETED = "COMPLETED"  # agent claims the task was completed
    DECLINED = "DECLINED"  # agent refused: unsafe, unauthorized, or against policy
    BLOCKED = "BLOCKED"  # agent could not complete due to failures it could not recover from


class TerminationReason(str, Enum):
    FINISHED = "FINISHED"
    MAX_STEPS = "MAX_STEPS"
    AGENT_ERROR = "AGENT_ERROR"


class TaskFamily(str, Enum):
    ROUTINE_TRANSFER = "ROUTINE_TRANSFER"
    POLICY_CONSTRAINED = "POLICY_CONSTRAINED"
    FAILURE_RECOVERY = "FAILURE_RECOVERY"
    ADVERSARIAL = "ADVERSARIAL"


class FaultKind(str, Enum):
    TIMEOUT_BEFORE_EXECUTE = "TIMEOUT_BEFORE_EXECUTE"  # error returned, no side effect
    TIMEOUT_AFTER_EXECUTE = "TIMEOUT_AFTER_EXECUTE"  # side effect happened, error returned
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"  # error returned, no side effect
    STALE_READ = "STALE_READ"  # read tools only: returns an older snapshot
