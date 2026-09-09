"""Hidden ground truth must never appear in observations. REQ-ENV-12, 10 §6."""

from __future__ import annotations

import json

import pytest

from agentic_payments_env.benchmark.v0 import TASKS, load_task
from tests.conftest import run_oracle

LEAK_KEYS = (
    "oracle_plan",
    "expected_outcome",
    "injection_targets",
    "forbidden_pix_keys",
    "notes",
)


@pytest.mark.parametrize("task_id", sorted(TASKS))
def test_hidden_never_in_observations(task_id: str) -> None:
    task = load_task(task_id)
    trace, _state = run_oracle(task)
    observations = [trace.reset_observation, *[step.observation for step in trace.steps]]
    notes = task.hidden.notes
    for observation in observations:
        blob = json.dumps(observation.model_dump(mode="json"))
        for key in LEAK_KEYS:
            assert key not in blob
        if notes:
            assert notes not in blob
