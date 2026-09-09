"""Reproducibility note and numeric claim provenance. T6.02."""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_reproducibility_lists_lockfile_and_oracle_command() -> None:
    text = Path("reports/reproducibility.md").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "uv.lock" in text
    assert "apenv bench" in text
    assert "oracle" in lowered
    assert "not yet measured" in lowered


def test_oracle_report_documents_provenance() -> None:
    text = Path("reports/v0/oracle.md").read_text(encoding="utf-8").lower()
    assert "provenance" in text
    assert "d-14" in text
    assert "apenv bench" in text


def test_committed_numeric_reports_have_source_artifacts() -> None:
    """Headline numeric tables must come from committed reports or datasets."""
    oracle = Path("reports/v0/oracle.md").read_text(encoding="utf-8")
    assert re.search(r"\|\s*safe success rate\s*\|", oracle, re.I)
    assert Path("benchmarks/v0").is_dir()
    assert any(Path("benchmarks/v0").glob("*.json"))


def test_no_stale_llm_absence_claim_in_readme() -> None:
    readme = Path("README.md").read_text(encoding="utf-8").lower()
    assert "no llm agents yet" not in readme
