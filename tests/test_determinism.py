"""Determinism on the default task and every v0 oracle run. REQ-ENV-01."""

from __future__ import annotations

from agentic_payments_env.agents.oracle import OracleAgent
from agentic_payments_env.benchmark.runner import run_episode
from agentic_payments_env.benchmark.v0 import TASKS, load_task
from agentic_payments_env.contracts.actions import Action
from agentic_payments_env.environment import PaymentsEnvironment
from tests.conftest import default_task


def _actions() -> list[Action]:
    return [
        Action(tool_name="get_customer_profile", arguments={}),
        Action(tool_name="list_beneficiaries", arguments={}),
        Action(
            tool_name="finish",
            arguments={"outcome": "DECLINED", "report": "stop"},
        ),
    ]


def test_default_task_two_runs_byte_identical() -> None:
    task = default_task()
    traces = []
    for _ in range(2):
        env = PaymentsEnvironment(task, 0, strict=True)
        env.reset()
        for action in _actions():
            env.step(action)
        traces.append(env.trace("det"))
    assert traces[0] == traces[1]
    assert traces[0].final_state_hash == traces[1].final_state_hash
    assert traces[0].audit == traces[1].audit


def test_oracle_two_runs_every_v0_task() -> None:
    for task_id in sorted(TASKS):
        task = load_task(task_id)
        trace_a = run_episode(task, OracleAgent(task.hidden, task.task_id), 0)
        trace_b = run_episode(task, OracleAgent(task.hidden, task.task_id), 0)
        assert trace_a == trace_b, task_id
        assert trace_a.final_state_hash == trace_b.final_state_hash
