"""Grader protocol. REQ-CON-10."""

from __future__ import annotations

from typing import Protocol

from agentic_payments_env.contracts.grading import Dimension, GraderResult
from agentic_payments_env.contracts.tasks import TaskSpec
from agentic_payments_env.contracts.trace import EpisodeTrace
from agentic_payments_env.contracts.world import WorldState


class Grader(Protocol):
    """Scores one grading dimension for an episode. REQ-CON-10."""

    dimension: Dimension

    def grade(
        self, task: TaskSpec, trace: EpisodeTrace, final_state: WorldState
    ) -> GraderResult: ...
