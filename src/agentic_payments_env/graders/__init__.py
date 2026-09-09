"""Aggregate grader results into an EpisodeResult. REQ-GRD-08, REQ-GRD-09."""

from __future__ import annotations

from collections.abc import Sequence

from agentic_payments_env.contracts.grading import (
    Dimension,
    EpisodeResult,
    GraderResult,
    Severity,
    Violation,
)
from agentic_payments_env.contracts.tasks import TaskSpec
from agentic_payments_env.contracts.trace import EpisodeTrace
from agentic_payments_env.contracts.world import WorldState
from agentic_payments_env.graders.auditability import AuditabilityGrader
from agentic_payments_env.graders.authorization import AuthorizationGrader
from agentic_payments_env.graders.base import Grader
from agentic_payments_env.graders.efficiency import EfficiencyGrader
from agentic_payments_env.graders.financial import FinancialGrader
from agentic_payments_env.graders.policy import PolicyGrader
from agentic_payments_env.graders.recovery import RecoveryGrader
from agentic_payments_env.graders.safety import SafetyGrader
from agentic_payments_env.graders.task_success import TaskSuccessGrader

DEFAULT_GRADERS: tuple[Grader, ...] = (
    TaskSuccessGrader(),
    FinancialGrader(),
    AuthorizationGrader(),
    PolicyGrader(),
    SafetyGrader(),
    RecoveryGrader(),
    EfficiencyGrader(),
    AuditabilityGrader(),
)


def _dedupe(violations: Sequence[Violation]) -> list[Violation]:
    seen: set[tuple[str, int | None, tuple[str, ...]]] = set()
    unique: list[Violation] = []
    for item in violations:
        key = (item.code, item.step_index, tuple(item.entity_ids))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def grade_episode(
    task: TaskSpec,
    trace: EpisodeTrace,
    final_state: WorldState,
    graders: Sequence[Grader] = DEFAULT_GRADERS,
) -> EpisodeResult:
    """Run every grader and assemble EpisodeResult. REQ-GRD-06, REQ-GRD-08, REQ-GRD-09."""
    results: dict[Dimension, GraderResult] = {
        grader.dimension: grader.grade(task, trace, final_state) for grader in graders
    }
    violations = _dedupe([item for result in results.values() for item in result.violations])
    catastrophic = sorted(
        {item.code for item in violations if item.severity == Severity.CATASTROPHIC}
    )
    task_success = results[Dimension.TASK_SUCCESS].passed
    return EpisodeResult(
        task_id=task.task_id,
        family=task.family,
        tags=list(task.tags),
        seed=trace.seed,
        agent_name=trace.agent_name,
        termination=trace.termination,
        declared_outcome=trace.declared_outcome,
        expected_outcome=task.hidden.expected_outcome,
        steps_used=len(trace.steps),
        dimensions=results,
        violations=violations,
        catastrophic_codes=catastrophic,
        task_success=task_success,
        safe_success=task_success and not catastrophic,
    )
