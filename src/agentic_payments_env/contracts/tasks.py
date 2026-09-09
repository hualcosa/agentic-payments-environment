"""Task specification contracts. REQ-CON-09."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import ConfigDict, Field, model_validator

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
    amount_centavos: Centavos | None = None


class ConsentResponse(str, Enum):
    GRANT = "GRANT"
    DENY = "DENY"
    NO_RESPONSE = "NO_RESPONSE"


class StepUpResponse(str, Enum):
    APPROVE = "APPROVE"
    DENY = "DENY"
    NO_RESPONSE = "NO_RESPONSE"


class UserVigilance(str, Enum):
    ALWAYS_FOLLOW_SCRIPT = "ALWAYS_FOLLOW_SCRIPT"
    DENY_IF_SCOPE_MISMATCH = "DENY_IF_SCOPE_MISMATCH"


class UserScript(FrozenModel):
    consent_responses: list[ConsentResponse] = Field(
        default_factory=lambda: [ConsentResponse.GRANT]
    )
    step_up_responses: list[StepUpResponse] = Field(
        default_factory=lambda: [StepUpResponse.APPROVE]
    )
    clarification_responses: list[UntrustedStr] = Field(
        default_factory=lambda: ["Please proceed exactly as I asked."]
    )
    vigilance: UserVigilance = UserVigilance.ALWAYS_FOLLOW_SCRIPT


class FaultTrigger(FrozenModel):
    tool_name: str
    call_ordinal: int = Field(ge=1)


class FaultInjection(FrozenModel):
    model_config = ConfigDict(frozen=True, extra="forbid", revalidate_instances="always")

    trigger: FaultTrigger
    kind: FaultKind
    stale_age_steps: int | None = None

    @model_validator(mode="after")
    def _validate_stale_age(self) -> FaultInjection:
        if self.kind == FaultKind.STALE_READ:
            if self.stale_age_steps is None:
                msg = "STALE_READ faults require stale_age_steps"
                raise ValueError(msg)
        elif self.stale_age_steps is not None:
            msg = "stale_age_steps allowed only for STALE_READ faults"
            raise ValueError(msg)
        return self


class TaskPublic(FrozenModel):
    instruction: str
    max_steps: int = Field(default=30, ge=1)


class OracleStep(FrozenModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class TaskHidden(FrozenModel):
    expected_outcome: EpisodeOutcome
    expected_transfers: list[ExpectedTransfer] = Field(default_factory=list)
    forbidden_pix_keys: list[str] = Field(default_factory=list)
    injection_targets: list[InjectionTarget] = Field(default_factory=list)
    recoverable: bool = True
    requires_clarification: bool = False
    oracle_plan: list[OracleStep]
    oracle_steps: int
    notes: str = ""


class TaskSpec(FrozenModel):
    model_config = ConfigDict(frozen=True, extra="forbid", revalidate_instances="always")

    schema_version: str = SCHEMA_VERSION
    task_id: str
    family: TaskFamily
    title: str
    tags: list[str] = Field(default_factory=list)
    world: WorldFixture
    public: TaskPublic
    user: UserScript = UserScript()
    faults: list[FaultInjection] = Field(default_factory=list)
    hidden: TaskHidden

    @model_validator(mode="after")
    def _validate_task_spec(self) -> TaskSpec:
        if self.hidden.oracle_steps != len(self.hidden.oracle_plan):
            msg = "hidden.oracle_steps must equal len(hidden.oracle_plan)"
            raise ValueError(msg)

        directory_keys = {record.pix_key for record in self.world.pix_directory}
        for expected in self.hidden.expected_transfers:
            if expected.pix_key not in directory_keys:
                msg = f"expected transfer pix_key not in directory: {expected.pix_key}"
                raise ValueError(msg)

        principal_account = next(
            (
                account
                for account in self.world.accounts
                if account.account_id == self.world.principal_account_id
            ),
            None,
        )
        if principal_account is None:
            msg = "world.principal_account_id not found in accounts"
            raise ValueError(msg)
        if principal_account.customer_id != self.world.principal_customer_id:
            msg = "world.principal_account_id does not belong to principal_customer_id"
            raise ValueError(msg)

        for fault in self.faults:
            if fault.kind == FaultKind.STALE_READ and fault.stale_age_steps is None:
                msg = "STALE_READ faults require stale_age_steps"
                raise ValueError(msg)
            if fault.kind != FaultKind.STALE_READ and fault.stale_age_steps is not None:
                msg = "stale_age_steps allowed only for STALE_READ faults"
                raise ValueError(msg)

        return self
