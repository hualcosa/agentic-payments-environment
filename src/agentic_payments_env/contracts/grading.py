"""Grading result contracts. REQ-GRD-01."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field

from agentic_payments_env.contracts.common import (
    SCHEMA_VERSION,
    EpisodeOutcome,
    FrozenModel,
    TaskFamily,
    TerminationReason,
)


class Dimension(str, Enum):
    TASK_SUCCESS = "TASK_SUCCESS"
    FINANCIAL_CORRECTNESS = "FINANCIAL_CORRECTNESS"
    AUTHORIZATION = "AUTHORIZATION"
    POLICY_COMPLIANCE = "POLICY_COMPLIANCE"
    SAFETY = "SAFETY"
    RECOVERY = "RECOVERY"
    EFFICIENCY = "EFFICIENCY"
    AUDITABILITY = "AUDITABILITY"


class Severity(str, Enum):
    CATASTROPHIC = "CATASTROPHIC"
    MAJOR = "MAJOR"
    MINOR = "MINOR"


class Violation(FrozenModel):
    code: str
    severity: Severity
    dimension: Dimension
    message: str
    step_index: int | None = None
    entity_ids: list[str] = Field(default_factory=list)


class GraderResult(FrozenModel):
    dimension: Dimension
    applicable: bool = True
    score: float | None
    passed: bool
    violations: list[Violation] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class EpisodeResult(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    task_id: str
    family: TaskFamily
    tags: list[str] = Field(default_factory=list)
    seed: int
    agent_name: str
    termination: TerminationReason
    declared_outcome: EpisodeOutcome | None
    expected_outcome: EpisodeOutcome
    steps_used: int
    dimensions: dict[Dimension, GraderResult]
    violations: list[Violation] = Field(default_factory=list)
    catastrophic_codes: list[str] = Field(default_factory=list)
    task_success: bool
    safe_success: bool


class FamilySummary(FrozenModel):
    family: TaskFamily | None
    episodes: int
    task_success_rate: float
    catastrophic_rate: float
    safe_success_rate: float
    mean_dimension_scores: dict[Dimension, float | None]
    violation_counts: dict[str, int] = Field(default_factory=dict)
    catastrophic_counts: dict[str, int] = Field(default_factory=dict)


class BenchmarkReport(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    benchmark_id: str
    agent_name: str
    seeds: list[int]
    episodes: list[EpisodeResult]
    summaries: list[FamilySummary] = Field(default_factory=list)
