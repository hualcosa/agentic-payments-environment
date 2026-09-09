"""Episode trace contracts.

Satisfies: REQ-CON-03, REQ-CON-04.
"""

from __future__ import annotations

from pydantic import field_validator

from agentic_payments_env.contracts.actions import Action, Observation
from agentic_payments_env.contracts.common import (
    SCHEMA_VERSION,
    Centavos,
    EpisodeOutcome,
    FrozenModel,
    TerminationReason,
    validate_schema_version,
)
from agentic_payments_env.contracts.domain import AuditEvent


class StateTransition(FrozenModel):
    step_index: int
    state_hash_before: str  # sha256 hex of canonical WorldState json
    state_hash_after: str
    audit_seq_range: tuple[int, int]  # inclusive (first, last); (0, 0) if none
    balances_after: dict[str, Centavos]
    new_transfer_ids: list[str] = []  # noqa: RUF012


class Step(FrozenModel):
    step_index: int  # 1-based
    action: Action
    observation: Observation
    transition: StateTransition


class EpisodeTrace(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    task_id: str
    seed: int
    agent_name: str
    reset_observation: Observation
    steps: list[Step]
    termination: TerminationReason
    declared_outcome: EpisodeOutcome | None
    final_report: str | None
    final_state_hash: str
    audit: list[AuditEvent]

    @field_validator("schema_version")
    @classmethod
    def _validate_schema_version(cls, value: str) -> str:
        return validate_schema_version(value)
