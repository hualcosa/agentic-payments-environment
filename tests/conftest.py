"""Shared pytest fixtures. REQ-TEST-02."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from agentic_payments_env.agents.oracle import OracleAgent
from agentic_payments_env.contracts.common import EpisodeOutcome, TaskFamily
from agentic_payments_env.contracts.tasks import OracleStep, TaskHidden, TaskPublic, TaskSpec
from agentic_payments_env.contracts.trace import EpisodeTrace, Step
from agentic_payments_env.environment import PaymentsEnvironment
from agentic_payments_env.world import WorldState
from tests.test_world import default_world_fixture


def default_task() -> TaskSpec:
    """Minimal valid task over the default world for environment tests."""
    return TaskSpec(
        task_id="v0/test-default",
        family=TaskFamily.ROUTINE_TRANSFER,
        title="default test task",
        world=default_world_fixture(),
        public=TaskPublic(instruction="Inspect the account and finish.", max_steps=30),
        hidden=TaskHidden(
            expected_outcome=EpisodeOutcome.DECLINED,
            oracle_plan=[
                OracleStep(tool_name="finish", arguments={"outcome": "DECLINED", "report": "stop"})
            ],
            oracle_steps=1,
        ),
    )


def run_oracle(task: TaskSpec, seed: int = 0) -> tuple[EpisodeTrace, WorldState]:
    """Drive OracleAgent without swallowing plan errors. REQ-TEST-02."""
    env = PaymentsEnvironment(task, seed, strict=True)
    agent = OracleAgent(task.hidden, task.task_id)
    obs = env.reset()
    agent.reset(task.public, obs)
    history: list[Step] = []
    while not env.done:
        action = agent.act(history, obs)
        obs, _done = env.step(action)
        history = list(env.steps)
    return env.trace(agent.name), env.state


@pytest.fixture
def env_factory() -> Callable[..., PaymentsEnvironment]:
    def _factory(
        task: TaskSpec | None = None, seed: int = 0, *, strict: bool = True
    ) -> PaymentsEnvironment:
        return PaymentsEnvironment(task or default_task(), seed, strict=strict)

    return _factory
