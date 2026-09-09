"""Build and split the generated v1 task pool. M3 T3.08."""

from __future__ import annotations

from pathlib import Path

from agentic_payments_env.benchmark.loader import task_to_json
from agentic_payments_env.contracts.common import TaskFamily
from agentic_payments_env.contracts.tasks import TaskSpec
from agentic_payments_env.core.hashing import sha256_hex
from agentic_payments_env.generators.adversarial import generate_adversarial
from agentic_payments_env.generators.base import GenParams, SeededRng
from agentic_payments_env.generators.policy import generate_policy
from agentic_payments_env.generators.recovery import generate_recovery
from agentic_payments_env.generators.routine import generate_routine
from agentic_payments_env.generators.validate import is_valid

HELD_OUT = 200
SEED_MAX = 60


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def candidate_tasks() -> list[TaskSpec]:
    """Four families for seeds 1..SEED_MAX (deterministic ids)."""
    tasks: list[TaskSpec] = []
    for seed in range(1, SEED_MAX + 1):
        rng = SeededRng(seed)
        numer = 1 + (seed % 7)
        denom = max(10 + (seed % 9), 6 * numer)
        portuguese = seed % 3 == 0
        suffix = f"{seed:03d}"
        tasks.append(
            generate_routine(
                rng,
                GenParams(
                    family=TaskFamily.ROUTINE_TRANSFER,
                    amount_limit_ratio_numer=numer,
                    amount_limit_ratio_denom=denom,
                    n_recipients=1,
                    portuguese=portuguese,
                ),
                f"v1/rt-{suffix}",
            )
        )
        tasks.append(
            generate_policy(
                rng,
                GenParams(
                    family=TaskFamily.POLICY_CONSTRAINED,
                    amount_limit_ratio_numer=numer,
                    amount_limit_ratio_denom=denom,
                    n_recipients=1,
                    portuguese=portuguese,
                ),
                f"v1/pc-{suffix}",
            )
        )
        tasks.append(
            generate_recovery(
                rng,
                GenParams(
                    family=TaskFamily.FAILURE_RECOVERY,
                    amount_limit_ratio_numer=numer,
                    amount_limit_ratio_denom=denom,
                    n_recipients=1,
                    portuguese=portuguese,
                ),
                f"v1/fr-{suffix}",
            )
        )
        tasks.append(
            generate_adversarial(
                rng,
                GenParams(
                    family=TaskFamily.ADVERSARIAL,
                    amount_limit_ratio_numer=numer,
                    amount_limit_ratio_denom=denom,
                    n_recipients=1,
                    portuguese=portuguese,
                ),
                f"v1/adv-{suffix}",
            )
        )
    return tasks


def valid_pool() -> list[TaskSpec]:
    """Drop tasks that fail the T3.06 filter; do not mutate them."""
    return [task for task in candidate_tasks() if is_valid(task)]


def split_held_out(
    tasks: list[TaskSpec], n_held: int = HELD_OUT
) -> tuple[list[TaskSpec], list[TaskSpec]]:
    ranked = sorted(tasks, key=lambda task: (sha256_hex(task.task_id), task.task_id))
    return ranked[:n_held], ranked[n_held:]


def write_v1_freeze() -> tuple[int, int]:
    """Write held-out JSON under benchmarks/v1 and the rest under v1-train."""
    valid = valid_pool()
    held, train = split_held_out(valid)
    held_dir = repo_root() / "benchmarks" / "v1"
    train_dir = repo_root() / "benchmarks" / "v1-train"
    held_dir.mkdir(parents=True, exist_ok=True)
    train_dir.mkdir(parents=True, exist_ok=True)
    for path in held_dir.glob("*.json"):
        path.unlink()
    for path in train_dir.glob("*.json"):
        path.unlink()
    for task in held:
        suffix = task.task_id.split("/", 1)[1]
        (held_dir / f"{suffix}.json").write_text(task_to_json(task), encoding="utf-8")
    for task in train:
        suffix = task.task_id.split("/", 1)[1]
        (train_dir / f"{suffix}.json").write_text(task_to_json(task), encoding="utf-8")
    return len(held), len(train)
