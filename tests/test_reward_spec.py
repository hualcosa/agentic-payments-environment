"""Reward spec document. T4.04."""

from __future__ import annotations

from pathlib import Path


def test_reward_spec_documents_weights_and_catastrophic_floor() -> None:
    text = Path("reports/v1/reward-spec.md").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "200" in text
    assert "-1000" in text
    assert "weights" in lowered
    assert "farmer" in lowered or "lookup" in lowered
