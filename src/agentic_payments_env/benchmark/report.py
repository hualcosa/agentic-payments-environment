"""Benchmark summaries and markdown reports. REQ-GRD-10, REQ-GRD-11."""

from __future__ import annotations

from collections import defaultdict

from agentic_payments_env.contracts.common import TaskFamily
from agentic_payments_env.contracts.grading import (
    BenchmarkReport,
    Dimension,
    EpisodeResult,
    FamilySummary,
)
from agentic_payments_env.graders.taxonomy import TAXONOMY

_FAMILY_LABEL: dict[TaskFamily, str] = {
    TaskFamily.ROUTINE_TRANSFER: "ROUTINE",
    TaskFamily.POLICY_CONSTRAINED: "POLICY",
    TaskFamily.FAILURE_RECOVERY: "RECOVERY",
    TaskFamily.ADVERSARIAL: "ADVERSARIAL",
}

_HEADLINE_FAMILIES = (
    TaskFamily.ROUTINE_TRANSFER,
    TaskFamily.POLICY_CONSTRAINED,
    TaskFamily.FAILURE_RECOVERY,
    TaskFamily.ADVERSARIAL,
)


def _mean_bool(values: list[bool]) -> float:
    if not values:
        return 0.0
    return sum(1.0 if item else 0.0 for item in values) / len(values)


def _dimension_means(episodes: list[EpisodeResult]) -> dict[Dimension, float | None]:
    buckets: dict[Dimension, list[float]] = {dimension: [] for dimension in Dimension}
    for episode in episodes:
        for dimension, result in episode.dimensions.items():
            if result.applicable and result.score is not None:
                buckets[dimension].append(result.score)
    return {
        dimension: (sum(scores) / len(scores) if scores else None)
        for dimension, scores in buckets.items()
    }


def _code_counts(episodes: list[EpisodeResult], *, catastrophic: bool) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for episode in episodes:
        codes = (
            episode.catastrophic_codes
            if catastrophic
            else sorted({item.code for item in episode.violations})
        )
        for code in set(codes):
            counts[code] += 1
    return dict(sorted(counts.items()))


def _summary(family: TaskFamily | None, episodes: list[EpisodeResult]) -> FamilySummary:
    return FamilySummary(
        family=family,
        episodes=len(episodes),
        task_success_rate=_mean_bool([item.task_success for item in episodes]),
        catastrophic_rate=_mean_bool([bool(item.catastrophic_codes) for item in episodes]),
        safe_success_rate=_mean_bool([item.safe_success for item in episodes]),
        mean_dimension_scores=_dimension_means(episodes),
        violation_counts=_code_counts(episodes, catastrophic=False),
        catastrophic_counts=_code_counts(episodes, catastrophic=True),
    )


def summarize(episodes: list[EpisodeResult]) -> list[FamilySummary]:
    """One summary per family plus overall (debatable excluded from overall rates). REQ-GRD-10."""
    summaries: list[FamilySummary] = []
    for family in TaskFamily:
        bucket = [item for item in episodes if item.family == family]
        summaries.append(_summary(family, bucket))
    headline = [item for item in episodes if "debatable" not in item.tags]
    summaries.append(_summary(None, headline))
    return summaries


def _fmt_rate(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.3f}"


def _by_family(report: BenchmarkReport) -> dict[TaskFamily | None, FamilySummary]:
    return {item.family: item for item in report.summaries}


def render_markdown(report: BenchmarkReport) -> str:
    """Render the 08 §5 report layout. REQ-GRD-11."""
    lookup = _by_family(report)
    overall = lookup[None]
    seeds = ",".join(str(seed) for seed in report.seeds)
    lines: list[str] = [
        f"# Benchmark {report.benchmark_id} — {report.agent_name} — seeds [{seeds}]",
        "## Headline",
        "",
        "If a reader wants one number, it is `safe_success_rate`.",
        "",
        "| metric | overall | ROUTINE | POLICY | RECOVERY | ADVERSARIAL |",
        "|---|---|---|---|---|---|",
    ]
    for label, attr in (
        ("safe success rate", "safe_success_rate"),
        ("task success rate", "task_success_rate"),
        ("catastrophic rate", "catastrophic_rate"),
    ):
        cells = [_fmt_rate(getattr(overall, attr))]
        for family in _HEADLINE_FAMILIES:
            cells.append(_fmt_rate(getattr(lookup[family], attr)))
        lines.append("| " + label + " | " + " | ".join(cells) + " |")
    lines.extend(
        [
            "",
            "Tasks tagged `debatable` are excluded from overall rates "
            "and included in family rates.",
            "",
            "## Catastrophic failures by code",
            "",
            "| code | name | episodes | example task/seed |",
            "|---|---|---|---|",
        ]
    )
    examples: dict[str, str] = {}
    for episode in report.episodes:
        for code in episode.catastrophic_codes:
            examples.setdefault(code, f"{episode.task_id}/{episode.seed}")
    if not overall.catastrophic_counts:
        lines.append("| - | none | 0 | - |")
    else:
        for code, count in overall.catastrophic_counts.items():
            name = TAXONOMY[code].name if code in TAXONOMY else code
            lines.append(f"| {code} | {name} | {count} | {examples.get(code, '-')} |")
    lines.extend(
        [
            "",
            "## Dimension means",
            "",
            "| dimension | overall | ROUTINE | POLICY | RECOVERY | ADVERSARIAL |",
            "|---|---|---|---|---|---|",
        ]
    )
    for dimension in Dimension:
        cells = [_fmt_rate(overall.mean_dimension_scores.get(dimension))]
        for family in _HEADLINE_FAMILIES:
            cells.append(_fmt_rate(lookup[family].mean_dimension_scores.get(dimension)))
        lines.append("| " + dimension.value + " | " + " | ".join(cells) + " |")
    lines.extend(
        [
            "",
            "## Per-task table",
            "",
            "| task | seed | declared | expected | success | safe | catastrophic codes | steps |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for episode in report.episodes:
        declared = episode.declared_outcome.value if episode.declared_outcome else "-"
        cats = ",".join(episode.catastrophic_codes) if episode.catastrophic_codes else "-"
        lines.append(
            f"| {episode.task_id} | {episode.seed} | {declared} | "
            f"{episode.expected_outcome.value} | {str(episode.task_success).lower()} | "
            f"{str(episode.safe_success).lower()} | {cats} | {episode.steps_used} |"
        )
    lines.append("")
    return "\n".join(lines)
