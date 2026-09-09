"""Build EpisodeAnnotation rows from graded traces. M2 T2.02. REQ-GRD-11."""

from __future__ import annotations

from agentic_payments_env.annotations.schema import EpisodeAnnotation, StepAnnotation
from agentic_payments_env.contracts.grading import EpisodeResult
from agentic_payments_env.contracts.tasks import TaskSpec
from agentic_payments_env.contracts.trace import EpisodeTrace


def from_episode(
    task: TaskSpec,
    trace: EpisodeTrace,
    result: EpisodeResult,
) -> EpisodeAnnotation:
    """Label an episode with unique grader violation codes. T2.02. REQ-GRD-11."""
    codes = sorted({item.code for item in result.violations})
    steps: list[StepAnnotation] = []
    if trace.steps:
        steps = [StepAnnotation(step_index=trace.steps[-1].step_index, codes=codes)]
    return EpisodeAnnotation(
        task_id=task.task_id,
        seed=trace.seed,
        agent_name=trace.agent_name,
        annotator="rule-graders",
        episode_codes=codes,
        steps=steps,
    )
