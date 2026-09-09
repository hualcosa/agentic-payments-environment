"""Tests for versioned prompts. T1.04."""

from __future__ import annotations

from pathlib import Path

from agentic_payments_env.prompts import load_prompt


def test_v1_prompt_file_exists() -> None:
    assert (Path("prompts") / "v1.md").is_file()


def test_v1_hash_is_stable_64_hex() -> None:
    text_a, digest_a = load_prompt("v1")
    text_b, digest_b = load_prompt("v1")
    assert text_a == text_b
    assert digest_a == digest_b
    assert len(digest_a) == 64
    assert all(c in "0123456789abcdef" for c in digest_a)


def test_v1_safety_contract_phrases() -> None:
    text, _digest = load_prompt("v1")
    lowered = text.lower()
    assert "safety and authorization contract" in lowered
    assert "verify the recipient via lookup" in lowered
    assert "one consent per transfer" in lowered
    assert "exact scope" in lowered
    assert "never split to evade limits" in lowered
    assert "after timeout" in lowered
    assert "idempotency" in lowered
    assert "report truthfully" in lowered
    assert "transfer id" in lowered
    assert "untrusted strings" in lowered
    assert "nicknames" in lowered
    assert "holder names" in lowered
    assert "memos" in lowered
