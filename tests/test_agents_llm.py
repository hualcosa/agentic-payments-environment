"""Tests for LLMAgent with FakeChatModel. T1.03."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from agentic_payments_env.adapters.base import FakeChatModel, ModelTurn
from agentic_payments_env.agents.llm import LLMAgent
from agentic_payments_env.contracts.actions import Action, Observation
from agentic_payments_env.contracts.common import EpisodeOutcome
from agentic_payments_env.contracts.tasks import TaskPublic
from agentic_payments_env.contracts.trace import StateTransition, Step
from agentic_payments_env.tools.specs import TOOL_SPECS

AWARE = datetime(2026, 3, 10, 14, 0, tzinfo=UTC)


def _reset_obs() -> Observation:
    return Observation(
        step_index=0,
        sim_time=AWARE,
        kind="reset",
        observed_at=AWARE,
        instruction="Pay Maria 50 reais.",
        principal={"customer_id": "cus_ana"},
        available_tools=list(TOOL_SPECS),
    )


def _tool_obs(*, step_index: int = 1, tool_name: str = "lookup_pix_key") -> Observation:
    return Observation(
        step_index=step_index,
        sim_time=AWARE,
        kind="tool_result",
        tool_name=tool_name,
        result={"holder_name": "Maria"},
        observed_at=AWARE,
    )


def _public(*, max_steps: int = 30) -> TaskPublic:
    return TaskPublic(instruction="Pay Maria 50 reais.", max_steps=max_steps)


def _history(action: Action, observation: Observation) -> list[Step]:
    return [
        Step(
            step_index=1,
            action=action,
            observation=observation,
            transition=StateTransition(
                step_index=1,
                state_hash_before="a" * 64,
                state_hash_after="b" * 64,
                audit_seq_range=(1, 1),
                balances_after={},
            ),
        )
    ]


def _agent(turns: list[ModelTurn]) -> LLMAgent:
    return LLMAgent(FakeChatModel(turns), system_prompt="You are careful.", prompt_id="v1")


def test_valid_tool_call() -> None:
    turn = ModelTurn(
        tool_calls=[
            {
                "id": "c1",
                "name": "lookup_pix_key",
                "arguments": {"pix_key": "maria@bank.com"},
            }
        ],
        text="looking up",
    )
    agent = _agent([turn])
    public = _public()
    reset = _reset_obs()
    agent.reset(public, reset)
    action = agent.act([], reset)
    assert action.tool_name == "lookup_pix_key"
    assert action.arguments == {"pix_key": "maria@bank.com"}
    assert action.rationale == "looking up"


def test_malformed_arguments_become_empty_dict() -> None:
    turn = ModelTurn(
        tool_calls=[{"id": "c1", "name": "lookup_pix_key", "arguments": "{not-json"}],
        text="",
    )
    agent = _agent([turn])
    reset = _reset_obs()
    agent.reset(_public(), reset)
    action = agent.act([], reset)
    assert action.tool_name == "lookup_pix_key"
    assert action.arguments == {}


def test_unknown_tool_name_is_forwarded() -> None:
    turn = ModelTurn(
        tool_calls=[{"id": "c1", "name": "explode_world", "arguments": {}}],
        text="oops",
    )
    agent = _agent([turn])
    reset = _reset_obs()
    agent.reset(_public(), reset)
    action = agent.act([], reset)
    assert action.tool_name == "explode_world"
    assert action.arguments == {}


def test_text_only_response_finishes_declined() -> None:
    turn = ModelTurn(tool_calls=[], text="I will not pay that recipient.")
    agent = _agent([turn])
    reset = _reset_obs()
    agent.reset(_public(), reset)
    action = agent.act([], reset)
    assert action.tool_name == "finish"
    assert action.arguments["outcome"] == EpisodeOutcome.DECLINED.value
    assert action.arguments["report"] == "I will not pay that recipient."


def test_forced_finish_at_max_steps_minus_one() -> None:
    first = ModelTurn(
        tool_calls=[{"id": "c1", "name": "lookup_pix_key", "arguments": {"pix_key": "x"}}],
        text="lookup",
    )
    agent = _agent([first])
    public = _public(max_steps=2)
    reset = _reset_obs()
    agent.reset(public, reset)
    first_action = agent.act([], reset)
    tool_obs = _tool_obs()
    second = agent.act(_history(first_action, tool_obs), tool_obs)
    assert second.tool_name == "finish"
    assert second.arguments == {
        "outcome": EpisodeOutcome.DECLINED.value,
        "report": "forced finish: max_steps",
    }


def test_llm_agent_exported() -> None:
    from agentic_payments_env.agents import LLMAgent as Exported

    assert Exported is LLMAgent
    _: Any = Exported
