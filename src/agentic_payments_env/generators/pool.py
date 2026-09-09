"""Build and split generated benchmark pools. M3 T3.08."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from agentic_payments_env.benchmark.loader import task_to_json
from agentic_payments_env.contracts.common import FaultKind, TaskFamily
from agentic_payments_env.contracts.tasks import TaskSpec
from agentic_payments_env.core.hashing import sha256_hex
from agentic_payments_env.generators.adversarial import generate_adversarial
from agentic_payments_env.generators.base import GenParams, InjectionPlacement, SeededRng
from agentic_payments_env.generators.difficulty import (
    difficulty_score,
    render_v11_difficulty_report,
    scripted_adversary_failure_rate,
    spearman_rank_correlation,
)
from agentic_payments_env.generators.policy import generate_policy
from agentic_payments_env.generators.recovery import generate_recovery
from agentic_payments_env.generators.routine import generate_routine
from agentic_payments_env.generators.validate import is_valid

HELD_OUT = 200
SEED_MAX = 60

V11_MIN_VALID = 1000
V11_HELD_OUT = 200
V11_SEED_MAX = 254


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _params_for_seed(seed: int, family: TaskFamily) -> GenParams:
    """Map a seed to generator knobs; v1.1 uses richer variation."""
    numer = 1 + (seed % 7)
    denom = max(10 + (seed % 9), 6 * numer)
    portuguese = seed % 3 == 0
    n_recipients = 2 if family == TaskFamily.ROUTINE_TRANSFER and seed % 17 == 0 else 1
    name_collision = family == TaskFamily.ROUTINE_TRANSFER and seed % 23 == 0
    fault_kinds = (
        FaultKind.TIMEOUT_BEFORE_EXECUTE,
        FaultKind.SERVICE_UNAVAILABLE,
        FaultKind.TIMEOUT_AFTER_EXECUTE,
    )
    fault_kind = (
        fault_kinds[seed % len(fault_kinds)] if family == TaskFamily.FAILURE_RECOVERY else None
    )
    injection_placement = (
        InjectionPlacement.HOLDER_NAME if seed % 2 == 0 else InjectionPlacement.NICKNAME
    )
    user_consent_deny = family == TaskFamily.POLICY_CONSTRAINED and seed % 13 == 0
    return GenParams(
        family=family,
        amount_limit_ratio_numer=numer,
        amount_limit_ratio_denom=denom,
        n_recipients=n_recipients,
        name_collision=name_collision,
        portuguese=portuguese,
        fault_kind=fault_kind,
        fault_ordinal=1,
        injection_placement=injection_placement,
        user_consent_deny=user_consent_deny,
    )


def _generate_family_task(
    rng: SeededRng, params: GenParams, task_id: str, family: TaskFamily
) -> TaskSpec:
    if family == TaskFamily.ROUTINE_TRANSFER:
        return generate_routine(rng, params, task_id)
    if family == TaskFamily.POLICY_CONSTRAINED:
        return generate_policy(rng, params, task_id)
    if family == TaskFamily.FAILURE_RECOVERY:
        return generate_recovery(rng, params, task_id)
    return generate_adversarial(rng, params, task_id)


def candidate_tasks(*, benchmark_prefix: str = "v1", seed_max: int = SEED_MAX) -> list[TaskSpec]:
    """Four families per seed with deterministic ids."""
    families = (
        (TaskFamily.ROUTINE_TRANSFER, "rt"),
        (TaskFamily.POLICY_CONSTRAINED, "pc"),
        (TaskFamily.FAILURE_RECOVERY, "fr"),
        (TaskFamily.ADVERSARIAL, "adv"),
    )
    tasks: list[TaskSpec] = []
    width = 3 if benchmark_prefix == "v1" else 4
    for seed in range(1, seed_max + 1):
        rng = SeededRng(seed)
        suffix = f"{seed:0{width}d}"
        for family, prefix in families:
            params = _params_for_seed(seed, family)
            if benchmark_prefix == "v1":
                params = params.model_copy(
                    update={
                        "n_recipients": 1,
                        "name_collision": False,
                        "fault_kind": None,
                        "user_consent_deny": False,
                        "injection_placement": InjectionPlacement.NICKNAME,
                    }
                )
            task_id = f"{benchmark_prefix}/{prefix}-{suffix}"
            tasks.append(_generate_family_task(rng, params, task_id, family))
    return tasks


def valid_pool(*, benchmark_prefix: str = "v1", seed_max: int = SEED_MAX) -> list[TaskSpec]:
    """Drop tasks that fail the T3.06 filter; do not mutate them."""
    return [
        task
        for task in candidate_tasks(benchmark_prefix=benchmark_prefix, seed_max=seed_max)
        if is_valid(task)
    ]


def split_held_out(
    tasks: list[TaskSpec], n_held: int = HELD_OUT
) -> tuple[list[TaskSpec], list[TaskSpec]]:
    ranked = sorted(tasks, key=lambda task: (sha256_hex(task.task_id), task.task_id))
    return ranked[:n_held], ranked[n_held:]


def content_hash(task: TaskSpec) -> str:
    """Stable hash of frozen JSON bytes for disjointness checks."""
    return sha256_hex(task_to_json(task))


def write_v1_freeze() -> tuple[int, int]:
    """Write held-out JSON under benchmarks/v1 and the rest under v1-train."""
    valid = valid_pool(benchmark_prefix="v1", seed_max=SEED_MAX)
    held, train = split_held_out(valid, HELD_OUT)
    held_dir = repo_root() / "benchmarks" / "v1"
    train_dir = repo_root() / "benchmarks" / "v1-train"
    return _write_split(held, train, held_dir, train_dir)


def write_v1_1_freeze() -> tuple[int, int]:
    """Write v1.1 held-out (200) and training pools from validated candidates."""
    valid = valid_pool(benchmark_prefix="v1.1", seed_max=V11_SEED_MAX)
    if len(valid) < V11_MIN_VALID:
        msg = f"v1.1 valid pool {len(valid)} < {V11_MIN_VALID}"
        raise RuntimeError(msg)
    held, train = split_held_out(valid, V11_HELD_OUT)
    held_dir = repo_root() / "benchmarks" / "v1.1"
    train_dir = repo_root() / "benchmarks" / "v1.1-train"
    counts = _write_split(held, train, held_dir, train_dir)
    report_path = repo_root() / "reports" / "v1.1" / "difficulty.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_v11_difficulty_report(valid), encoding="utf-8")
    return counts


def _write_split(
    held: list[TaskSpec], train: list[TaskSpec], held_dir: Path, train_dir: Path
) -> tuple[int, int]:
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


def v11_difficulty_correlation(tasks: list[TaskSpec]) -> tuple[float, int]:
    """Spearman rho between difficulty_score and scripted failure rate."""
    scores = [float(difficulty_score(task)) for task in tasks]
    rates = [scripted_adversary_failure_rate(task) for task in tasks]
    return spearman_rank_correlation(scores, rates), len(tasks)


def v11_family_distribution(tasks: list[TaskSpec]) -> Counter[str]:
    return Counter(task.family.value for task in tasks)
