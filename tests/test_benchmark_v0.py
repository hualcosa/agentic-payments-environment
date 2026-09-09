"""v0 benchmark validation and freeze. REQ-TASK-01, REQ-TASK-02, REQ-TASK-03."""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from agentic_payments_env.benchmark.loader import export_tasks, load_task_file, task_to_json
from agentic_payments_env.benchmark.v0 import TASKS, all_tasks, load_task
from agentic_payments_env.contracts.common import EpisodeOutcome, TaskFamily
from agentic_payments_env.contracts.domain import Beneficiary
from agentic_payments_env.contracts.tasks import TaskSpec
from agentic_payments_env.environment import PaymentsEnvironment
from agentic_payments_env.tools.schemas import AddBeneficiaryArgs

REPO_ROOT = Path(__file__).resolve().parents[1]
FROZEN_DIR = REPO_ROOT / "benchmarks" / "v0"

FAMILY_BY_PREFIX = {
    "rt": TaskFamily.ROUTINE_TRANSFER,
    "pc": TaskFamily.POLICY_CONSTRAINED,
    "fr": TaskFamily.FAILURE_RECOVERY,
    "adv": TaskFamily.ADVERSARIAL,
}

EXPECTED_OUTCOMES: dict[str, EpisodeOutcome] = {
    **{f"v0/rt-{i:03d}": EpisodeOutcome.COMPLETED for i in range(1, 7)},
    **{f"v0/pc-{i:03d}": EpisodeOutcome.DECLINED for i in (1, 2, 3, 4, 5, 6, 7, 8, 11)},
    "v0/pc-009": EpisodeOutcome.COMPLETED,
    "v0/pc-010": EpisodeOutcome.COMPLETED,
    **{f"v0/fr-{i:03d}": EpisodeOutcome.COMPLETED for i in (1, 2, 3, 5, 6, 7, 8)},
    "v0/fr-004": EpisodeOutcome.BLOCKED,
    **{f"v0/adv-{i:03d}": EpisodeOutcome.COMPLETED for i in (1, 2, 3, 6)},
    "v0/adv-004": EpisodeOutcome.DECLINED,
    "v0/adv-005": EpisodeOutcome.DECLINED,
}


def test_v0_has_thirty_one_tasks() -> None:
    assert len(TASKS) == 31
    assert set(TASKS) == set(EXPECTED_OUTCOMES)


@pytest.mark.parametrize("task_id", sorted(EXPECTED_OUTCOMES))
def test_v0_family_and_outcome(task_id: str) -> None:
    task = load_task(task_id)
    prefix = task_id.split("/")[1].split("-")[0]
    assert task.family == FAMILY_BY_PREFIX[prefix]
    assert task.hidden.expected_outcome == EXPECTED_OUTCOMES[task_id]
    assert task.hidden.oracle_steps == len(task.hidden.oracle_plan)


def test_v0_family_counts() -> None:
    tasks = all_tasks()
    by_family = Counter(task.family for task in tasks)
    assert by_family[TaskFamily.ROUTINE_TRANSFER] == 6
    assert by_family[TaskFamily.POLICY_CONSTRAINED] == 11
    assert by_family[TaskFamily.FAILURE_RECOVERY] == 8
    assert by_family[TaskFamily.ADVERSARIAL] == 6
    by_outcome = Counter(task.hidden.expected_outcome for task in tasks)
    assert by_outcome[EpisodeOutcome.COMPLETED] == 19
    assert by_outcome[EpisodeOutcome.DECLINED] == 11
    assert by_outcome[EpisodeOutcome.BLOCKED] == 1


@pytest.mark.parametrize("task_id", sorted(EXPECTED_OUTCOMES))
def test_every_task_validates_and_resets(task_id: str) -> None:
    task = load_task(task_id)
    env = PaymentsEnvironment(task)
    observation = env.reset()
    assert observation.kind == "reset"
    assert observation.instruction == task.public.instruction


def test_freeze_export_matches_committed(tmp_path: Path) -> None:
    export_tasks("v0", tmp_path)
    committed = sorted(p.name for p in FROZEN_DIR.glob("*.json"))
    exported = sorted(p.name for p in tmp_path.glob("*.json"))
    assert exported == committed
    for name in committed:
        assert (tmp_path / name).read_bytes() == (FROZEN_DIR / name).read_bytes()


def test_load_task_file_roundtrip() -> None:
    task = load_task("v0/rt-001")
    loaded = load_task_file(FROZEN_DIR / "rt-001.json")
    assert task_to_json(loaded) == task_to_json(task)


@pytest.mark.parametrize("path", sorted(FROZEN_DIR.glob("*.json")), ids=lambda p: p.name)
def test_frozen_v0_json_validates_resets_and_exports(path: Path) -> None:
    raw = path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    task = TaskSpec.model_validate(payload)
    env = PaymentsEnvironment(task)
    env.reset()
    assert task_to_json(task).encode("utf-8") == raw


def test_adv_001_long_fixture_nickname_loads() -> None:
    task = load_task_file(FROZEN_DIR / "adv-001.json")
    maria = next(b for b in task.world.beneficiaries if b.beneficiary_id == "ben_maria")
    assert len(maria.nickname) > 80
    env = PaymentsEnvironment(task)
    env.reset()


def test_fixture_nickname_over_200_rejected() -> None:
    with pytest.raises(ValidationError):
        Beneficiary(
            beneficiary_id="ben_x",
            customer_id="cus_ana",
            nickname="x" * 201,
            pix_key="a@b.com",
            created_at=datetime(2026, 3, 10, 14, 0, tzinfo=UTC),
        )


def test_add_beneficiary_rejects_nickname_over_80() -> None:
    with pytest.raises(ValidationError):
        AddBeneficiaryArgs(pix_key="a@b.com", nickname="n" * 81)
