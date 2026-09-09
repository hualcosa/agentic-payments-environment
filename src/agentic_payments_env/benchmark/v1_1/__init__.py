"""v1.1 held-out task registry loaded from frozen JSON. REQ-TASK-02."""

from __future__ import annotations

from pathlib import Path

from agentic_payments_env.benchmark.loader import load_task_file
from agentic_payments_env.contracts.tasks import TaskSpec


def _frozen_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "benchmarks" / "v1.1"


def load_task(task_id: str) -> TaskSpec:
    """Load a frozen v1.1 TaskSpec. REQ-TASK-02."""
    if not task_id.startswith("v1.1/"):
        raise KeyError(f"unknown task_id {task_id!r}")
    suffix = task_id.split("/", 1)[1]
    path = _frozen_dir() / f"{suffix}.json"
    if not path.is_file():
        raise KeyError(f"unknown task_id {task_id!r}")
    return load_task_file(path)


def all_tasks() -> list[TaskSpec]:
    """Every frozen v1.1 held-out task, sorted by task_id."""
    tasks = [load_task_file(path) for path in sorted(_frozen_dir().glob("*.json"))]
    return sorted(tasks, key=lambda task: task.task_id)
