"""Technical report section coverage and reference integrity. T6.01."""

from __future__ import annotations

import re
from pathlib import Path

STALE_CLAIMS = (
    "no llm agents yet",
    "q-16",
    "q-17",
)


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


def test_technical_report_has_no_stale_capability_claims() -> None:
    text = Path("reports/technical-report.md").read_text(encoding="utf-8").lower()
    for phrase in STALE_CLAIMS:
        assert phrase not in text, phrase


def test_technical_report_links_resolve() -> None:
    text = Path("reports/technical-report.md").read_text(encoding="utf-8")
    for match in re.finditer(r"\]\(([^)]+)\)", text):
        target = match.group(1)
        if target.startswith("http"):
            continue
        path = Path("reports/technical-report.md").parent / target
        assert path.exists(), target


def test_readme_oracle_provenance_matches_d14() -> None:
    readme = Path("README.md").read_text(encoding="utf-8").lower()
    assert "d-14" in readme or "reviewed report" in readme
    assert "reports/reproducibility.md" in readme
