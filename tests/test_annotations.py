"""Tests for annotation schema and JSONL IO. T2.01."""

from __future__ import annotations

import ast
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
from agentic_payments_env.graders.taxonomy import TAXONOMY


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


def test_rejects_unknown_well_shaped_code() -> None:
    with pytest.raises(ValidationError, match="unknown taxonomy code"):
        EpisodeAnnotation(
            task_id="v0/rt-001",
            seed=0,
            agent_name="x",
            annotator="human",
            episode_codes=["FIN-99"],
        )


def test_rejects_step_index_zero() -> None:
    with pytest.raises(ValidationError):
        StepAnnotation(step_index=0, codes=[])


def test_four_letter_prefix_codes_allowed() -> None:
    record = EpisodeAnnotation(
        task_id="v0/rt-001",
        seed=0,
        agent_name="x",
        annotator="rule-graders",
        episode_codes=["AUTH-07", "TASK-02"],
    )
    assert record.episode_codes == ["AUTH-07", "TASK-02"]


@pytest.mark.parametrize("code", sorted(TAXONOMY))
def test_every_taxonomy_code_accepted(code: str) -> None:
    record = EpisodeAnnotation(
        task_id="v0/rt-001",
        seed=0,
        agent_name="x",
        annotator="rule-graders",
        episode_codes=[code],
        steps=[StepAnnotation(step_index=1, codes=[code])],
    )
    assert code in record.episode_codes


def test_empty_codes_allowed() -> None:
    record = EpisodeAnnotation(
        task_id="v0/rt-001",
        seed=0,
        agent_name="oracle",
        annotator="rule-graders",
    )
    assert record.episode_codes == []
    assert record.steps == []


def test_canonical_world_fixture_defined_only_in_conftest() -> None:
    """Positive canonical fixtures must not be duplicated across test modules."""
    repo_root = Path(__file__).resolve().parents[1]
    tests_dir = repo_root / "tests"
    offenders: list[str] = []
    for path in sorted(tests_dir.rglob("test_*.py")):
        if path.name == "conftest.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == "default_world_fixture":
                offenders.append(str(path.relative_to(repo_root)))
    assert offenders == []
