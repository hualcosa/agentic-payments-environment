"""ChatModel protocol and an in-memory FakeChatModel for tests.

Satisfies: M1 T1.01; agents consume TaskPublic and Observations only (REQ-CON-10).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from agentic_payments_env.contracts.common import FrozenModel


class ChatMessage(FrozenModel):
    """One chat message in a provider-agnostic transcript. REQ-CON-10."""

    role: str
    content: str | None = None
    tool_call_id: str | None = None
    name: str | None = None
    tool_calls: list[dict[str, object]] | None = None


class ToolSpec(FrozenModel):
    """JSON-Schema tool definition passed to a chat model. REQ-CON-10."""

    name: str
    description: str
    parameters: dict[str, object]


class Usage(FrozenModel):
    """Token usage for one model turn. Defaults to zeros when unknown. REQ-CON-10."""

    input_tokens: int = 0
    output_tokens: int = 0


class ModelTurn(FrozenModel):
    """One model response: tool calls and/or text, plus usage. REQ-CON-10.

    Each item in ``tool_calls`` is a dict with keys ``id``, ``name``, and
    ``arguments`` (a JSON object, not a string).
    """

    tool_calls: list[dict[str, object]]
    text: str
    usage: Usage = Usage()


class NormalizedModelTurn(FrozenModel):
    """Provider-agnostic record of one LLM completion. REQ-CON-10."""

    model_id: str
    text: str
    tool_calls: list[dict[str, object]]
    usage: Usage = Usage()
    parsed_tool_name: str
    parsed_arguments: dict[str, object]


class ModelTurnLog(FrozenModel):
    """Sidecar log written beside ``meta.json``. REQ-CON-10."""

    schema_version: str = "0.1"
    model_id: str
    prompt_id: str | None = None
    turns: list[NormalizedModelTurn]


class ChatModel(Protocol):
    """Minimal chat-completions surface used by LLMAgent. REQ-ENV-16."""

    model_id: str

    def complete(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolSpec],
    ) -> ModelTurn: ...


class FakeChatModel:
    """Scripted ChatModel: returns queued turns, no network. REQ-ENV-16."""

    def __init__(
        self,
        turns: Sequence[ModelTurn],
        model_id: str = "fake",
    ) -> None:
        self.model_id = model_id
        self._turns: list[ModelTurn] = list(turns)
        self._index = 0

    def complete(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolSpec],
    ) -> ModelTurn:
        """Return the next scripted turn. REQ-ENV-16."""
        del messages, tools
        if self._index >= len(self._turns):
            raise IndexError("FakeChatModel has no remaining scripted turns")
        turn = self._turns[self._index]
        self._index += 1
        return turn
