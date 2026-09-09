"""Tests for oracle SFT JSONL export. T5.02."""

from __future__ import annotations

import json
from pathlib import Path

from agentic_payments_env.cli import main
from agentic_payments_env.export_sft import export_sft


def test_export_sft_rt001_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "sft.jsonl"
    export_sft(["v0/rt-001"], path)
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["task_id"] == "v0/rt-001"
    assert row["agent"] == "oracle"
    assert isinstance(row["actions"][0]["tool_name"], str)


def test_export_sft_cli(tmp_path: Path) -> None:
    path = tmp_path / "cli.jsonl"
    assert main(["export-sft", "--task", "v0/rt-001", "--out", str(path)]) == 0
    assert path.is_file()
    json.loads(path.read_text(encoding="utf-8").splitlines()[0])
