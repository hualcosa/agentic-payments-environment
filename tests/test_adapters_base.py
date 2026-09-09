"""Tests for ChatModel protocol types and FakeChatModel. T1.01."""

from __future__ import annotations

import pytest

from agentic_payments_env.adapters.base import (
    ChatMessage,
    FakeChatModel,
    ModelTurn,
    ToolSpec,
    Usage,
)


def test_usage_defaults_to_zeros() -> None:
    usage = Usage()
    assert usage.input_tokens == 0
    assert usage.output_tokens == 0


def test_fake_chat_model_returns_scripted_turns_in_order() -> None:
    first = ModelTurn(tool_calls=[], text="one", usage=Usage(input_tokens=1, output_tokens=2))
    second = ModelTurn(
        tool_calls=[{"id": "c1", "name": "lookup_pix_key", "arguments": {"key": "a"}}],
        text="two",
    )
    model = FakeChatModel([first, second], model_id="fake-test")
    tools = [
        ToolSpec(
            name="lookup_pix_key",
            description="look up",
            parameters={"type": "object", "properties": {}},
        )
    ]
    messages = [ChatMessage(role="user", content="go")]
    assert model.model_id == "fake-test"
    assert model.complete(messages, tools) == first
    assert model.complete(messages, tools) == second


def test_fake_chat_model_exhaustion_raises() -> None:
    model = FakeChatModel([])
    with pytest.raises(IndexError, match="no remaining scripted turns"):
        model.complete([], [])
