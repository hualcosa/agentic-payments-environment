"""Tests for grader-derived episode annotations. T2.02."""

from __future__ import annotations

from pathlib import Path

from agentic_payments_env.agents.presets import build
from agentic_payments_env.annotations.from_grade import from_episode
from agentic_payments_env.annotations.schema import read_jsonl
from agentic_payments_env.benchmark.runner import _drive
from agentic_payments_env.benchmark.v0 import load_task
from agentic_payments_env.cli import main
from agentic_payments_env.graders import grade_episode


def test_oracle_rt001_has_empty_codes() -> None:
    task = load_task("v0/rt-001")
    env, trace = _drive(task, build("oracle", task), 0)
    result = grade_episode(task, trace, env.state)
    record = from_episode(task, trace, result)
    assert record.annotator == "rule-graders"
    assert record.episode_codes == []
    assert record.steps
    assert record.steps[0].step_index == trace.steps[-1].step_index


def test_quitter_rt001_has_codes() -> None:
    task = load_task("v0/rt-001")
    env, trace = _drive(task, build("quitter", task), 0)
    result = grade_episode(task, trace, env.state)
    record = from_episode(task, trace, result)
    assert record.episode_codes
    assert record.episode_codes == sorted(record.episode_codes)


def test_annotate_trace_cli_appends(tmp_path: Path) -> None:
    out_run = tmp_path / "run"
    assert main(["run", "--task", "v0/rt-001", "--agent", "quitter", "--out", str(out_run)]) == 0
    trace_path = out_run / "v0_rt-001" / "seed-0.trace.json"
    result_path = out_run / "v0_rt-001" / "seed-0.result.json"
    jsonl = tmp_path / "ann.jsonl"
    assert (
        main(
            [
                "annotate-trace",
                "--trace",
                str(trace_path),
                "--result",
                str(result_path),
                "--out",
                str(jsonl),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "annotate-trace",
                "--trace",
                str(trace_path),
                "--result",
                str(result_path),
                "--out",
                str(jsonl),
            ]
        )
        == 0
    )
    rows = read_jsonl(jsonl)
    assert len(rows) == 2
    assert rows[0].episode_codes == rows[1].episode_codes
    assert rows[0].episode_codes
