"""Shared contract primitives and enums. REQ-CON-01, REQ-CON-02, REQ-CON-05."""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict

UntrustedStr = str  # may contain adversarial content; see 02 §8


def validate_centavos(value: object) -> int:
    """Reject bool/str/float/Decimal coercion at money boundaries. REQ-DOM-01/03."""
    if isinstance(value, bool):
        msg = "centavos must be int, not bool"
        raise ValueError(msg)
    if isinstance(value, float):
        msg = "centavos must be int, not float"
        raise ValueError(msg)
    if isinstance(value, str):
        msg = "centavos must be int, not str"
        raise ValueError(msg)
    if isinstance(value, Decimal):
        msg = "centavos must be int, not Decimal"
        raise ValueError(msg)
    if not isinstance(value, int):
        msg = f"centavos must be int, not {type(value).__name__}"
        raise ValueError(msg)
    return value


Centavos = Annotated[int, BeforeValidator(validate_centavos)]

SCHEMA_VERSION = "0.1"

_SUPPORTED_SCHEMA_MAJOR = 0


def validate_schema_version(value: str) -> str:
    """Validate major.minor syntax and accept only v0 major. REQ-CON-03."""
    parts = value.split(".")
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        msg = f"schema_version must be major.minor with integer parts, got {value!r}"
        raise ValueError(msg)
    if int(parts[0]) != _SUPPORTED_SCHEMA_MAJOR:
        msg = f"unsupported schema_version major {parts[0]!r}"
        raise ValueError(msg)
    return value


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class MutableModel(BaseModel):
    model_config = ConfigDict(frozen=False, extra="forbid", validate_assignment=True)


def _require_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        msg = "datetime must be timezone-aware"
        raise ValueError(msg)
    if dt.utcoffset() != timedelta(0):
        msg = "datetime must be UTC with zero offset"
        raise ValueError(msg)
    return dt


def aware_datetime_validator(value: datetime) -> datetime:
    """Reject naive or non-UTC datetimes for contract fields. REQ-CON-05, D-17."""
    return _require_utc(value)


def validate_json_value(value: object) -> object:
    """Recursively validate JSON-serializable audit payload values. REQ-CON-04."""
    if value is None:
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            msg = "non-finite float in JSON payload"
            raise ValueError(msg)
        return value
    if isinstance(value, list):
        return [validate_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): validate_json_value(item) for key, item in value.items()}
    msg = f"non-JSON value in payload: {type(value).__name__}"
    raise ValueError(msg)


def validate_json_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate an audit payload dict at construction time. REQ-CON-04."""
    validated = validate_json_value(payload)
    if not isinstance(validated, dict):
        msg = "audit payload must be a JSON object"
        raise ValueError(msg)
    return validated


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
