"""Rule vs copy-rule FakeChatModel agreement on AUD-01. M2 T2.05."""

from __future__ import annotations

import json

from agentic_payments_env.adapters.base import FakeChatModel, ModelTurn
from agentic_payments_env.agents.presets import build
from agentic_payments_env.annotations.corpus import PRESETS
from agentic_payments_env.benchmark.runner import _drive
from agentic_payments_env.benchmark.v0 import all_tasks
from agentic_payments_env.graders import grade_episode
from agentic_payments_env.graders.llm_judge import ReportTruthJudge


def copy_rule_aud01_agreement_rate() -> float:
    """Fraction of episodes where the judge copies the rule AUD-01 bit. T2.05."""
    matched = 0
    total = 0
    for task in all_tasks():
        for name in PRESETS:
            env, trace = _drive(task, build(name, task), 0)
            result = grade_episode(task, trace, env.state)
            omits = any(item.code == "AUD-01" for item in result.violations)
            text = json.dumps({"omits_transfer_ids": omits, "note": "copy-rule"})
            judge = ReportTruthJudge(FakeChatModel([ModelTurn(tool_calls=[], text=text)]))
            judged = any(
                item.code == "AUD-01" for item in judge.grade(task, trace, env.state).violations
            )
            total += 1
            if omits == judged:
                matched += 1
    if total == 0:
        return 0.0
    return matched / total
