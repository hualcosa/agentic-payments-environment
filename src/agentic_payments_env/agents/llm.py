"""LLM agent: ChatModel turns to environment Actions. REQ-TOOL-08, REQ-CON-10."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from agentic_payments_env.adapters.base import (
    ChatMessage,
    ChatModel,
    ModelTurn,
    NormalizedModelTurn,
    Usage,
)
from agentic_payments_env.adapters.base import ToolSpec as ChatToolSpec
from agentic_payments_env.contracts.actions import Action, Observation
from agentic_payments_env.contracts.common import EpisodeOutcome
from agentic_payments_env.contracts.tasks import TaskPublic
from agentic_payments_env.contracts.trace import Step
from agentic_payments_env.tools.specs import TOOL_SPECS

_RATIONALE_MAX = 4000
_REPORT_MAX = 2000
_FORCED_FINISH = "forced finish: max_steps"

# D-27: tools that never change world state. Only these may share a model turn.
READ_ONLY_TOOLS: frozenset[str] = frozenset(
    {
        "get_customer_profile",
        "get_account_balance",
        "list_beneficiaries",
        "lookup_pix_key",
        "check_transfer_policy",
        "get_transfer",
        "get_transfer_by_idempotency_key",
        "list_transfers",
    }
)


class LLMAgentProtocolError(RuntimeError):
    """Reject model turns that cannot map to one correlated Action. REQ-CON-10."""


class LLMAgent:
    """Drive tools via a ChatModel; never receives TaskHidden. REQ-CON-10, REQ-TOOL-08."""

    name = "llm"

    def __init__(self, model: ChatModel, system_prompt: str, prompt_id: str) -> None:
        self.model = model
        self.system_prompt = system_prompt
        self.prompt_id = prompt_id
        self._public: TaskPublic | None = None
        self._messages: list[ChatMessage] = []
        self._pending_tool_call_id: str | None = None
        self._queue: list[tuple[str, Action]] = []
        self._protocol_error: str | None = None
        self._provider_error: str | None = None
        self.usage_log: list[Usage] = []
        self.turn_log: list[NormalizedModelTurn] = []

    @property
    def protocol_error(self) -> str | None:
        """Expose a safe rejection reason for episode metadata. REQ-ENV-17."""
        return self._protocol_error

    @property
    def provider_error(self) -> str | None:
        """Safe reason when the model call itself failed (not agent behavior). D-26."""
        return self._provider_error

    def reset(self, public: TaskPublic, reset_observation: Observation) -> None:
        del reset_observation
        self._public = public
        self._pending_tool_call_id = None
        self._queue = []
        self._protocol_error = None
        self._provider_error = None
        self.usage_log = []
        self.turn_log = []
        self._messages = [
            ChatMessage(role="system", content=self.system_prompt),
            ChatMessage(role="user", content=public.instruction),
        ]

    def act(self, history: Sequence[Step], last_observation: Observation) -> Action:
        if self._public is None:
            raise RuntimeError("LLMAgent.reset must be called before act")
        if self._protocol_error is not None:
            raise LLMAgentProtocolError(self._protocol_error)
        self._messages.append(self._observation_message(last_observation))
        if len(history) == self._public.max_steps - 1:
            self._pending_tool_call_id = None
            self._queue = []
            self.usage_log.append(Usage())
            forced = Action(
                tool_name="finish",
                arguments={
                    "outcome": EpisodeOutcome.DECLINED.value,
                    "report": _FORCED_FINISH,
                },
                rationale=_FORCED_FINISH,
            )
            self._record_turn(
                ModelTurn(tool_calls=[], text=_FORCED_FINISH, usage=Usage()),
                forced,
            )
            return forced
        if self._queue:
            # D-27: drain an accepted read-only batch before the next model request.
            tool_call_id, queued = self._queue.pop(0)
            self._pending_tool_call_id = tool_call_id
            self.usage_log.append(Usage())
            return queued
        try:
            turn = self.model.complete(self._messages, _chat_tools())
        except Exception as exc:
            # Exception type only: messages may echo request content or endpoints.
            self._provider_error = f"PROVIDER_ERROR type={type(exc).__name__}"
            raise
        self.usage_log.append(turn.usage)
        try:
            tool_call_ids = _validate_turn(turn)
        except LLMAgentProtocolError as exc:
            self._protocol_error = str(exc)
            self._record_turn(turn, None)
            raise
        self._messages.append(_assistant_message(turn))
        action = self._action_from_turn(turn, tool_call_ids[0] if tool_call_ids else None)
        for tool_call_id, call in zip(tool_call_ids[1:], turn.tool_calls[1:], strict=True):
            self._queue.append((tool_call_id, _call_action(call, rationale=None)))
        self._record_turn(turn, action)
        return action

    def _observation_message(self, observation: Observation) -> ChatMessage:
        payload = _drop_none(observation.model_dump(mode="json"))
        content = json.dumps(payload, separators=(",", ":"))
        if self._pending_tool_call_id is not None:
            tool_call_id = self._pending_tool_call_id
            self._pending_tool_call_id = None
            return ChatMessage(
                role="tool",
                content=content,
                tool_call_id=tool_call_id,
                name=observation.tool_name,
            )
        return ChatMessage(role="user", content=content)

    def _record_turn(self, turn: ModelTurn, action: Action | None) -> None:
        """Append a normalized, SDK-free record of one completion. REQ-CON-10."""
        self.turn_log.append(
            NormalizedModelTurn(
                model_id=self.model.model_id,
                served_model=turn.served_model,
                text=turn.text,
                tool_calls=list(turn.tool_calls),
                usage=turn.usage,
                parsed_tool_name=action.tool_name if action is not None else None,
                parsed_arguments=dict(action.arguments) if action is not None else {},
                protocol_error=self._protocol_error if action is None else None,
            )
        )

    def _action_from_turn(self, turn: ModelTurn, tool_call_id: str | None) -> Action:
        rationale = turn.text[:_RATIONALE_MAX]
        if not turn.tool_calls:
            self._pending_tool_call_id = None
            return Action(
                tool_name="finish",
                arguments={
                    "outcome": EpisodeOutcome.DECLINED.value,
                    "report": turn.text[:_REPORT_MAX],
                },
                rationale=rationale,
            )
        self._pending_tool_call_id = tool_call_id
        return _call_action(turn.tool_calls[0], rationale=rationale)


def _call_action(call: dict[str, object], *, rationale: str | None) -> Action:
    name_obj = call.get("name")
    name = name_obj if isinstance(name_obj, str) and name_obj else "unknown"
    return Action(
        tool_name=name,
        arguments=_parse_arguments(call.get("arguments")),
        rationale=rationale,
    )


def _chat_tools() -> list[ChatToolSpec]:
    return [
        ChatToolSpec(name=spec.name, description=spec.description, parameters=spec.args_schema)
        for spec in TOOL_SPECS.values()
    ]


def _assistant_message(turn: ModelTurn) -> ChatMessage:
    tool_calls = turn.tool_calls or None
    return ChatMessage(
        role="assistant",
        content=turn.text or None,
        tool_calls=tool_calls,
    )


def _validate_turn(turn: ModelTurn) -> list[str]:
    """Validate the correlation contract; batches must be read-only. REQ-CON-10, D-27."""
    calls = turn.tool_calls
    if len(calls) > 1 and any(call.get("name") not in READ_ONLY_TOOLS for call in calls):
        raise LLMAgentProtocolError(f"LLM_PROTOCOL_MULTIPLE_TOOL_CALLS count={len(calls)}")
    ids: list[str] = []
    for call in calls:
        raw_id = call.get("id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            type_name = type(raw_id).__name__
            raise LLMAgentProtocolError(f"LLM_PROTOCOL_INVALID_TOOL_CALL_ID type={type_name}")
        if raw_id in ids:
            raise LLMAgentProtocolError(f"LLM_PROTOCOL_DUPLICATE_TOOL_CALL_ID count={len(calls)}")
        ids.append(raw_id)
    return ids


def _drop_none(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def _parse_arguments(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return dict(parsed)
    return {}
