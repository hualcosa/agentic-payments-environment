"""Integer difficulty scores and a deterministic curriculum order. M3 T3.07."""

from __future__ import annotations

from collections.abc import Sequence

from agentic_payments_env.contracts.common import TaskFamily
from agentic_payments_env.contracts.tasks import TaskSpec

_FAMILY_ORDER = (
    TaskFamily.ROUTINE_TRANSFER,
    TaskFamily.POLICY_CONSTRAINED,
    TaskFamily.FAILURE_RECOVERY,
    TaskFamily.ADVERSARIAL,
)


def difficulty_score(task: TaskSpec) -> int:
    """Non-negative int from amount/limit, faults, injection, language. T3.07."""
    limit = task.world.policy.per_transfer_limit_centavos or 500_000
    amount = _primary_amount(task)
    ratio_millis = (amount * 1000) // limit if limit > 0 else 0
    score = ratio_millis
    score += 100 * len(task.faults)
    score += 50 if task.hidden.injection_targets else 0
    score += 5 if _looks_portuguese(task.public.instruction) else 0
    return score


def curriculum_order(tasks: Sequence[TaskSpec]) -> list[TaskSpec]:
    """Sort by difficulty then task_id; round-robin families when several exist."""
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
