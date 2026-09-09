"""v0.1 freeze decision. T2.07."""

from __future__ import annotations

from pathlib import Path


def test_v01_decision_file_exists() -> None:
    text = Path("reports/v0/v0.1-decision.md").read_text(encoding="utf-8").lower()
    assert Path("reports/v0/v0.1-decision.md").is_file()
    assert "no v0.1 freeze" in text
    assert "benchmarks/v0" in text
