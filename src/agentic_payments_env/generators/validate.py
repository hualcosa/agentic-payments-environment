"""Validity filter for generated tasks. M3 T3.06."""

from __future__ import annotations

from agentic_payments_env.agents.presets import build
from agentic_payments_env.benchmark.runner import _drive
from agentic_payments_env.contracts.grading import EpisodeResult
from agentic_payments_env.contracts.tasks import TaskSpec
from agentic_payments_env.graders import grade_episode

_ADVERSARIES = ("quitter", "liar", "naive_retry", "obedient", "splitter")


def is_valid(task: TaskSpec) -> bool:
    """Oracle must succeed with zero violations; one adversary must fail. T3.06."""
    oracle = _grade(task, "oracle")
    if not oracle.safe_success or oracle.violations:
        return False
    return any(not _safe_success(task, name) for name in _ADVERSARIES)


def _grade(task: TaskSpec, agent_name: str) -> EpisodeResult:
    env, trace = _drive(task, build(agent_name, task), 0)
    return grade_episode(task, trace, env.state)


def _safe_success(task: TaskSpec, agent_name: str) -> bool:
    return _grade(task, agent_name).safe_success
