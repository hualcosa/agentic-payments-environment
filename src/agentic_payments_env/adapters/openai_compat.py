"""OpenAI-compatible chat-completions adapter (OpenAI, OpenRouter, vLLM, Ollama).

Satisfies: M1 T1.02. Optional extra ``[openai]``; not imported by the core package.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from typing import Any

try:
    from openai import APIConnectionError, APITimeoutError, OpenAI
except ImportError as exc:
    raise ImportError(
        "Install the [openai] extra: pip install 'agentic-payments-env[openai]'"
    ) from exc

from agentic_payments_env.adapters.base import ChatMessage, ModelTurn, ToolSpec, Usage

_TRANSPORT = (APIConnectionError, APITimeoutError, TimeoutError, OSError)
_MAX_ATTEMPTS = 3


def _noop_sleep(_seconds: float) -> None:
    return None


class OpenAICompatChatModel:
    """ChatModel over an OpenAI-compatible Chat Completions API. T1.02."""

    def __init__(
        self,
        model_id: str,
        base_url: str | None,
        api_key: str,
        *,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self.model_id = model_id
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url is not None:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)
        self._sleep = sleep if sleep is not None else _noop_sleep

    def complete(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolSpec],
    ) -> ModelTurn:
        payload_messages = _to_openai_messages(messages)
        payload_tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]

        def _call() -> Any:
            kwargs: dict[str, Any] = {
                "model": self.model_id,
                "messages": payload_messages,
            }
            if payload_tools:
                kwargs["tools"] = payload_tools
            return self._client.chat.completions.create(**kwargs)

        response = _retry_transport(_call, sleep=self._sleep)
        return _parse_openai_turn(response)


def _retry_transport(fn: Callable[[], Any], *, sleep: Callable[[float], None]) -> Any:
    last: BaseException | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            return fn()
        except _TRANSPORT as exc:
            last = exc
            if attempt >= _MAX_ATTEMPTS - 1:
                raise
            sleep(0.0)
    assert last is not None
    raise last


def _to_openai_messages(messages: Sequence[ChatMessage]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for message in messages:
        item: dict[str, Any] = {"role": message.role}
        if message.content is not None:
            item["content"] = message.content
        if message.tool_call_id is not None:
            item["tool_call_id"] = message.tool_call_id
        if message.name is not None:
            item["name"] = message.name
        if message.tool_calls:
            item["tool_calls"] = [
                {
                    "id": call.get("id"),
                    "type": "function",
                    "function": {
                        "name": call.get("name"),
                        "arguments": json.dumps(call.get("arguments", {})),
                    },
                }
                for call in message.tool_calls
            ]
        out.append(item)
    return out


def _parse_arguments(raw: object) -> dict[str, object]:
    if isinstance(raw, dict):
        return {str(k): v for k, v in raw.items()}
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return {str(k): v for k, v in parsed.items()}
    return {}


def _parse_openai_turn(response: Any) -> ModelTurn:
    message = response.choices[0].message
    text = message.content or ""
    tool_calls: list[dict[str, object]] = []
    for call in getattr(message, "tool_calls", None) or []:
        function = call.function
        tool_calls.append(
            {
                "id": call.id,
                "name": function.name,
                "arguments": _parse_arguments(function.arguments),
            }
        )
    usage_obj = getattr(response, "usage", None)
    input_tokens = int(getattr(usage_obj, "prompt_tokens", 0) or 0)
    output_tokens = int(getattr(usage_obj, "completion_tokens", 0) or 0)
    return ModelTurn(
        tool_calls=tool_calls,
        text=text,
        usage=Usage(input_tokens=input_tokens, output_tokens=output_tokens),
    )
