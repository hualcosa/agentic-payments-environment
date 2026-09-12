"""Frozen training export contracts. M4/M5. REQ-GRD-12."""

from __future__ import annotations

from pydantic import Field

from agentic_payments_env.contracts.common import FrozenModel


class PreferenceRecord(FrozenModel):
    """One chosen/rejected episode pair with rank provenance. T4.03. REQ-GRD-12."""

    schema_version: str = "0.1"
    task_id: str
    seed: int = 0
    chosen_agent: str
    rejected_agent: str
    chosen_actions: list[dict[str, object]]
    rejected_actions: list[dict[str, object]]
    rank_key_chosen: tuple[bool, int, int]
    rank_key_rejected: tuple[bool, int, int]
    provenance: str = Field(min_length=1)


class SFTRecord(FrozenModel):
    """One action trace suitable for supervised fine-tuning. T5.02. REQ-GRD-12."""

    schema_version: str = "0.1"
    task_id: str
    seed: int = 0
    agent: str
    safe_success: bool
    actions: list[dict[str, object]]
