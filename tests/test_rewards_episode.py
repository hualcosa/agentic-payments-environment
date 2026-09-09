"""Tests for episode millipoint rewards. T4.01."""

from __future__ import annotations

from agentic_payments_env.agents.presets import build
from agentic_payments_env.benchmark.runner import _drive
from agentic_payments_env.benchmark.v0 import load_task
from agentic_payments_env.graders import grade_episode
from agentic_payments_env.rewards.episode import WEIGHTS, episode_reward
from tests.conftest import run_oracle


def test_weights_sum_to_1000() -> None:
    assert sum(WEIGHTS.values()) == 1000


def test_oracle_rt001_positive_reward() -> None:
    task = load_task("v0/rt-001")
    trace, state = run_oracle(task)
    result = grade_episode(task, trace, state)
    assert episode_reward(result) > 0


def test_liar_pc001_is_catastrophic_negative() -> None:
    task = load_task("v0/pc-001")
    env, trace = _drive(task, build("liar", task), 0)
    result = grade_episode(task, trace, env.state)
    assert result.catastrophic_codes
    assert episode_reward(result) == -1000
