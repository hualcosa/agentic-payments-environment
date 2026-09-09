"""Tests for annotation schema and JSONL IO. T2.01."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from agentic_payments_env.annotations.schema import (
    EpisodeAnnotation,
    StepAnnotation,
    dumps_jsonl,
    loads_jsonl,
    read_jsonl,
    write_jsonl,
)


def _record(*, task_id: str, codes: list[str]) -> EpisodeAnnotation:
    return EpisodeAnnotation(
        task_id=task_id,
        seed=0,
        agent_name="oracle",
        annotator="rule-graders",
        episode_codes=codes,
        steps=[StepAnnotation(step_index=1, codes=codes, note="")],
    )


def test_jsonl_round_trip_two_records(tmp_path: Path) -> None:
    first = _record(task_id="v0/rt-001", codes=[])
    second = _record(task_id="v0/rt-002", codes=["SAF-06"])
    text = dumps_jsonl([first, second])
    assert loads_jsonl(text) == [first, second]
    path = tmp_path / "a.jsonl"
    write_jsonl(path, [first, second])
    assert read_jsonl(path) == [first, second]


def test_rejects_malformed_code() -> None:
    with pytest.raises(ValidationError):
        EpisodeAnnotation(
            task_id="v0/rt-001",
            seed=0,
            agent_name="x",
            annotator="human",
            episode_codes=["FIN-1"],
        )


def test_empty_codes_allowed() -> None:
    record = EpisodeAnnotation(
        task_id="v0/rt-001",
        seed=0,
        agent_name="oracle",
        annotator="rule-graders",
    )
    assert record.episode_codes == []
    assert record.steps == []
