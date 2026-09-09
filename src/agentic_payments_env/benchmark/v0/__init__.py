"""v0 task registry. REQ-TASK-01, REQ-TASK-03."""

from __future__ import annotations

from collections.abc import Callable

from agentic_payments_env.benchmark.v0.tasks_adversarial import (
    adv_001,
    adv_002,
    adv_003,
    adv_004,
    adv_005,
    adv_006,
)
from agentic_payments_env.benchmark.v0.tasks_policy import (
    pc_001,
    pc_002,
    pc_003,
    pc_004,
    pc_005,
    pc_006,
    pc_007,
    pc_008,
    pc_009,
    pc_010,
    pc_011,
)
from agentic_payments_env.benchmark.v0.tasks_recovery import (
    fr_001,
    fr_002,
    fr_003,
    fr_004,
    fr_005,
    fr_006,
    fr_007,
    fr_008,
)
from agentic_payments_env.benchmark.v0.tasks_routine import (
    rt_001,
    rt_002,
    rt_003,
    rt_004,
    rt_005,
    rt_006,
)
from agentic_payments_env.contracts.tasks import TaskSpec

TASKS: dict[str, Callable[[], TaskSpec]] = {
    "v0/rt-001": rt_001,
    "v0/rt-002": rt_002,
    "v0/rt-003": rt_003,
    "v0/rt-004": rt_004,
    "v0/rt-005": rt_005,
    "v0/rt-006": rt_006,
    "v0/pc-001": pc_001,
    "v0/pc-002": pc_002,
    "v0/pc-003": pc_003,
    "v0/pc-004": pc_004,
    "v0/pc-005": pc_005,
    "v0/pc-006": pc_006,
    "v0/pc-007": pc_007,
    "v0/pc-008": pc_008,
    "v0/pc-009": pc_009,
    "v0/pc-010": pc_010,
    "v0/pc-011": pc_011,
    "v0/fr-001": fr_001,
    "v0/fr-002": fr_002,
    "v0/fr-003": fr_003,
    "v0/fr-004": fr_004,
    "v0/fr-005": fr_005,
    "v0/fr-006": fr_006,
    "v0/fr-007": fr_007,
    "v0/fr-008": fr_008,
    "v0/adv-001": adv_001,
    "v0/adv-002": adv_002,
    "v0/adv-003": adv_003,
    "v0/adv-004": adv_004,
    "v0/adv-005": adv_005,
    "v0/adv-006": adv_006,
}


def load_task(task_id: str) -> TaskSpec:
    """Build the TaskSpec for ``task_id``. REQ-TASK-01."""
    try:
        builder = TASKS[task_id]
    except KeyError as exc:
        raise KeyError(f"unknown task_id {task_id!r}") from exc
    return builder()


def all_tasks() -> list[TaskSpec]:
    """Build every registered v0 task in id order. REQ-TASK-01."""
    return [TASKS[task_id]() for task_id in sorted(TASKS)]
