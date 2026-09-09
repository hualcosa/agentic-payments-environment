"""Tests for the committed v0 scripted annotation corpus. T2.03."""

from __future__ import annotations

from pathlib import Path

from agentic_payments_env.annotations.corpus import PRESETS, dumps_scripted_corpus
from agentic_payments_env.annotations.schema import read_jsonl
from agentic_payments_env.benchmark.v0 import all_tasks


def test_scripted_corpus_has_at_least_100_and_matches_commit() -> None:
    committed = Path("annotations/v0-scripted.jsonl")
    assert committed.is_file()
    rows = read_jsonl(committed)
    expected = len(all_tasks()) * len(PRESETS)
    assert len(rows) >= 100
    assert len(rows) == expected
    assert committed.read_text(encoding="utf-8") == dumps_scripted_corpus()
