"""Environment reset/step lifecycle. REQ-ENV-01, REQ-ENV-02, REQ-ENV-03, REQ-ENV-08-10."""

from __future__ import annotations

import pytest

from agentic_payments_env.contracts.actions import Action, ToolErrorCode
from agentic_payments_env.contracts.common import TerminationReason
from agentic_payments_env.contracts.tasks import TaskPublic
from agentic_payments_env.environment import PaymentsEnvironment
from tests.conftest import default_task


def test_req_env_01_reset_is_idempotent() -> None:
    task = default_task()
    env = PaymentsEnvironment(task, 0, strict=True)
    env.reset()
    first = env.state_hash()
    env.step(Action(tool_name="get_customer_profile", arguments={}))
    env.reset()
    assert env.state_hash() == first
    env2 = PaymentsEnvironment(task, 0, strict=True)
    env2.reset()
    assert env2.state_hash() == first


def test_req_env_02_step_before_reset_raises() -> None:
    env = PaymentsEnvironment(default_task(), 0, strict=True)
    with pytest.raises(RuntimeError):
        env.step(Action(tool_name="get_customer_profile", arguments={}))


def test_req_env_03_step_after_done_does_not_mutate() -> None:
    env = PaymentsEnvironment(default_task(), 0, strict=True)
    env.reset()
    env.step(Action(tool_name="finish", arguments={"outcome": "DECLINED", "report": "stop"}))
    assert env.done
    hashed = env.state_hash()
    now = env.state.now
    steps = len(env.steps)
    obs, done = env.step(Action(tool_name="get_customer_profile", arguments={}))
    assert done is True
    assert obs.error is not None
    assert obs.error.code == ToolErrorCode.EPISODE_FINISHED
    assert env.state_hash() == hashed
    assert env.state.now == now
    assert len(env.steps) == steps


def test_req_env_08_clock_ticks_on_failed_action() -> None:
    env = PaymentsEnvironment(default_task(), 0, strict=True)
    env.reset()
    before = env.state.now
    obs, _done = env.step(Action(tool_name="not_a_tool", arguments={}))
    assert obs.error is not None
    assert obs.error.code == ToolErrorCode.UNKNOWN_TOOL
    assert env.state.now > before


def test_req_env_09_observation_step_index_and_sim_time() -> None:
    env = PaymentsEnvironment(default_task(), 0, strict=True)
    env.reset()
    obs, _done = env.step(Action(tool_name="get_customer_profile", arguments={}))
    assert obs.step_index == 1
    assert obs.sim_time == env.state.now


def test_req_env_10_max_steps_keeps_tool_observation() -> None:
    task = default_task().model_copy(update={"public": TaskPublic(instruction="x", max_steps=1)})
    env = PaymentsEnvironment(task, 0, strict=True)
    env.reset()
    obs, done = env.step(Action(tool_name="get_customer_profile", arguments={}))
    assert done is True
    assert obs.kind == "tool_result"
    trace = env.trace("tester")
    assert trace.termination == TerminationReason.MAX_STEPS
    assert trace.declared_outcome is None
    assert trace.final_report is None
