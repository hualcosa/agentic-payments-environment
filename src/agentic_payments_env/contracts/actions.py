"""Agent actions and environment observations. REQ-CON-08."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from agentic_payments_env.contracts.common import (
    FrozenModel,
    PolicyRuleId,
    aware_datetime_validator,
)


class Action(FrozenModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    rationale: str | None = None


class ToolErrorCode(str, Enum):
    UNKNOWN_TOOL = "UNKNOWN_TOOL"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    NOT_FOUND = "NOT_FOUND"
    ACCOUNT_BLOCKED = "ACCOUNT_BLOCKED"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    CONSENT_REQUIRED = "CONSENT_REQUIRED"
    CONSENT_INVALID = "CONSENT_INVALID"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    REVERSAL_NOT_ALLOWED = "REVERSAL_NOT_ALLOWED"
    TIMEOUT = "TIMEOUT"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    EPISODE_FINISHED = "EPISODE_FINISHED"


class PolicyWarning(FrozenModel):
    rule: PolicyRuleId
    message: str


class ToolError(FrozenModel):
    code: ToolErrorCode
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class Observation(FrozenModel):
    model_config = ConfigDict(frozen=True, extra="forbid", revalidate_instances="always")

    step_index: int
    sim_time: datetime
    kind: Literal["reset", "tool_result", "tool_error", "final"]
    tool_name: str | None = None
    result: dict[str, Any] | None = None
    error: ToolError | None = None
    warnings: list[PolicyWarning] = Field(default_factory=list)
    observed_at: datetime
    instruction: str | None = None
    principal: dict[str, Any] | None = None
    available_tools: list[str] | None = None

    @field_validator("sim_time", "observed_at", mode="after")
    @classmethod
    def _validate_datetimes(cls, value: datetime) -> datetime:
        return aware_datetime_validator(value)

    @model_validator(mode="after")
    def _validate_result_error(self) -> Observation:
        if self.kind == "tool_result" and (self.result is None or self.error is not None):
            msg = "tool_result requires result and forbids error"
            raise ValueError(msg)
        if self.kind == "tool_error" and (self.error is None or self.result is not None):
            msg = "tool_error requires error and forbids result"
            raise ValueError(msg)
        if self.kind == "final":
            if self.result is None or self.error is not None:
                msg = "final requires result and forbids error"
                raise ValueError(msg)
            outcome = self.result.get("outcome")
            report = self.result.get("report")
            if not isinstance(outcome, str) or not isinstance(report, str):
                msg = "final result requires string outcome and report"
                raise ValueError(msg)
        return self
