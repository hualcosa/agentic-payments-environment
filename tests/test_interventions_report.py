"""Intervention evaluation report. T5.03."""

from __future__ import annotations

from pathlib import Path


def test_interventions_report_not_yet_measured() -> None:
    text = Path("reports/v1/interventions.md").read_text(encoding="utf-8").lower()
    assert "not yet measured" in text
    assert "v1" in text or "held-out" in text
