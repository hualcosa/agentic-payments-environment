"""Reproducibility note and one-command artifact checks. T6.02, T7.19."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import agentic_payments_env.reproduce as reproduce_module
from agentic_payments_env.reproduce import check, rebuild, repo_root


def test_reproducibility_lists_lockfile_and_oracle_command() -> None:
    text = Path("reports/reproducibility.md").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "uv.lock" in text
    assert "apenv bench" in text
    assert "apenv reproduce" in lowered
    assert "oracle" in lowered
    assert "not yet measured" in lowered


def test_oracle_report_documents_provenance() -> None:
    text = Path("reports/v0/oracle.md").read_text(encoding="utf-8").lower()
    assert "provenance" in text
    assert "d-14" in text
    assert "apenv bench" in text


def test_committed_numeric_reports_have_source_artifacts() -> None:
    oracle = Path("reports/v0/oracle.md").read_text(encoding="utf-8")
    assert re.search(r"\|\s*safe success rate\s*\|", oracle, re.I)
    assert Path("benchmarks/v0").is_dir()
    assert any(Path("benchmarks/v0").glob("*.json"))


def test_no_stale_llm_absence_claim_in_readme() -> None:
    readme = Path("README.md").read_text(encoding="utf-8").lower()
    assert "no llm agents yet" not in readme


def test_reproduce_rebuild_writes_only_under_out_dir(tmp_path: Path) -> None:
    out = tmp_path / "repro"
    rebuild(out)
    assert (out / "annotations" / "v0-scripted.jsonl").is_file()
    assert (out / "reports" / "v0" / "oracle.md").is_file()
    assert (out / "reports" / "v1" / "reward-spec.md").read_bytes() == Path(
        "reports/v1/reward-spec.md"
    ).read_bytes()
    assert not any(repo_root().joinpath("annotations").glob("*.tmp"))


def test_reproduce_check_matches_committed_artifacts(tmp_path: Path) -> None:
    check(tmp_path / "repro_check")


def test_reproduce_check_detects_reward_artifact_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(reproduce_module, "_reward_spec_markdown", lambda: "tampered\n")
    with pytest.raises(SystemExit, match=r"reports/v1/reward-spec\.md"):
        check(tmp_path / "reward_mismatch")


def test_reproduce_rejects_nonempty_output_dir(tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    (out / "leftover.txt").write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit, match="empty or nonexistent"):
        rebuild(out)
