"""Tests for the grader agreement report. T2.05."""

from __future__ import annotations

from pathlib import Path

from agentic_payments_env.annotations.agreement import copy_rule_aud01_agreement_rate


def test_agreement_report_exists_and_states_protocol() -> None:
    text = Path("reports/v0/grader-agreement.md").read_text(encoding="utf-8")
    assert "not yet measured" in text.lower()
    assert "agreement_rate" in text


def test_copy_rule_fake_judge_agreement_is_one() -> None:
    rate = copy_rule_aud01_agreement_rate()
    assert 0.0 <= rate <= 1.0
    assert rate == 1.0
