"""Tests for optional OpenAI and Anthropic adapters. T1.02."""

from __future__ import annotations

import importlib
import json
import sys
import types
from copy import deepcopy
from typing import Any

import pytest

from agentic_payments_env.adapters.base import ChatMessage, ToolSpec, Usage


def _purge(name: str) -> None:
    sys.modules.pop(name, None)


def _install_fake_openai(monkeypatch: pytest.MonkeyPatch, create: Any) -> types.ModuleType:
    fake = types.ModuleType("openai")

    class APIConnectionError(Exception):
        pass

    class APITimeoutError(Exception):
        pass

    class OpenAI:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs
            self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=create))

    fake.APIConnectionError = APIConnectionError  # type: ignore[attr-defined]
    fake.APITimeoutError = APITimeoutError  # type: ignore[attr-defined]
    fake.OpenAI = OpenAI  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "openai", fake)
    _purge("agentic_payments_env.adapters.openai_compat")
    return fake


def _install_fake_anthropic(monkeypatch: pytest.MonkeyPatch, create: Any) -> types.ModuleType:
    fake = types.ModuleType("anthropic")

    class APIConnectionError(Exception):
        pass

    class APITimeoutError(Exception):
        pass

    class Anthropic:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs
            self.messages = types.SimpleNamespace(create=create)

    fake.APIConnectionError = APIConnectionError  # type: ignore[attr-defined]
    fake.APITimeoutError = APITimeoutError  # type: ignore[attr-defined]
    fake.Anthropic = Anthropic  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    _purge("agentic_payments_env.adapters.anthropic")
    return fake


def _openai_ok_response() -> Any:
    return types.SimpleNamespace(
        choices=[
            types.SimpleNamespace(
                message=types.SimpleNamespace(
                    content="done",
                    tool_calls=[
                        types.SimpleNamespace(
                            id="call_1",
                            function=types.SimpleNamespace(
                                name="lookup_pix_key",
                                arguments='{"pix_key":"a@b.com"}',
                            ),
                        )
                    ],
                )
            )
        ],
        usage=types.SimpleNamespace(prompt_tokens=11, completion_tokens=7),
    )


def _anthropic_ok_response() -> Any:
    return types.SimpleNamespace(
        content=[
            types.SimpleNamespace(type="text", text="done"),
            types.SimpleNamespace(
                type="tool_use",
                id="toolu_1",
                name="lookup_pix_key",
                input={"pix_key": "a@b.com"},
            ),
        ],
        usage=types.SimpleNamespace(input_tokens=9, output_tokens=4),
    )


def _openai_text_response(text: str = "done") -> Any:
    return types.SimpleNamespace(
        choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=text, tool_calls=[]))],
        usage=types.SimpleNamespace(prompt_tokens=3, completion_tokens=2),
    )


def _anthropic_text_response(text: str = "done") -> Any:
    return types.SimpleNamespace(
        content=[types.SimpleNamespace(type="text", text=text)],
        usage=types.SimpleNamespace(input_tokens=3, output_tokens=2),
    )


def _conversation() -> list[ChatMessage]:
    return [
        ChatMessage(role="system", content="system"),
        ChatMessage(role="user", content="pay"),
        ChatMessage(
            role="assistant",
            content="lookup",
            tool_calls=[
                {
                    "id": "c1",
                    "name": "lookup_pix_key",
                    "arguments": {"pix_key": "a@b.com"},
                }
            ],
        ),
        ChatMessage(
            role="tool",
            name="lookup_pix_key",
            tool_call_id="c1",
            content='{"error":{"code":"INVALID_ARGUMENT"}}',
        ),
        ChatMessage(
            role="assistant",
            content="retry",
            tool_calls=[
                {
                    "id": "c2",
                    "name": "lookup_pix_key",
                    "arguments": {"pix_key": "maria@bank.com"},
                }
            ],
        ),
        ChatMessage(
            role="tool",
            name="lookup_pix_key",
            tool_call_id="c2",
            content='{"result":{"holder_name":"Maria"}}',
        ),
    ]


def _sample_inputs() -> tuple[list[ChatMessage], list[ToolSpec]]:
    messages = [ChatMessage(role="user", content="pay")]
    tools = [
        ToolSpec(
            name="lookup_pix_key",
            description="lookup",
            parameters={"type": "object", "properties": {}},
        )
    ]
    return messages, tools


def test_openai_complete_maps_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    def create(**kwargs: object) -> Any:
        assert kwargs["model"] == "gpt-test"
        return _openai_ok_response()

    _install_fake_openai(monkeypatch, create)
    mod = importlib.import_module("agentic_payments_env.adapters.openai_compat")
    model = mod.OpenAICompatChatModel("gpt-test", "https://example.invalid/v1", "sk-test")
    messages, tools = _sample_inputs()
    turn = model.complete(messages, tools)
    assert turn.text == "done"
    assert turn.tool_calls == [
        {"id": "call_1", "name": "lookup_pix_key", "arguments": {"pix_key": "a@b.com"}}
    ]
    assert turn.usage == Usage(input_tokens=11, output_tokens=7)


def test_openai_requests_serial_tools_and_preserves_multiturn_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[dict[str, object]] = []

    def create(**kwargs: object) -> Any:
        requests.append(deepcopy(kwargs))
        return _openai_text_response()

    _install_fake_openai(monkeypatch, create)
    mod = importlib.import_module("agentic_payments_env.adapters.openai_compat")
    model = mod.OpenAICompatChatModel("gpt-test", None, "sk-test")
    _, tools = _sample_inputs()
    model.complete(_conversation(), tools)

    request = requests[0]
    assert request["parallel_tool_calls"] is False
    assert request["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "lookup_pix_key",
                "description": "lookup",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]
    payload = request["messages"]
    assert isinstance(payload, list)
    assistant_calls = [item["tool_calls"][0] for item in payload if item.get("tool_calls")]
    assert [call["id"] for call in assistant_calls] == ["c1", "c2"]
    assert [json.loads(call["function"]["arguments"]) for call in assistant_calls] == [
        {"pix_key": "a@b.com"},
        {"pix_key": "maria@bank.com"},
    ]
    results = [item for item in payload if item["role"] == "tool"]
    assert [item["tool_call_id"] for item in results] == ["c1", "c2"]
    assert results[0]["content"] == '{"error":{"code":"INVALID_ARGUMENT"}}'


def test_openai_omits_tool_controls_when_tools_are_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[dict[str, object]] = []

    def create(**kwargs: object) -> Any:
        requests.append(deepcopy(kwargs))
        return _openai_text_response()

    _install_fake_openai(monkeypatch, create)
    mod = importlib.import_module("agentic_payments_env.adapters.openai_compat")
    model = mod.OpenAICompatChatModel("gpt-test", None, "sk-test")
    turn = model.complete([ChatMessage(role="user", content="hello")], [])
    assert "tools" not in requests[0]
    assert "parallel_tool_calls" not in requests[0]
    assert turn.text == "done"
    assert turn.usage == Usage(input_tokens=3, output_tokens=2)


def test_openai_preserves_multiple_calls_for_agent_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = _openai_ok_response()
    first = response.choices[0].message.tool_calls[0]
    response.choices[0].message.tool_calls = [
        first,
        types.SimpleNamespace(
            id=None,
            function=types.SimpleNamespace(name="finish", arguments="{}"),
        ),
    ]
    _install_fake_openai(monkeypatch, lambda **_kwargs: response)
    mod = importlib.import_module("agentic_payments_env.adapters.openai_compat")
    model = mod.OpenAICompatChatModel("gpt-test", None, "sk-test")
    messages, tools = _sample_inputs()
    turn = model.complete(messages, tools)
    assert [call["id"] for call in turn.tool_calls] == ["call_1", None]


def test_openai_transport_exhaustion_and_nontransport_propagation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}

    def transport_failure(**_kwargs: object) -> Any:
        calls["n"] += 1
        raise sys.modules["openai"].APIConnectionError("down")  # type: ignore[attr-defined]

    _install_fake_openai(monkeypatch, transport_failure)
    mod = importlib.import_module("agentic_payments_env.adapters.openai_compat")
    model = mod.OpenAICompatChatModel("gpt-test", None, "sk-test")
    messages, tools = _sample_inputs()
    with pytest.raises(sys.modules["openai"].APIConnectionError, match="down"):  # type: ignore[attr-defined]
        model.complete(messages, tools)
    assert calls["n"] == 3

    calls["n"] = 0

    def unsupported(**_kwargs: object) -> Any:
        calls["n"] += 1
        raise ValueError("unsupported parameter")

    model._client.chat.completions.create = unsupported
    with pytest.raises(ValueError, match="unsupported parameter"):
        model.complete(messages, tools)
    assert calls["n"] == 1


def test_openai_retries_transport_error_once(monkeypatch: pytest.MonkeyPatch) -> None:
    slept: list[float] = []
    calls = {"n": 0}

    def create(**kwargs: object) -> Any:
        del kwargs
        calls["n"] += 1
        if calls["n"] == 1:
            raise sys.modules["openai"].APIConnectionError("boom")  # type: ignore[attr-defined]
        return _openai_ok_response()

    _install_fake_openai(monkeypatch, create)
    mod = importlib.import_module("agentic_payments_env.adapters.openai_compat")
    model = mod.OpenAICompatChatModel(
        "gpt-test",
        None,
        "sk-test",
        sleep=slept.append,
    )
    messages, tools = _sample_inputs()
    turn = model.complete(messages, tools)
    assert calls["n"] == 2
    assert slept == [0.0]
    assert turn.text == "done"


def test_openai_import_error_names_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "openai", None)
    _purge("agentic_payments_env.adapters.openai_compat")
    with pytest.raises(ImportError, match=r"\[openai\]"):
        importlib.import_module("agentic_payments_env.adapters.openai_compat")


def test_anthropic_complete_maps_tool_use(monkeypatch: pytest.MonkeyPatch) -> None:
    def create(**kwargs: object) -> Any:
        assert kwargs["model"] == "claude-test"
        return _anthropic_ok_response()

    _install_fake_anthropic(monkeypatch, create)
    mod = importlib.import_module("agentic_payments_env.adapters.anthropic")
    model = mod.AnthropicChatModel("claude-test", "sk-ant-test")
    messages, tools = _sample_inputs()
    turn = model.complete(messages, tools)
    assert turn.text == "done"
    assert turn.tool_calls == [
        {"id": "toolu_1", "name": "lookup_pix_key", "arguments": {"pix_key": "a@b.com"}}
    ]
    assert turn.usage == Usage(input_tokens=9, output_tokens=4)


def test_anthropic_requests_serial_tools_and_preserves_multiturn_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[dict[str, object]] = []

    def create(**kwargs: object) -> Any:
        requests.append(deepcopy(kwargs))
        return _anthropic_text_response()

    _install_fake_anthropic(monkeypatch, create)
    mod = importlib.import_module("agentic_payments_env.adapters.anthropic")
    model = mod.AnthropicChatModel("claude-test", "sk-ant-test")
    _, tools = _sample_inputs()
    model.complete(_conversation(), tools)

    request = requests[0]
    assert request["system"] == "system"
    assert request["tool_choice"] == {"type": "auto", "disable_parallel_tool_use": True}
    assert request["tools"] == [
        {
            "name": "lookup_pix_key",
            "description": "lookup",
            "input_schema": {"type": "object", "properties": {}},
        }
    ]
    payload = request["messages"]
    assert isinstance(payload, list)
    tool_uses = [
        block
        for item in payload
        for block in (item["content"] if isinstance(item["content"], list) else [])
        if block["type"] == "tool_use"
    ]
    assert [(block["id"], block["input"]) for block in tool_uses] == [
        ("c1", {"pix_key": "a@b.com"}),
        ("c2", {"pix_key": "maria@bank.com"}),
    ]
    results = [
        block
        for item in payload
        for block in (item["content"] if isinstance(item["content"], list) else [])
        if block["type"] == "tool_result"
    ]
    assert [block["tool_use_id"] for block in results] == ["c1", "c2"]
    assert results[0]["content"] == '{"error":{"code":"INVALID_ARGUMENT"}}'


def test_anthropic_omits_tool_controls_when_tools_are_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[dict[str, object]] = []

    def create(**kwargs: object) -> Any:
        requests.append(deepcopy(kwargs))
        return _anthropic_text_response()

    _install_fake_anthropic(monkeypatch, create)
    mod = importlib.import_module("agentic_payments_env.adapters.anthropic")
    model = mod.AnthropicChatModel("claude-test", "sk-ant-test")
    turn = model.complete([ChatMessage(role="user", content="hello")], [])
    assert "tools" not in requests[0]
    assert "tool_choice" not in requests[0]
    assert turn.text == "done"
    assert turn.usage == Usage(input_tokens=3, output_tokens=2)


def test_anthropic_preserves_multiple_calls_for_agent_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = _anthropic_ok_response()
    response.content.append(
        types.SimpleNamespace(type="tool_use", id=None, name="finish", input={})
    )
    _install_fake_anthropic(monkeypatch, lambda **_kwargs: response)
    mod = importlib.import_module("agentic_payments_env.adapters.anthropic")
    model = mod.AnthropicChatModel("claude-test", "sk-ant-test")
    messages, tools = _sample_inputs()
    turn = model.complete(messages, tools)
    assert [call["id"] for call in turn.tool_calls] == ["toolu_1", None]


def test_anthropic_transport_exhaustion_and_nontransport_propagation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}

    def transport_failure(**_kwargs: object) -> Any:
        calls["n"] += 1
        raise sys.modules["anthropic"].APIConnectionError("down")  # type: ignore[attr-defined]

    _install_fake_anthropic(monkeypatch, transport_failure)
    mod = importlib.import_module("agentic_payments_env.adapters.anthropic")
    model = mod.AnthropicChatModel("claude-test", "sk-ant-test")
    messages, tools = _sample_inputs()
    with pytest.raises(sys.modules["anthropic"].APIConnectionError, match="down"):  # type: ignore[attr-defined]
        model.complete(messages, tools)
    assert calls["n"] == 3

    calls["n"] = 0

    def unsupported(**_kwargs: object) -> Any:
        calls["n"] += 1
        raise ValueError("unsupported parameter")

    model._client.messages.create = unsupported
    with pytest.raises(ValueError, match="unsupported parameter"):
        model.complete(messages, tools)
    assert calls["n"] == 1


def test_anthropic_retries_transport_error_once(monkeypatch: pytest.MonkeyPatch) -> None:
    slept: list[float] = []
    calls = {"n": 0}

    def create(**kwargs: object) -> Any:
        del kwargs
        calls["n"] += 1
        if calls["n"] == 1:
            raise sys.modules["anthropic"].APIConnectionError("boom")  # type: ignore[attr-defined]
        return _anthropic_ok_response()

    _install_fake_anthropic(monkeypatch, create)
    mod = importlib.import_module("agentic_payments_env.adapters.anthropic")
    model = mod.AnthropicChatModel("claude-test", "sk-ant-test", sleep=slept.append)
    messages, tools = _sample_inputs()
    turn = model.complete(messages, tools)
    assert calls["n"] == 2
    assert slept == [0.0]
    assert turn.text == "done"


def test_anthropic_import_error_names_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "anthropic", None)
    _purge("agentic_payments_env.adapters.anthropic")
    with pytest.raises(ImportError, match=r"\[anthropic\]"):
        importlib.import_module("agentic_payments_env.adapters.anthropic")
