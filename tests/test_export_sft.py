"""Tests for SFT JSONL export. T5.02."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_payments_env.benchmark.v1 import all_tasks as all_v1
from agentic_payments_env.cli import main
from agentic_payments_env.contracts.training import SFTRecord
from agentic_payments_env.export_sft import build_sft_records, dumps_sft, export_sft


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


def test_sft_record_validates() -> None:
    record = SFTRecord(
        task_id="v0/rt-001",
        agent="oracle",
        safe_success=True,
        actions=[{"tool_name": "finish", "arguments": {}}],
    )
    assert record.schema_version == "0.1"


def test_non_oracle_sft_filtered_by_safe_success() -> None:
    records = build_sft_records(["v0/rt-001"], agents=("oracle", "quitter"))
    agents = {record.agent for record in records}
    assert "oracle" in agents
    assert "quitter" not in agents


def test_held_out_sft_export_rejected() -> None:
    with pytest.raises(ValueError, match="held-out"):
        export_sft([all_v1()[0].task_id], Path("/tmp/x.jsonl"))


def test_committed_sft_v11_rebuilds() -> None:
    path = Path("datasets/sft-v1.1.jsonl")
    assert path.is_file()
    committed = path.read_text(encoding="utf-8")
    rebuilt = dumps_sft(build_sft_records(None, agents=("oracle", "quitter")))
    assert rebuilt == committed


def test_sft_rebuild_is_deterministic(tmp_path: Path) -> None:
    records = build_sft_records(["v0/rt-001"], agents=("oracle",))
    text = dumps_sft(records)
    export_sft(["v0/rt-001"], tmp_path / "sft.jsonl")
    assert (tmp_path / "sft.jsonl").read_text(encoding="utf-8") == text
