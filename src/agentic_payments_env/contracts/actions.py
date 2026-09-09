"""Action and observation contracts.

Satisfies: REQ-CON-02, REQ-CON-05, REQ-CON-08.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import model_validator

from agentic_payments_env.contracts.common import (
    FrozenModel,
    PolicyRuleId,
    aware_datetime_validator,
)


class Action(FrozenModel):
    tool_name: str
    arguments: dict[str, Any] = {}  # noqa: RUF012
    rationale: str | None = None  # free text from the agent; recorded, never graded in v0


class ToolErrorCode(str, Enum):  # noqa: UP042
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
    details: dict[str, Any] = {}  # noqa: RUF012  # e.g. {"violations": [...]} for POLICY_VIOLATION


class Observation(FrozenModel):
    step_index: int  # 0 for the reset observation
    sim_time: datetime
    kind: Literal["reset", "tool_result", "tool_error", "final"]
    tool_name: str | None = None
    result: dict[str, Any] | None = None  # tool-specific payload (04 §3)
    error: ToolError | None = None
    warnings: list[PolicyWarning] = []  # noqa: RUF012  # SOFT-mode findings attached to a success
    observed_at: datetime  # == sim_time unless a STALE_READ fault applied
    instruction: str | None = None  # only on kind == "reset"
    principal: dict[str, Any] | None = (
        None  # only on reset: customer_id, account_id(s), display_name
    )
    available_tools: list[str] | None = None  # only on reset

    _aware = aware_datetime_validator("sim_time", "observed_at")

    @model_validator(mode="after")
    def _req_con_08(self) -> Observation:
        """Exactly one of result/error when kind is tool_result/tool_error. REQ-CON-08."""
        if self.result is not None and self.error is not None:
            raise ValueError("Observation cannot set both result and error")
        if self.kind == "tool_result" and self.result is None:
            raise ValueError("tool_result observations must set result")
        if self.kind == "tool_error" and self.error is None:
            raise ValueError("tool_error observations must set error")
        if self.kind == "tool_result" and self.error is not None:
            raise ValueError("tool_result observations must not set error")
        if self.kind == "tool_error" and self.result is not None:
            raise ValueError("tool_error observations must not set result")
        return self
