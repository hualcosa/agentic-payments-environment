"""Tests for optional OpenAI and Anthropic adapters. T1.02."""

from __future__ import annotations

import importlib
import sys
import types
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
