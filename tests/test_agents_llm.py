"""Tests for LLMAgent with FakeChatModel. T1.03."""

from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

import pytest

from agentic_payments_env.adapters.base import (
    ChatMessage,
    FakeChatModel,
    ModelTurn,
    ToolSpec,
    Usage,
)
from agentic_payments_env.agents.llm import LLMAgent, LLMAgentProtocolError
from agentic_payments_env.contracts.actions import Action, Observation, ToolError
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


def _error_obs(*, step_index: int = 1, tool_name: str = "lookup_pix_key") -> Observation:
    return Observation(
        step_index=step_index,
        sim_time=AWARE,
        kind="tool_error",
        tool_name=tool_name,
        error=ToolError(code="INVALID_ARGUMENT", message="bad arguments"),
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


class RecordingChatModel:
    """Scripted model that snapshots each request. REQ-CON-10, REQ-TOOL-08."""

    model_id = "recording"

    def __init__(self, turns: Sequence[ModelTurn]) -> None:
        self._turns = list(turns)
        self.requests: list[list[ChatMessage]] = []

    def complete(self, messages: Sequence[ChatMessage], tools: Sequence[ToolSpec]) -> ModelTurn:
        del tools
        self.requests.append(deepcopy(list(messages)))
        return self._turns[len(self.requests) - 1]


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


def test_multiple_tool_calls_are_rejected_atomically_but_usage_is_retained() -> None:
    model = RecordingChatModel(
        [
            ModelTurn(
                tool_calls=[
                    {"id": "c1", "name": "lookup_pix_key", "arguments": {"pix_key": "x"}},
                    {"id": "c2", "name": "finish", "arguments": {}},
                ],
                text="two calls",
                usage=Usage(input_tokens=11, output_tokens=7),
            )
        ]
    )
    agent = LLMAgent(model, system_prompt="system", prompt_id="v1")
    reset = _reset_obs()
    agent.reset(_public(), reset)

    with pytest.raises(LLMAgentProtocolError, match=r"^LLM_PROTOCOL_MULTIPLE_TOOL_CALLS count=2$"):
        agent.act([], reset)

    assert agent.usage_log == [Usage(input_tokens=11, output_tokens=7)]
    assert [message.role for message in agent._messages] == ["system", "user", "user"]
    assert all(message.tool_calls is None for message in agent._messages)
    assert agent._pending_tool_call_id is None


@pytest.mark.parametrize("invalid_id", [None, 7, "", "   ", "\t\n"])
def test_invalid_single_tool_call_id_is_rejected(invalid_id: object) -> None:
    agent = _agent(
        [
            ModelTurn(
                tool_calls=[
                    {"id": invalid_id, "name": "lookup_pix_key", "arguments": {"pix_key": "x"}}
                ],
                text="lookup",
            )
        ]
    )
    reset = _reset_obs()
    agent.reset(_public(), reset)

    with pytest.raises(LLMAgentProtocolError, match=r"^LLM_PROTOCOL_INVALID_TOOL_CALL_ID"):
        agent.act([], reset)

    assert agent._pending_tool_call_id is None
    assert all(message.role != "assistant" for message in agent._messages)


def test_valid_tool_call_id_is_preserved_exactly_in_next_request() -> None:
    model = RecordingChatModel(
        [
            ModelTurn(
                tool_calls=[
                    {
                        "id": "  provider-id  ",
                        "name": "lookup_pix_key",
                        "arguments": {"pix_key": "x"},
                    }
                ],
                text="lookup",
            ),
            ModelTurn(tool_calls=[], text="done"),
        ]
    )
    agent = LLMAgent(model, system_prompt="system", prompt_id="v1")
    reset = _reset_obs()
    agent.reset(_public(), reset)
    first_action = agent.act([], reset)
    observation = _tool_obs()
    agent.act(_history(first_action, observation), observation)

    tool_message = model.requests[1][-1]
    assert tool_message.role == "tool"
    assert tool_message.tool_call_id == "  provider-id  "
    assert tool_message.name == "lookup_pix_key"


def test_three_turn_transcript_correlates_success_and_error_observations() -> None:
    model = RecordingChatModel(
        [
            ModelTurn(
                tool_calls=[{"id": "c1", "name": "lookup_pix_key", "arguments": {}}],
                text="first",
            ),
            ModelTurn(
                tool_calls=[{"id": "c2", "name": "explode_world", "arguments": {}}],
                text="second",
            ),
            ModelTurn(tool_calls=[], text="stop"),
        ]
    )
    agent = LLMAgent(model, system_prompt="system", prompt_id="v1")
    reset = _reset_obs()
    agent.reset(_public(), reset)
    first_action = agent.act([], reset)
    first_obs = _tool_obs()
    second_action = agent.act(_history(first_action, first_obs), first_obs)
    second_obs = _error_obs(step_index=2, tool_name="explode_world")
    history = _history(first_action, first_obs) + _history(second_action, second_obs)
    agent.act(history, second_obs)

    third_request = model.requests[2]
    assistants = [message for message in third_request if message.role == "assistant"]
    results = [message for message in third_request if message.role == "tool"]
    assert [message.tool_calls[0]["id"] for message in assistants if message.tool_calls] == [
        "c1",
        "c2",
    ]
    assert [message.tool_call_id for message in results] == ["c1", "c2"]
    assert '"code":"INVALID_ARGUMENT"' in (results[1].content or "")


def test_reset_after_protocol_failure_clears_transcript_pending_id_and_usage() -> None:
    turn = ModelTurn(
        tool_calls=[
            {"id": "c1", "name": "lookup_pix_key", "arguments": {}},
            {"id": "c2", "name": "finish", "arguments": {}},
        ],
        text="bad",
        usage=Usage(input_tokens=3, output_tokens=2),
    )
    agent = _agent([turn])
    reset = _reset_obs()
    agent.reset(_public(), reset)
    with pytest.raises(LLMAgentProtocolError):
        agent.act([], reset)

    agent.reset(_public(), reset)
    assert [message.role for message in agent._messages] == ["system", "user"]
    assert agent._pending_tool_call_id is None
    assert agent.usage_log == []


def test_missing_id_and_rejected_turn_require_reset_before_another_request() -> None:
    model = RecordingChatModel(
        [
            ModelTurn(
                tool_calls=[{"name": "lookup_pix_key", "arguments": {}}],
                text="private rejected text",
                usage=Usage(input_tokens=3, output_tokens=2),
            ),
            ModelTurn(tool_calls=[], text="decline"),
        ]
    )
    agent = LLMAgent(model, system_prompt="system", prompt_id="v1")
    reset = _reset_obs()
    agent.reset(_public(), reset)
    reason = "LLM_PROTOCOL_INVALID_TOOL_CALL_ID type=NoneType"
    with pytest.raises(LLMAgentProtocolError, match=f"^{reason}$"):
        agent.act([], reset)
    snapshot = deepcopy(agent._messages)
    with pytest.raises(LLMAgentProtocolError, match=f"^{reason}$"):
        agent.act([], reset)
    assert agent._messages == snapshot
    assert len(model.requests) == 1
    assert agent.usage_log == [Usage(input_tokens=3, output_tokens=2)]
    assert agent.protocol_error == reason

    agent.reset(_public(), reset)
    assert agent.protocol_error is None
    action = agent.act([], reset)
    assert action.tool_name == "finish"
    assert len(model.requests) == 2
    assert len(model.requests[-1]) == 3
    assert "private rejected text" not in str(model.requests[-1])


def test_reset_discards_pending_successful_call_before_next_episode() -> None:
    model = RecordingChatModel(
        [
            ModelTurn(
                tool_calls=[{"id": "old-id", "name": "lookup_pix_key", "arguments": {}}],
                text="old episode",
                usage=Usage(input_tokens=3, output_tokens=2),
            ),
            ModelTurn(tool_calls=[], text="decline"),
        ]
    )
    agent = LLMAgent(model, system_prompt="system", prompt_id="v1")
    reset = _reset_obs()
    agent.reset(_public(), reset)
    agent.act([], reset)
    assert agent._pending_tool_call_id == "old-id"
    agent.reset(_public(), reset)
    assert agent._pending_tool_call_id is None
    assert agent.usage_log == []
    agent.act([], reset)
    assert [message.role for message in model.requests[-1]] == ["system", "user", "user"]
    assert "old-id" not in str(model.requests[-1])


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


def test_forced_finish_with_max_steps_one_makes_no_model_request() -> None:
    model = RecordingChatModel([])
    agent = LLMAgent(model, system_prompt="system", prompt_id="v1")
    reset = _reset_obs()
    agent.reset(_public(max_steps=1), reset)

    action = agent.act([], reset)

    assert action.tool_name == "finish"
    assert model.requests == []
    assert agent.usage_log == [Usage()]


def test_llm_agent_exported() -> None:
    from agentic_payments_env.agents import LLMAgent as Exported

    assert Exported is LLMAgent
    _: Any = Exported
