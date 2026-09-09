"""Load and freeze benchmark task JSON. REQ-TASK-02."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from agentic_payments_env.contracts.tasks import TaskSpec

BENCHMARK_IDS: tuple[str, ...] = ("v0", "v1", "v1.1")


def load_task_file(path: Path) -> TaskSpec:
    """Parse a frozen TaskSpec JSON file. REQ-TASK-02, REQ-CON-03."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return TaskSpec.model_validate(payload)


def task_to_json(task: TaskSpec) -> str:
    """Serialize a task with the freeze formatting. REQ-TASK-02."""
    return (
        json.dumps(task.model_dump(mode="json"), indent=2, sort_keys=True, ensure_ascii=False)
        + "\n"
    )


def load_task(task_id: str) -> TaskSpec:
    """Load v0 from the builder registry or v1 from frozen JSON. REQ-TASK-02."""
    if task_id.startswith("v0/"):
        from agentic_payments_env.benchmark.v0 import load_task as load_v0

        return load_v0(task_id)
    if task_id.startswith("v1/"):
        from agentic_payments_env.benchmark.v1 import load_task as load_v1

        return load_v1(task_id)
    if task_id.startswith("v1.1/"):
        from agentic_payments_env.benchmark.v1_1 import load_task as load_v11

        return load_v11(task_id)
    raise KeyError(f"unknown task_id {task_id!r}")


def _all_tasks_registry() -> dict[str, Callable[[], list[TaskSpec]]]:
    """Lazy registry of held-out task lists keyed by benchmark id."""
    from agentic_payments_env.benchmark.v0 import all_tasks as all_v0
    from agentic_payments_env.benchmark.v1 import all_tasks as all_v1
    from agentic_payments_env.benchmark.v1_1 import all_tasks as all_v11

    return {"v0": all_v0, "v1": all_v1, "v1.1": all_v11}


def all_tasks_for(benchmark_id: str) -> list[TaskSpec]:
    """Return every held-out task for ``benchmark_id``. REQ-TASK-02, REQ-ENV-17."""
    registry = _all_tasks_registry()
    if benchmark_id not in registry:
        msg = f"unknown benchmark_id {benchmark_id!r}"
        raise ValueError(msg)
    return registry[benchmark_id]()


def export_tasks(benchmark_id: str, out_dir: Path) -> None:
    """Write ``<suffix>.json`` for every task in ``benchmark_id``. REQ-TASK-02."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for task in all_tasks_for(benchmark_id):
        suffix = task.task_id.split("/", 1)[1]
        (out_dir / f"{suffix}.json").write_text(task_to_json(task), encoding="utf-8")
