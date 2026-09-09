"""Replay matching and divergence. REQ-ENV-16."""

from __future__ import annotations

from agentic_payments_env.contracts.actions import Action
from agentic_payments_env.environment import PaymentsEnvironment
from agentic_payments_env.replay import replay
from tests.conftest import default_task


def _run() -> tuple:
    task = default_task()
    env = PaymentsEnvironment(task, 7, strict=True)
    env.reset()
    env.step(
        Action(
            tool_name="check_transfer_policy",
            arguments={
                "from_account_id": "acc_ana",
                "pix_key": "maria.oliveira@example.com",
                "amount_centavos": 500_001,
            },
        )
    )
    env.step(Action(tool_name="finish", arguments={"outcome": "DECLINED", "report": "stop"}))
    return task, env.trace("tester")


def test_replay_matches() -> None:
    task, trace = _run()
    result = replay(task, trace)
    assert result.matches is True
    assert result.first_divergence_step is None
    assert result.expected_hash == result.actual_hash


def test_replay_mutated_action_diverges_at_that_step() -> None:
    task, trace = _run()
    step = trace.steps[0]
    args = dict(step.action.arguments)
    args["amount_centavos"] = int(args["amount_centavos"]) + 1
    mutated_action = step.action.model_copy(update={"arguments": args})
    mutated_step = step.model_copy(update={"action": mutated_action})
    mutated = trace.model_copy(update={"steps": [mutated_step, *trace.steps[1:]]})
    result = replay(task, mutated)
    assert result.matches is False
    assert result.first_divergence_step == 1
