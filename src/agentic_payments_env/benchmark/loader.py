"""Load and freeze benchmark task JSON. REQ-TASK-02."""

from __future__ import annotations

import json
from pathlib import Path

from agentic_payments_env.contracts.tasks import TaskSpec


def load_task_file(path: Path) -> TaskSpec:
    """Parse a frozen TaskSpec JSON file. REQ-TASK-02."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return TaskSpec.model_validate(payload)


def task_to_json(task: TaskSpec) -> str:
    """Serialize a task with the freeze formatting. REQ-TASK-02."""
    return (
        json.dumps(task.model_dump(mode="json"), indent=2, sort_keys=True, ensure_ascii=False)
        + "\n"
    )


def export_tasks(benchmark_id: str, out_dir: Path) -> None:
    """Write ``<suffix>.json`` for every task in ``benchmark_id``. REQ-TASK-02."""
    if benchmark_id != "v0":
        raise ValueError(f"unknown benchmark_id {benchmark_id!r}")
    from agentic_payments_env.benchmark.v0 import all_tasks

    out_dir.mkdir(parents=True, exist_ok=True)
    for task in all_tasks():
        suffix = task.task_id.split("/", 1)[1]
        (out_dir / f"{suffix}.json").write_text(task_to_json(task), encoding="utf-8")
