"""Taxonomy v1 evidence file. T2.06."""

from __future__ import annotations

from pathlib import Path


def test_taxonomy_v1_file_records_no_additions() -> None:
    text = Path("reports/v0/taxonomy-v1.md").read_text(encoding="utf-8").lower()
    assert "no codes added" in text or "no code" in text
    assert "taxonomy v1" in text
