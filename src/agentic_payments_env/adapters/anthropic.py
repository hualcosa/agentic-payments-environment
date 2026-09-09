"""Anthropic Messages API adapter with tools.

Satisfies: M1 T1.02. Optional extra ``[anthropic]``; not imported by the core package.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

try:
    from anthropic import Anthropic, APIConnectionError, APITimeoutError
except ImportError as exc:
    raise ImportError(
        "Install the [anthropic] extra: pip install 'agentic-payments-env[anthropic]'"
    ) from exc

from agentic_payments_env.adapters.base import ChatMessage, ModelTurn, ToolSpec, Usage

_TRANSPORT = (APIConnectionError, APITimeoutError, TimeoutError, OSError)
_MAX_ATTEMPTS = 3


def _noop_sleep(_seconds: float) -> None:
    return None


class AnthropicChatModel:
    """ChatModel over Anthropic Messages. REQ-ENV-16."""

    def __init__(
        self,
        model_id: str,
        api_key: str,
        *,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self.model_id = model_id
        self._client = Anthropic(api_key=api_key)
        self._sleep = sleep if sleep is not None else _noop_sleep

    def complete(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolSpec],
    ) -> ModelTurn:
        """Call Anthropic Messages with tools. REQ-ENV-16."""
        system, payload_messages = _to_anthropic_messages(messages)
        payload_tools = [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
            }
            for t in tools
        ]

        def _call() -> Any:
            kwargs: dict[str, Any] = {
                "model": self.model_id,
                "max_tokens": 4096,
                "messages": payload_messages,
            }
            if system:
                kwargs["system"] = system
            if payload_tools:
                kwargs["tools"] = payload_tools
                kwargs["tool_choice"] = {"type": "auto", "disable_parallel_tool_use": True}
            return self._client.messages.create(**kwargs)

        response = _retry_transport(_call, sleep=self._sleep)
        return _parse_anthropic_turn(response)


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


def _to_anthropic_messages(
    messages: Sequence[ChatMessage],
) -> tuple[str, list[dict[str, Any]]]:
    system_parts: list[str] = []
    out: list[dict[str, Any]] = []
    for message in messages:
        if message.role == "system":
            if message.content:
                system_parts.append(message.content)
            continue
        if message.role == "tool":
            out.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": message.tool_call_id or "",
                            "content": message.content or "",
                        }
                    ],
                }
            )
            continue
        if message.role == "assistant" and message.tool_calls:
            blocks: list[dict[str, Any]] = []
            if message.content:
                blocks.append({"type": "text", "text": message.content})
            for call in message.tool_calls:
                args = call.get("arguments", {})
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": call.get("id"),
                        "name": call.get("name"),
                        "input": args if isinstance(args, dict) else {},
                    }
                )
            out.append({"role": "assistant", "content": blocks})
            continue
        out.append({"role": message.role, "content": message.content or ""})
    return "\n\n".join(system_parts), out


def _parse_anthropic_turn(response: Any) -> ModelTurn:
    text_parts: list[str] = []
    tool_calls: list[dict[str, object]] = []
    for block in response.content:
        kind = getattr(block, "type", None)
        if kind == "text":
            text_parts.append(block.text)
        elif kind == "tool_use":
            raw_input = getattr(block, "input", {}) or {}
            arguments = (
                {str(k): v for k, v in raw_input.items()} if isinstance(raw_input, dict) else {}
            )
            tool_calls.append({"id": block.id, "name": block.name, "arguments": arguments})
    usage_obj = getattr(response, "usage", None)
    input_tokens = int(getattr(usage_obj, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage_obj, "output_tokens", 0) or 0)
    return ModelTurn(
        tool_calls=tool_calls,
        text="".join(text_parts),
        usage=Usage(input_tokens=input_tokens, output_tokens=output_tokens),
    )
