"""Benchmark report summaries. REQ-GRD-10, REQ-GRD-11."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agentic_payments_env.benchmark.report import render_markdown, summarize
from agentic_payments_env.contracts.common import EpisodeOutcome, TaskFamily, TerminationReason
from agentic_payments_env.contracts.grading import (
    BenchmarkReport,
    Dimension,
    EpisodeResult,
    GraderResult,
    Severity,
    Violation,
)


def _dims(*, recovery: bool = True) -> dict[Dimension, GraderResult]:
    results: dict[Dimension, GraderResult] = {}
    for dimension in Dimension:
        if dimension == Dimension.RECOVERY and not recovery:
            results[dimension] = GraderResult(
                dimension=dimension, applicable=False, score=None, passed=True
            )
        else:
            results[dimension] = GraderResult(
                dimension=dimension, applicable=True, score=1.0, passed=True
            )
    return results


def _episode(
    *,
    task_id: str,
    family: TaskFamily,
    tags: list[str],
    safe: bool,
    cats: list[str],
    extra_codes: list[str] | None = None,
) -> EpisodeResult:
    violations = [
        Violation(
            code=code,
            severity=Severity.CATASTROPHIC,
            dimension=Dimension.SAFETY,
            message=code,
        )
        for code in cats
    ]
    for code in extra_codes or []:
        violations.append(
            Violation(
                code=code,
                severity=Severity.MAJOR,
                dimension=Dimension.TASK_SUCCESS,
                message=code,
            )
        )
    return EpisodeResult(
        task_id=task_id,
        family=family,
        tags=tags,
        seed=0,
        agent_name="scripted",
        termination=TerminationReason.FINISHED,
        declared_outcome=EpisodeOutcome.COMPLETED,
        expected_outcome=EpisodeOutcome.COMPLETED,
        steps_used=5,
        dimensions=_dims(recovery=family == TaskFamily.FAILURE_RECOVERY),
        violations=violations,
        catastrophic_codes=cats,
        task_success=safe,
        safe_success=safe,
    )


def test_summarize_rates_and_debatable_exclusion() -> None:
    episodes = [
        _episode(
            task_id="v0/rt-001",
            family=TaskFamily.ROUTINE_TRANSFER,
            tags=[],
            safe=True,
            cats=[],
        ),
        _episode(
            task_id="v0/rt-002",
            family=TaskFamily.ROUTINE_TRANSFER,
            tags=[],
            safe=True,
            cats=[],
            extra_codes=["TASK-02"],
        ),
        _episode(
            task_id="v0/adv-006",
            family=TaskFamily.ADVERSARIAL,
            tags=["debatable"],
            safe=False,
            cats=["SAF-01"],
        ),
    ]
    summaries = {item.family: item for item in summarize(episodes)}
    overall = summaries[None]
    assert overall.episodes == 2
    assert overall.safe_success_rate == 1.0
    assert overall.task_success_rate == 1.0
    assert overall.catastrophic_rate == 0.0
    assert overall.violation_counts == {"TASK-02": 1}
    assert overall.catastrophic_counts == {}
    adv = summaries[TaskFamily.ADVERSARIAL]
    assert adv.episodes == 1
    assert adv.safe_success_rate == 0.0
    assert adv.catastrophic_counts == {"SAF-01": 1}
    assert adv.catastrophic_rate == 1.0
    routine = summaries[TaskFamily.ROUTINE_TRANSFER]
    assert routine.mean_dimension_scores[Dimension.RECOVERY] is None
    rec = summaries[TaskFamily.FAILURE_RECOVERY]
    assert rec.episodes == 0
    assert rec.mean_dimension_scores[Dimension.TASK_SUCCESS] is None


def test_benchmark_report_rejects_unknown_schema_version() -> None:
    episodes = [
        _episode(
            task_id="v0/rt-001",
            family=TaskFamily.ROUTINE_TRANSFER,
            tags=[],
            safe=True,
            cats=[],
        )
    ]
    payload = BenchmarkReport(
        benchmark_id="v0",
        agent_name="oracle",
        seeds=[0],
        episodes=episodes,
        summaries=summarize(episodes),
    ).model_dump(mode="json")
    payload["schema_version"] = "2.0"
    with pytest.raises(ValidationError):
        BenchmarkReport.model_validate(payload)


def test_render_markdown_layout() -> None:
    episodes = [
        _episode(
            task_id="v0/rt-001",
            family=TaskFamily.ROUTINE_TRANSFER,
            tags=[],
            safe=True,
            cats=[],
        )
    ]
    report = BenchmarkReport(
        benchmark_id="v0",
        agent_name="oracle",
        seeds=[0, 1],
        episodes=episodes,
        summaries=summarize(episodes),
    )
    md = render_markdown(report)
    assert md.startswith("# Benchmark v0 — oracle — seeds [0,1]")
    assert "If a reader wants one number, it is `safe_success_rate`." in md
    assert "## Headline" in md
    assert "## Catastrophic failures by code" in md
    assert "## Dimension means" in md
    assert "## Per-task table" in md
    assert "v0/rt-001" in md
