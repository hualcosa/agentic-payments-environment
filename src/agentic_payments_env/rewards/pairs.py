"""Preference ranking and export from episode results. M4 T4.03. REQ-GRD-04."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from agentic_payments_env.agents.presets import NAMES, build
from agentic_payments_env.benchmark.loader import load_task, load_task_file
from agentic_payments_env.benchmark.runner import _drive
from agentic_payments_env.contracts.grading import EpisodeResult
from agentic_payments_env.contracts.training import PreferenceRecord
from agentic_payments_env.graders import grade_episode
from agentic_payments_env.rewards.episode import episode_reward

RankKey = tuple[bool, int, int]
ActionTrace = list[dict[str, object]]
AgentPair = tuple[str, str]

_SCRIPTED = ("quitter", "liar", "naive_retry", "obedient", "splitter")


def rank_key(result: EpisodeResult) -> RankKey:
    """Higher tuple is better: safe_success, fewer catastrophics, reward. REQ-GRD-04."""
    return (result.safe_success, -len(result.catastrophic_codes), episode_reward(result))


def prefer(result_a: EpisodeResult, result_b: EpisodeResult) -> Literal["A", "B", "TIE"]:
    """Compare two graded episodes. T4.03. REQ-GRD-04."""
    key_a = rank_key(result_a)
    key_b = rank_key(result_b)
    if key_a > key_b:
        return "A"
    if key_b > key_a:
        return "B"
    return "TIE"


def _grade(task_id: str, agent_name: str, seed: int = 0) -> EpisodeResult:
    result, _actions = _evaluate(task_id, agent_name, seed)
    return result


def _evaluate(task_id: str, agent_name: str, seed: int) -> tuple[EpisodeResult, ActionTrace]:
    task = load_task(task_id)
    env, trace = _drive(task, build(agent_name, task), seed)
    result = grade_episode(task, trace, env.state)
    actions: ActionTrace = [
        {
            "tool_name": step.action.tool_name,
            "arguments": dict(step.action.arguments),
        }
        for step in trace.steps
    ]
    return result, actions


def oracle_vs_scripted_pairs(
    task_ids: list[str], scripted_names: list[str]
) -> list[tuple[str, str]]:
    """Pairs ``(winner, loser)`` for oracle vs each scripted name, seed 0. REQ-GRD-04."""
    pairs: list[tuple[str, str]] = []
    for task_id in task_ids:
        oracle_result = _grade(task_id, "oracle")
        for name in scripted_names:
            other = _grade(task_id, name)
            choice = prefer(oracle_result, other)
            if choice == "A":
                pairs.append(("oracle", name))
            elif choice == "B":
                pairs.append((name, "oracle"))
    return pairs


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _held_out_task_ids() -> frozenset[str]:
    ids: set[str] = set()
    for folder in ("v1", "v1.1"):
        bench_dir = _repo_root() / "benchmarks" / folder
        if bench_dir.is_dir():
            for path in bench_dir.glob("*.json"):
                task = load_task_file(path)
                ids.add(task.task_id)
    return frozenset(ids)


def assert_training_task_id(task_id: str) -> None:
    """Reject v1/v1.1 held-out ids for training exports. REQ-GRD-04."""
    if task_id in _held_out_task_ids():
        msg = f"held-out task {task_id!r} cannot be exported for training"
        raise ValueError(msg)


def training_task_ids() -> list[str]:
    """v0 tasks plus v1.1-train; never held-out v1 or v1.1. REQ-GRD-04."""
    from agentic_payments_env.benchmark.v0 import all_tasks as all_v0

    ids = [task.task_id for task in all_v0()]
    train_dir = _repo_root() / "benchmarks" / "v1.1-train"
    for path in sorted(train_dir.glob("*.json")):
        task = load_task_file(path)
        assert_training_task_id(task.task_id)
        ids.append(task.task_id)
    return sorted(ids)


def build_preference_records(
    task_ids: list[str] | None = None,
    *,
    scripted_names: tuple[str, ...] = _SCRIPTED,
    agent_pairs: Sequence[AgentPair] | None = None,
    seed: int = 0,
) -> list[PreferenceRecord]:
    """Build action-pair rows; ties are omitted deterministically. T4.03. REQ-GRD-04."""
    tasks = training_task_ids() if task_ids is None else task_ids
    for task_id in tasks:
        assert_training_task_id(task_id)
    pairs = (
        tuple(agent_pairs)
        if agent_pairs is not None
        else tuple(("oracle", name) for name in scripted_names)
    )
    for agent_a, agent_b in pairs:
        if agent_a not in NAMES or agent_b not in NAMES:
            msg = f"unknown preference agent pair: {agent_a!r}, {agent_b!r}"
            raise ValueError(msg)
    records: list[PreferenceRecord] = []
    for task_id in tasks:
        evaluated: dict[str, tuple[EpisodeResult, ActionTrace]] = {}
        for agent_a, agent_b in pairs:
            for agent_name in (agent_a, agent_b):
                if agent_name not in evaluated:
                    evaluated[agent_name] = _evaluate(task_id, agent_name, seed)
            result_a, actions_a = evaluated[agent_a]
            result_b, actions_b = evaluated[agent_b]
            key_a = rank_key(result_a)
            key_b = rank_key(result_b)
            choice = prefer(result_a, result_b)
            if choice == "TIE":
                continue
            if choice == "A":
                chosen, rejected = agent_a, agent_b
                chosen_actions, rejected_actions = actions_a, actions_b
                chosen_key, rejected_key = key_a, key_b
            else:
                chosen, rejected = agent_b, agent_a
                chosen_actions, rejected_actions = actions_b, actions_a
                chosen_key, rejected_key = key_b, key_a
            records.append(
                PreferenceRecord(
                    task_id=task_id,
                    seed=seed,
                    chosen_agent=chosen,
                    rejected_agent=rejected,
                    chosen_actions=chosen_actions,
                    rejected_actions=rejected_actions,
                    rank_key_chosen=chosen_key,
                    rank_key_rejected=rejected_key,
                    provenance=(
                        "oracle_vs_scripted" if "oracle" in {agent_a, agent_b} else "agent_vs_agent"
                    ),
                )
            )
    return records


def dumps_preferences(records: list[PreferenceRecord]) -> str:
    """Canonical JSONL text for preference records. REQ-GRD-04."""
    lines = [
        json.dumps(record.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
        for record in records
    ]
    return "\n".join(lines) + ("\n" if lines else "")


def export_preferences(out_path: Path, task_ids: list[str] | None = None) -> None:
    """Write preference JSONL for training tasks only. T4.03. REQ-GRD-04."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    records = build_preference_records(task_ids)
    out_path.write_text(dumps_preferences(records), encoding="utf-8")
