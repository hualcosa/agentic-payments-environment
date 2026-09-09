"""Technical report section coverage. T6.01."""

from __future__ import annotations

from pathlib import Path


def test_technical_report_has_required_sections() -> None:
    text = Path("reports/technical-report.md").read_text(encoding="utf-8").lower()
    for heading in (
        "research question",
        "environment",
        "benchmark",
        "graders",
        "baseline failures",
        "interventions",
        "limitations",
        "reproducibility",
    ):
        assert heading in text, heading
    assert "not yet measured" in text
