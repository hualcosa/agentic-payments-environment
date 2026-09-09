"""Integer difficulty scores and a deterministic curriculum order. M3 T3.07. REQ-TASK-05."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from agentic_payments_env.agents.presets import build
from agentic_payments_env.benchmark.runner import _drive
from agentic_payments_env.contracts.common import TaskFamily
from agentic_payments_env.contracts.tasks import TaskSpec
from agentic_payments_env.graders import grade_episode

_SCRIPTED_PRESETS = ("quitter", "liar", "naive_retry", "obedient", "splitter")

_FAMILY_ORDER = (
    TaskFamily.ROUTINE_TRANSFER,
    TaskFamily.POLICY_CONSTRAINED,
    TaskFamily.FAILURE_RECOVERY,
    TaskFamily.ADVERSARIAL,
)


def difficulty_score(task: TaskSpec) -> int:
    """Non-negative int from amount/limit, faults, injection, language. T3.07. REQ-TASK-05."""
    limit = task.world.policy.per_transfer_limit_centavos or 500_000
    amount = _primary_amount(task)
    ratio_millis = (amount * 1000) // limit if limit > 0 else 0
    score = ratio_millis
    score += 100 * len(task.faults)
    score += 50 if task.hidden.injection_targets else 0
    score += 5 if _looks_portuguese(task.public.instruction) else 0
    return score


def curriculum_order(tasks: Sequence[TaskSpec]) -> list[TaskSpec]:
    """Sort by difficulty then task_id; round-robin families when several exist. REQ-TASK-05."""
    items = list(tasks)
    if not items:
        return []
    families_present = {task.family for task in items}
    if len(families_present) <= 1:
        return sorted(items, key=lambda task: (difficulty_score(task), task.task_id))
    buckets: dict[TaskFamily, list[TaskSpec]] = {family: [] for family in _FAMILY_ORDER}
    for task in items:
        buckets.setdefault(task.family, []).append(task)
    for family in buckets:
        buckets[family].sort(key=lambda task: (difficulty_score(task), task.task_id))
    order: list[TaskSpec] = []
    indices = dict.fromkeys(buckets, 0)
    sequence = [family for family in _FAMILY_ORDER if buckets.get(family)]
    while len(order) < len(items):
        progressed = False
        for family in sequence:
            idx = indices[family]
            bucket = buckets[family]
            if idx < len(bucket):
                order.append(bucket[idx])
                indices[family] = idx + 1
                progressed = True
        if not progressed:
            break
    return order


def _primary_amount(task: TaskSpec) -> int:
    expected = [item.amount_centavos for item in task.hidden.expected_transfers]
    if expected:
        return max(expected)
    for planned in task.hidden.oracle_plan:
        raw = planned.arguments.get("amount_centavos")
        if isinstance(raw, int) and raw > 0:
            return raw
    return 0


def _looks_portuguese(instruction: str) -> bool:
    lowered = instruction.lower()
    return lowered.startswith("envie ") or " pela minha conta" in lowered


def scripted_adversary_failure_rate(task: TaskSpec) -> float:
    """Fraction of five scripted presets that fail safe_success on ``task``. REQ-TASK-05."""
    failures = 0
    for preset in _SCRIPTED_PRESETS:
        env, trace = _drive(task, build(preset, task), 0)
        if not grade_episode(task, trace, env.state).safe_success:
            failures += 1
    return failures / len(_SCRIPTED_PRESETS)


def spearman_rank_correlation(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Spearman rho without external dependencies. REQ-TASK-05."""
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0
    n = len(xs)

    def _ranks(values: Sequence[float]) -> list[float]:
        order = sorted(range(n), key=lambda index: values[index])
        ranks = [0.0] * n
        index = 0
        while index < n:
            start = index
            value = values[order[index]]
            while index < n and values[order[index]] == value:
                index += 1
            avg_rank = (start + 1 + index) / 2.0
            for position in range(start, index):
                ranks[order[position]] = avg_rank
        return ranks

    rx = _ranks(xs)
    ry = _ranks(ys)
    mean_x = sum(rx) / n
    mean_y = sum(ry) / n
    numerator = sum((rx[i] - mean_x) * (ry[i] - mean_y) for i in range(n))
    denom_x = sum((value - mean_x) ** 2 for value in rx) ** 0.5
    denom_y = sum((value - mean_y) ** 2 for value in ry) ** 0.5
    if denom_x == 0.0 or denom_y == 0.0:
        return 0.0
    return float(numerator / (denom_x * denom_y))


def render_v11_difficulty_report(tasks: Sequence[TaskSpec]) -> str:
    """Markdown report for v1.1 difficulty vs scripted failure rate. REQ-TASK-05."""
    scores = [float(difficulty_score(task)) for task in tasks]
    rates = [scripted_adversary_failure_rate(task) for task in tasks]
    rho = spearman_rank_correlation(scores, rates)
    families = Counter(task.family.value for task in tasks)
    family_lines = "\n".join(
        f"| {family} | {count} |" for family, count in sorted(families.items())
    )
    interpretation = (
        "positive association: harder tasks tend to break more scripted presets"
        if rho > 0.1
        else "weak or flat association at this sample size"
    )
    return "\n".join(
        [
            "# Benchmark v1.1 difficulty vs scripted failure rate",
            "",
            f"Sample size: **{len(tasks)}** validated generated tasks "
            f"(before the 200-task held-out split).",
            "",
            "## Family distribution",
            "",
            "| family | count |",
            "|---|---|",
            family_lines,
            "",
            "## Scripted-adversary correlation",
            "",
            f"Spearman rho (`difficulty_score` vs mean failure rate across "
            f"{', '.join(_SCRIPTED_PRESETS)}): **{rho:.3f}**.",
            "",
            interpretation + ".",
            "",
            "## Live LLM baseline",
            "",
            "**not yet measured**. Do not infer model correlation from this table.",
            "",
        ]
    )
