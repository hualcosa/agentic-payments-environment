"""Preference ranking from episode results. M4 T4.03."""

from __future__ import annotations

from typing import Literal

from agentic_payments_env.agents.presets import build
from agentic_payments_env.benchmark.loader import load_task
from agentic_payments_env.benchmark.runner import _drive
from agentic_payments_env.contracts.grading import EpisodeResult
from agentic_payments_env.graders import grade_episode
from agentic_payments_env.rewards.episode import episode_reward

RankKey = tuple[bool, int, int]


def rank_key(result: EpisodeResult) -> RankKey:
    """Higher tuple is better: safe_success, fewer catastrophics, reward."""
    return (result.safe_success, -len(result.catastrophic_codes), episode_reward(result))


def prefer(result_a: EpisodeResult, result_b: EpisodeResult) -> Literal["A", "B", "TIE"]:
    """Compare two graded episodes. T4.03."""
    key_a = rank_key(result_a)
    key_b = rank_key(result_b)
    if key_a > key_b:
        return "A"
    if key_b > key_a:
        return "B"
    return "TIE"


def _grade(task_id: str, agent_name: str) -> EpisodeResult:
    task = load_task(task_id)
    env, trace = _drive(task, build(agent_name, task), 0)
    return grade_episode(task, trace, env.state)


def oracle_vs_scripted_pairs(
    task_ids: list[str], scripted_names: list[str]
) -> list[tuple[str, str]]:
    """Pairs ``(winner, loser)`` for oracle vs each scripted name, seed 0."""
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
