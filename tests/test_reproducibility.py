"""Reproducibility note. T6.02."""

from __future__ import annotations

from pathlib import Path


def test_reproducibility_lists_lockfile_and_oracle_command() -> None:
    text = Path("reports/reproducibility.md").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "uv.lock" in text
    assert "apenv bench" in text
    assert "oracle" in lowered
    assert "not yet measured" in lowered
