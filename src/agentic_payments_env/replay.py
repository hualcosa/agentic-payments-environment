"""Replay a recorded episode against a fresh environment. REQ-ENV-16."""

from __future__ import annotations

from agentic_payments_env.contracts.common import FrozenModel
from agentic_payments_env.contracts.tasks import TaskSpec
from agentic_payments_env.contracts.trace import EpisodeTrace
from agentic_payments_env.environment import PaymentsEnvironment


class ReplayResult(FrozenModel):
    """Whether a replay matched the recorded hashes, observations, and audit. REQ-ENV-16."""

    matches: bool
    first_divergence_step: int | None
    expected_hash: str
    actual_hash: str


def replay(task: TaskSpec, trace: EpisodeTrace) -> ReplayResult:
    """Re-apply every recorded action and compare transitions. REQ-ENV-16."""
    env = PaymentsEnvironment(task, trace.seed, strict=True)
    env.reset()
    expected_final = trace.final_state_hash
    for recorded in trace.steps:
        observation, _done = env.step(recorded.action)
        actual = env.steps[-1]
        if (
            actual.transition.state_hash_after != recorded.transition.state_hash_after
            or actual.observation != recorded.observation
        ):
            return ReplayResult(
                matches=False,
                first_divergence_step=recorded.step_index,
                expected_hash=recorded.transition.state_hash_after,
                actual_hash=actual.transition.state_hash_after,
            )
        del observation
    if list(env.state.audit) != list(trace.audit):
        return ReplayResult(
            matches=False,
            first_divergence_step=None,
            expected_hash=expected_final,
            actual_hash=env.state_hash(),
        )
    matches = env.state_hash() == expected_final
    return ReplayResult(
        matches=matches,
        first_divergence_step=None
        if matches
        else (trace.steps[-1].step_index if trace.steps else 0),
        expected_hash=expected_final,
        actual_hash=env.state_hash(),
    )
