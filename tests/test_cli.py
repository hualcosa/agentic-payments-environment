"""CLI smoke tests. 06 §10."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_payments_env.cli import main


def test_list_tasks(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list-tasks"]) == 0
    out = capsys.readouterr().out
    assert "v0/rt-001" in out
    assert "ROUTINE_TRANSFER" in out
    assert "v0/adv-006" in out


def test_run_oracle_and_quitter(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "oracle"
    assert main(["run", "--task", "v0/rt-001", "--agent", "oracle", "--out", str(out)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["safe_success"] is True
    assert payload["task_success"] is True
    trace_path = out / "v0_rt-001" / "seed-0.trace.json"
    assert trace_path.is_file()
    assert (out / "v0_rt-001" / "seed-0.result.json").is_file()

    assert main(["run", "--task", "v0/rt-001", "--agent", "quitter"]) == 0
    quit_payload = json.loads(capsys.readouterr().out)
    assert quit_payload["safe_success"] is False
    assert "SAF-06" not in quit_payload["catastrophic_codes"]

    assert main(["replay", str(trace_path)]) == 0
    replay_payload = json.loads(capsys.readouterr().out)
    assert replay_payload["matches"] is True
