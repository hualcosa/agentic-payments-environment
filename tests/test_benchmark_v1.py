"""v1 freeze tests. T3.08."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_payments_env.benchmark.loader import export_tasks, load_task, task_to_json
from agentic_payments_env.benchmark.v1 import all_tasks
from agentic_payments_env.contracts.tasks import TaskSpec
from agentic_payments_env.environment import PaymentsEnvironment
from agentic_payments_env.generators.validate import is_valid

REPO = Path(__file__).resolve().parents[1]
HELD = REPO / "benchmarks" / "v1"
TRAIN = REPO / "benchmarks" / "v1-train"


def test_v1_has_two_hundred_held_out() -> None:
    files = list(HELD.glob("*.json"))
    assert len(files) == 200
    tasks = all_tasks()
    assert len(tasks) == 200
    assert {path.stem for path in files} == {task.task_id.split("/", 1)[1] for task in tasks}


def test_load_task_v1() -> None:
    task = load_task(all_tasks()[0].task_id)
    assert task.task_id.startswith("v1/")


def test_v1_freeze_matches_export(tmp_path: Path) -> None:
    export_tasks("v1", tmp_path)
    committed = sorted(p.name for p in HELD.glob("*.json"))
    exported = sorted(p.name for p in tmp_path.glob("*.json"))
    assert exported == committed
    for name in committed:
        assert (tmp_path / name).read_bytes() == (HELD / name).read_bytes()


def test_v1_sample_passes_validity_filter() -> None:
    tasks = all_tasks()
    families = {task.family: task for task in tasks}
    assert len(families) >= 1
    for task in list(families.values())[:4]:
        assert is_valid(task) is True


def test_difficulty_report_exists() -> None:
    text = (REPO / "reports" / "v1" / "difficulty.md").read_text(encoding="utf-8").lower()
    assert "not yet measured" in text


def test_training_pool_nonempty() -> None:
    assert TRAIN.is_dir()
    assert list(TRAIN.glob("*.json"))


def _frozen_v1_json_paths() -> list[Path]:
    return sorted(list(HELD.glob("*.json")) + list(TRAIN.glob("*.json")))


@pytest.mark.parametrize("path", _frozen_v1_json_paths(), ids=lambda p: p.name)
def test_frozen_v1_json_validates_resets_and_exports(path: Path) -> None:
    raw = path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    task = TaskSpec.model_validate(payload)
    env = PaymentsEnvironment(task)
    env.reset()
    assert task_to_json(task).encode("utf-8") == raw
