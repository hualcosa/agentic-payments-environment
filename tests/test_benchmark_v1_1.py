"""v1.1 freeze tests. T7.11."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from agentic_payments_env.benchmark.loader import (
    all_tasks_for,
    export_tasks,
    load_task,
    load_task_file,
    task_to_json,
)
from agentic_payments_env.benchmark.runner import tasks_for_benchmark
from agentic_payments_env.benchmark.v1_1 import all_tasks
from agentic_payments_env.contracts.tasks import TaskSpec
from agentic_payments_env.environment import PaymentsEnvironment
from agentic_payments_env.generators.pool import (
    V11_HELD_OUT,
    V11_MIN_VALID,
    V11_SEED_MAX,
    content_hash,
    split_held_out,
    v11_difficulty_correlation,
    valid_pool,
)
from agentic_payments_env.generators.validate import is_valid

REPO = Path(__file__).resolve().parents[1]
HELD = REPO / "benchmarks" / "v1.1"
TRAIN = REPO / "benchmarks" / "v1.1-train"
REPORT = REPO / "reports" / "v1.1" / "difficulty.md"


def test_v11_valid_pool_has_at_least_one_thousand_candidates() -> None:
    valid = valid_pool(benchmark_prefix="v1.1", seed_max=V11_SEED_MAX)
    assert len(valid) >= V11_MIN_VALID


def test_v11_has_two_hundred_held_out() -> None:
    files = list(HELD.glob("*.json"))
    assert len(files) == V11_HELD_OUT
    tasks = all_tasks()
    assert len(tasks) == V11_HELD_OUT
    assert {path.stem for path in files} == {task.task_id.split("/", 1)[1] for task in tasks}


def test_v11_freeze_reconstructs_from_generator_config(tmp_path: Path) -> None:
    valid = valid_pool(benchmark_prefix="v1.1", seed_max=V11_SEED_MAX)
    _held, train = split_held_out(valid, V11_HELD_OUT)
    export_tasks("v1.1", tmp_path)
    committed = sorted(p.name for p in HELD.glob("*.json"))
    exported = sorted(p.name for p in tmp_path.glob("*.json"))
    assert exported == committed
    for name in committed:
        assert (tmp_path / name).read_bytes() == (HELD / name).read_bytes()
    assert len(train) == len(list(TRAIN.glob("*.json")))


def test_v11_held_out_and_train_disjoint() -> None:
    held_hashes = {content_hash(load_task_file(p)) for p in HELD.glob("*.json")}
    train_hashes = {content_hash(load_task_file(p)) for p in TRAIN.glob("*.json")}
    held_ids = {json.loads(p.read_text())["task_id"] for p in HELD.glob("*.json")}
    train_ids = {json.loads(p.read_text())["task_id"] for p in TRAIN.glob("*.json")}
    assert held_ids.isdisjoint(train_ids)
    assert held_hashes.isdisjoint(train_hashes)


def test_v11_difficulty_report_matches_recalculation() -> None:
    text = REPORT.read_text(encoding="utf-8")
    match = re.search(r"Spearman rho.*\*\*(-?\d+\.\d+)\*\*", text)
    assert match is not None
    reported = float(match.group(1))
    valid = valid_pool(benchmark_prefix="v1.1", seed_max=V11_SEED_MAX)
    rho, sample = v11_difficulty_correlation(valid)
    assert sample == len(valid)
    assert abs(rho - reported) < 1e-3


def test_v11_family_balance_present() -> None:
    text = REPORT.read_text(encoding="utf-8").lower()
    for family in ("routine_transfer", "policy_constrained", "failure_recovery", "adversarial"):
        assert family in text


@pytest.mark.parametrize("path", sorted(HELD.glob("*.json")), ids=lambda p: p.name)
def test_frozen_v11_json_validates_resets_and_exports(path: Path) -> None:
    raw = path.read_bytes()
    task = TaskSpec.model_validate(json.loads(raw.decode("utf-8")))
    env = PaymentsEnvironment(task)
    env.reset()
    assert task_to_json(task).encode("utf-8") == raw
    assert is_valid(task) is True


def test_load_task_v11() -> None:
    task = load_task(all_tasks()[0].task_id)
    assert task.task_id.startswith("v1.1/")


def test_v11_loader_and_runner_registry() -> None:
    loaded = all_tasks_for("v1.1")
    assert len(loaded) == V11_HELD_OUT
    assert tasks_for_benchmark("v1.1")[0].task_id == loaded[0].task_id
