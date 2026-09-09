"""Tests for the opt-in report-truth LLM judge. T2.04."""

from __future__ import annotations

from agentic_payments_env.adapters.base import FakeChatModel, ModelTurn
from agentic_payments_env.agents.presets import build
from agentic_payments_env.benchmark.runner import _drive
from agentic_payments_env.benchmark.v0 import load_task
from agentic_payments_env.graders import DEFAULT_GRADERS
from agentic_payments_env.graders.llm_judge import ReportTruthJudge


def test_judge_omits_transfer_ids_emits_aud01() -> None:
    task = load_task("v0/rt-001")
    env, trace = _drive(task, build("oracle", task), 0)
    model = FakeChatModel(
        [
            ModelTurn(
                tool_calls=[],
                text='{"omits_transfer_ids": true, "note": "missing ids"}',
            )
        ]
    )
    result = ReportTruthJudge(model).grade(task, trace, env.state)
    assert any(item.code == "AUD-01" for item in result.violations)


def test_malformed_json_emits_no_aud01() -> None:
    task = load_task("v0/rt-001")
    env, trace = _drive(task, build("oracle", task), 0)
    model = FakeChatModel([ModelTurn(tool_calls=[], text="not-json")])
    result = ReportTruthJudge(model).grade(task, trace, env.state)
    assert result.violations == []


def test_report_truth_judge_not_in_default_graders() -> None:
    assert not any(type(grader).__name__ == "ReportTruthJudge" for grader in DEFAULT_GRADERS)
