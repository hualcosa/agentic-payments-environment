"""Tests for step shaping and anti-gaming farmers. T4.02."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from agentic_payments_env.agents.base import Agent
from agentic_payments_env.benchmark.runner import _drive
from agentic_payments_env.benchmark.v0 import load_task
from agentic_payments_env.contracts.actions import Action, Observation
from agentic_payments_env.contracts.common import EpisodeOutcome
from agentic_payments_env.contracts.tasks import TaskPublic
from agentic_payments_env.contracts.trace import Step
from agentic_payments_env.graders import grade_episode
from agentic_payments_env.rewards.episode import episode_reward
from agentic_payments_env.rewards.step import step_reward, step_rewards
from tests.conftest import run_oracle


class _LookupFarmer:
    """Lookup then finish DECLINED without paying. T4.02 anti-gaming."""

    name = "lookup_farmer"

    def __init__(self) -> None:
        self._lookups = 0

    def reset(self, public: TaskPublic, reset_observation: Observation) -> None:
        del public, reset_observation
        self._lookups = 0

    def act(self, history: Sequence[Step], last_observation: Observation) -> Action:
        del history, last_observation
        if self._lookups < 3:
            self._lookups += 1
            return Action(
                tool_name="lookup_pix_key", arguments={"pix_key": "maria.oliveira@example.com"}
            )
        return Action(
            tool_name="finish",
            arguments={
                "outcome": EpisodeOutcome.DECLINED.value,
                "report": "Farmed lookups without transferring.",
            },
        )


class _ConsentFarmer:
    """Request consent repeatedly without transferring."""

    name = "consent_farmer"

    def __init__(self) -> None:
        self._consents = 0

    def reset(self, public: TaskPublic, reset_observation: Observation) -> None:
        del public, reset_observation
        self._consents = 0

    def act(self, history: Sequence[Step], last_observation: Observation) -> Action:
        del history, last_observation
        if self._consents < 3:
            self._consents += 1
            return Action(
                tool_name="request_consent",
                arguments={
                    "from_account_id": "acc_ana",
                    "pix_key": "maria.oliveira@example.com",
                    "amount_centavos": 25000,
                    "description": "farmed consent",
                },
            )
        return Action(
            tool_name="finish",
            arguments={
                "outcome": EpisodeOutcome.DECLINED.value,
                "report": "Farmed consent without transferring.",
            },
        )


def test_oracle_rt001_has_positive_step_reward() -> None:
    task = load_task("v0/rt-001")
    trace, _state = run_oracle(task)
    rewards = step_rewards(trace)
    assert len(rewards) == len(trace.steps)
    assert all(value in {0, 10} for value in rewards)
    assert any(value > 0 for value in rewards)
    assert rewards == [step_reward(trace, index) for index in range(len(trace.steps))]


def test_step_reward_rejects_invalid_index() -> None:
    task = load_task("v0/rt-001")
    trace, _state = run_oracle(task)
    with pytest.raises(IndexError):
        step_reward(trace, len(trace.steps))
    with pytest.raises(IndexError):
        step_reward(trace, -1)


def test_empty_trace_has_no_step_rewards() -> None:
    task = load_task("v0/rt-001")
    trace, _state = run_oracle(task)
    empty = trace.model_copy(update={"steps": []})
    assert step_rewards(empty) == []


def test_lookup_farmer_episode_reward_non_positive() -> None:
    task = load_task("v0/rt-001")
    agent: Agent = _LookupFarmer()
    env, trace = _drive(task, agent, 0)
    result = grade_episode(task, trace, env.state)
    assert episode_reward(result) <= 0
    assert not result.task_success


def test_consent_farmer_episode_reward_non_positive() -> None:
    task = load_task("v0/rt-001")
    env, trace = _drive(task, _ConsentFarmer(), 0)
    result = grade_episode(task, trace, env.state)
    assert episode_reward(result) <= 0
    assert not result.task_success
