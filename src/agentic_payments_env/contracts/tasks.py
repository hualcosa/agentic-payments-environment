"""Task specification contracts.

Satisfies: REQ-CON-03, REQ-CON-09.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, model_validator

from agentic_payments_env.contracts.common import (
    SCHEMA_VERSION,
    Centavos,
    EpisodeOutcome,
    FaultKind,
    FrozenModel,
    TaskFamily,
    UntrustedStr,
)
from agentic_payments_env.contracts.world import WorldFixture


class ExpectedTransfer(FrozenModel):
    pix_key: str
    amount_centavos: Centavos = Field(gt=0)


class InjectionTarget(FrozenModel):
    pix_key: str
    amount_centavos: Centavos | None = None  # None = any amount to this key counts


class ConsentResponse(str, Enum):  # noqa: UP042
    GRANT = "GRANT"
    DENY = "DENY"
    NO_RESPONSE = "NO_RESPONSE"


class StepUpResponse(str, Enum):  # noqa: UP042
    APPROVE = "APPROVE"
    DENY = "DENY"
    NO_RESPONSE = "NO_RESPONSE"


class UserVigilance(str, Enum):  # noqa: UP042
    ALWAYS_FOLLOW_SCRIPT = "ALWAYS_FOLLOW_SCRIPT"
    DENY_IF_SCOPE_MISMATCH = "DENY_IF_SCOPE_MISMATCH"  # deny consent whose scope is not expected


class UserScript(FrozenModel):
    consent_responses: list[ConsentResponse] = [ConsentResponse.GRANT]  # noqa: RUF012
    step_up_responses: list[StepUpResponse] = [StepUpResponse.APPROVE]  # noqa: RUF012
    clarification_responses: list[UntrustedStr] = ["Please proceed exactly as I asked."]  # noqa: RUF012
    vigilance: UserVigilance = UserVigilance.ALWAYS_FOLLOW_SCRIPT


class FaultTrigger(FrozenModel):
    tool_name: str
    call_ordinal: int = Field(ge=1)  # fires on the N-th call of this tool in the episode


class FaultInjection(FrozenModel):
    trigger: FaultTrigger
    kind: FaultKind
    stale_age_steps: int | None = None  # required iff kind == STALE_READ

    @model_validator(mode="after")
    def _stale_age_iff_stale_read(self) -> FaultInjection:
        if self.kind == FaultKind.STALE_READ:
            if self.stale_age_steps is None:
                raise ValueError("stale_age_steps is required iff kind is STALE_READ")
        elif self.stale_age_steps is not None:
            raise ValueError("stale_age_steps is required iff kind is STALE_READ")
        return self


class TaskPublic(FrozenModel):
    instruction: str
    max_steps: int = Field(default=30, ge=1)


class OracleStep(FrozenModel):
    tool_name: str
    arguments: dict[str, Any] = {}  # noqa: RUF012  # may contain "$variables", see 07 §6


class TaskHidden(FrozenModel):
    expected_outcome: EpisodeOutcome
    expected_transfers: list[ExpectedTransfer] = []  # noqa: RUF012
    forbidden_pix_keys: list[str] = []  # noqa: RUF012
    injection_targets: list[InjectionTarget] = []  # noqa: RUF012
    recoverable: bool = True  # if faults exist: can the task still be completed?
    requires_clarification: bool = False
    oracle_plan: list[OracleStep]
    oracle_steps: int  # == len(oracle_plan); used by efficiency grader
    notes: str = ""


class TaskSpec(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    task_id: str  # e.g. "v0/rt-001"
    family: TaskFamily
    title: str
    tags: list[str] = []  # noqa: RUF012
    world: WorldFixture
    public: TaskPublic
    user: UserScript = UserScript()
    faults: list[FaultInjection] = []  # noqa: RUF012
    hidden: TaskHidden

    @model_validator(mode="after")
    def _req_con_09(self) -> TaskSpec:
        """Validate oracle length, PIX keys, principal ownership, and stale faults. REQ-CON-09."""
        if self.hidden.oracle_steps != len(self.hidden.oracle_plan):
            raise ValueError("hidden.oracle_steps must equal len(hidden.oracle_plan)")
        directory_keys = {record.pix_key for record in self.world.pix_directory}
        for expected in self.hidden.expected_transfers:
            if expected.pix_key not in directory_keys:
                raise ValueError(
                    f"expected transfer pix_key {expected.pix_key!r} is not in world.pix_directory"
                )
        accounts = {account.account_id: account for account in self.world.accounts}
        principal_account = accounts.get(self.world.principal_account_id)
        if (
            principal_account is None
            or principal_account.customer_id != self.world.principal_customer_id
        ):
            raise ValueError(
                "world.principal_account_id must belong to world.principal_customer_id"
            )
        for fault in self.faults:
            is_stale = fault.kind == FaultKind.STALE_READ
            has_age = fault.stale_age_steps is not None
            if is_stale != has_age:
                raise ValueError("stale_age_steps must be set iff fault kind is STALE_READ")
        return self
