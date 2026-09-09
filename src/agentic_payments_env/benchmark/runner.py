"""Episode runner. REQ-ENV-18."""

from __future__ import annotations

from agentic_payments_env.agents.base import Agent
from agentic_payments_env.contracts.common import TerminationReason
from agentic_payments_env.contracts.tasks import TaskSpec
from agentic_payments_env.contracts.trace import EpisodeTrace, Step
from agentic_payments_env.environment import PaymentsEnvironment


def run_episode(
    task: TaskSpec, agent: Agent, seed: int = 0, *, strict: bool = True
) -> EpisodeTrace:
    """Reset, loop ``agent.act`` until the environment is done. REQ-ENV-18."""
    env = PaymentsEnvironment(task, seed, strict=strict)
    obs = env.reset()
    agent.reset(task.public, obs)
    history: list[Step] = []
    while not env.done:
        try:
            action = agent.act(history, obs)
        except Exception as exc:
            return env.trace(agent.name, termination=TerminationReason.AGENT_ERROR, error=str(exc))
        obs, _done = env.step(action)
        history = list(env.steps)
    return env.trace(agent.name)
