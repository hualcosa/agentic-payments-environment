"""M1 report placeholders must exist and must not invent rates. T1.06."""

from __future__ import annotations

from pathlib import Path

_REPORTS = (
    Path("reports/v0/gpt-4o-mini-v1.md"),
    Path("reports/v0/claude-haiku-4-5-v1.md"),
)


def test_examples_readme_not_yet_measured() -> None:
    path = Path("reports/v0/examples/README.md")
    assert path.is_file()
    assert "not yet measured" in path.read_text(encoding="utf-8").lower()


def test_two_v1_reports_exist() -> None:
    for path in _REPORTS:
        assert path.is_file(), path
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        if "not yet measured" in lowered:
            continue
        assert "safe_success_rate" in text or "safe success rate" in lowered
