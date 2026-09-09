"""Tests for the policy-constrained generator. T3.03."""

from __future__ import annotations

from agentic_payments_env.contracts.common import EpisodeOutcome, TaskFamily
from agentic_payments_env.generators.base import GenParams, SeededRng
from agentic_payments_env.generators.policy import generate_policy
from agentic_payments_env.graders import grade_episode
from tests.conftest import run_oracle


def _params() -> GenParams:
    return GenParams(
        family=TaskFamily.POLICY_CONSTRAINED,
        amount_limit_ratio_numer=1,
        amount_limit_ratio_denom=20,
        n_recipients=1,
    )


def test_generate_policy_declined_over_limit() -> None:
    task = generate_policy(SeededRng(0), _params(), "v1/gen-pc-001")
    again = generate_policy(SeededRng(0), _params(), "v1/gen-pc-001")
    assert task.model_dump(mode="json") == again.model_dump(mode="json")
    assert task.hidden.expected_outcome == EpisodeOutcome.DECLINED
    limit = task.world.policy.per_transfer_limit_centavos or 0
    # amount lives on the oracle check step
    check = next(
        step for step in task.hidden.oracle_plan if step.tool_name == "check_transfer_policy"
    )
    amount = check.arguments["amount_centavos"]
    assert isinstance(amount, int)
    assert amount > limit
    trace, state = run_oracle(task)
    result = grade_episode(task, trace, state)
    assert result.safe_success is True
