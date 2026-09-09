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
        self.usage_log: list[Usage] = []
        self.turn_log: list[NormalizedModelTurn] = []

    def reset(self, public: TaskPublic, reset_observation: Observation) -> None:
        del reset_observation
        self._public = public
        self._pending_tool_call_id = None
        self.usage_log = []
        self.turn_log = []
        self._messages = [
            ChatMessage(role="system", content=self.system_prompt),
            ChatMessage(role="user", content=public.instruction),
        ]

    def act(self, history: Sequence[Step], last_observation: Observation) -> Action:
        if self._public is None:
            raise RuntimeError("LLMAgent.reset must be called before act")
        self._messages.append(self._observation_message(last_observation))
        if len(history) == self._public.max_steps - 1:
            self._pending_tool_call_id = None
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
        turn = self.model.complete(self._messages, _chat_tools())
        self.usage_log.append(turn.usage)
        self._messages.append(_assistant_message(turn))
        action = self._action_from_turn(turn)
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

    def _record_turn(self, turn: ModelTurn, action: Action) -> None:
        self.turn_log.append(
            NormalizedModelTurn(
                model_id=self.model.model_id,
                text=turn.text,
                tool_calls=list(turn.tool_calls),
                usage=turn.usage,
                parsed_tool_name=action.tool_name,
                parsed_arguments=dict(action.arguments),
            )
        )

    def _action_from_turn(self, turn: ModelTurn) -> Action:
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
        call = turn.tool_calls[0]
        name_obj = call.get("name")
        name = name_obj if isinstance(name_obj, str) and name_obj else "unknown"
        raw_id = call.get("id")
        self._pending_tool_call_id = raw_id if isinstance(raw_id, str) else None
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
