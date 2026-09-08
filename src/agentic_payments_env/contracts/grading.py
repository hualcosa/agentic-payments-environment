"""Grading result contracts.

Satisfies: REQ-CON-02, REQ-CON-03.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from agentic_payments_env.contracts.common import (
    SCHEMA_VERSION,
    EpisodeOutcome,
    FrozenModel,
    TaskFamily,
    TerminationReason,
)


class Dimension(str, Enum):  # noqa: UP042
    TASK_SUCCESS = "TASK_SUCCESS"
    FINANCIAL_CORRECTNESS = "FINANCIAL_CORRECTNESS"
    AUTHORIZATION = "AUTHORIZATION"
    POLICY_COMPLIANCE = "POLICY_COMPLIANCE"
    SAFETY = "SAFETY"
    RECOVERY = "RECOVERY"
    EFFICIENCY = "EFFICIENCY"
    AUDITABILITY = "AUDITABILITY"


class Severity(str, Enum):  # noqa: UP042
    CATASTROPHIC = "CATASTROPHIC"
    MAJOR = "MAJOR"
    MINOR = "MINOR"


class Violation(FrozenModel):
    code: str  # from 09-failure-taxonomy.md, e.g. "FIN-03"
    severity: Severity
    dimension: Dimension
    message: str
    step_index: int | None = None
    entity_ids: list[str] = []  # noqa: RUF012


class GraderResult(FrozenModel):
    dimension: Dimension
    applicable: bool = True  # False -> score is None and dimension is excluded from means
    score: float | None  # in [0, 1]
    passed: bool
    violations: list[Violation] = []  # noqa: RUF012
    details: dict[str, Any] = {}  # noqa: RUF012


class EpisodeResult(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    task_id: str
    family: TaskFamily
    tags: list[str] = []  # noqa: RUF012  # copied from TaskSpec; "debatable" affects report headline
    seed: int
    agent_name: str
    termination: TerminationReason
    declared_outcome: EpisodeOutcome | None
    expected_outcome: EpisodeOutcome
    steps_used: int
    dimensions: dict[Dimension, GraderResult]
    violations: list[Violation]  # union of all grader violations
    catastrophic_codes: list[str]  # sorted, de-duplicated
    task_success: bool
    safe_success: bool  # task_success and not catastrophic_codes


class FamilySummary(FrozenModel):
    family: TaskFamily | None  # None = overall
    episodes: int
    task_success_rate: float
    catastrophic_rate: float  # episodes with >= 1 catastrophic code
    safe_success_rate: float
    mean_dimension_scores: dict[Dimension, float | None]
    violation_counts: dict[str, int]  # code -> count of episodes containing it
    catastrophic_counts: dict[str, int]


class BenchmarkReport(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    benchmark_id: str  # "v0"
    agent_name: str
    seeds: list[int]
    episodes: list[EpisodeResult]
    summaries: list[FamilySummary]  # one per family plus overall
