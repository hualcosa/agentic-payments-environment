"""Oracle agent that replays a TaskHidden plan. REQ-TASK-06, REQ-CON-10."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from agentic_payments_env.contracts.actions import Action, Observation
from agentic_payments_env.contracts.tasks import OracleStep, TaskHidden, TaskPublic
from agentic_payments_env.contracts.trace import Step
from agentic_payments_env.errors import OraclePlanError

_IDEMPOTENCY = re.compile(r"\$idem:([A-Za-z0-9_.-]+)")
_UNRESOLVED = re.compile(
    r"\$(?:principal_account|last_consent_id|last_transfer_id|"
    r"last_challenge_id|idem:|beneficiary_key:)"
)


class OracleAgent:
    """Replay ``hidden.oracle_plan`` with 07 §6 variable resolution. REQ-TASK-06."""

    name = "oracle"

    def __init__(self, task_hidden: TaskHidden, task_id: str) -> None:
        self._hidden = task_hidden
        self._task_id = task_id
        self._reset: Observation | None = None
        self._cursor = 0

    def reset(self, public: TaskPublic, reset_observation: Observation) -> None:
        del public
        self._reset = reset_observation
        self._cursor = 0

    def act(self, history: Sequence[Step], last_observation: Observation) -> Action:
        del last_observation
        if self._cursor >= len(self._hidden.oracle_plan):
            raise OraclePlanError("oracle plan exhausted before the episode ended")
        planned: OracleStep = self._hidden.oracle_plan[self._cursor]
        self._cursor += 1
        arguments = self._resolve_args(planned.arguments, history)
        return Action(tool_name=planned.tool_name, arguments=arguments)

    def _resolve_args(self, arguments: dict[str, Any], history: Sequence[Step]) -> dict[str, Any]:
        return {key: self._resolve_value(value, history) for key, value in arguments.items()}

    def _resolve_value(self, value: Any, history: Sequence[Step]) -> Any:
        if isinstance(value, str):
            return self._resolve_string(value, history)
        if isinstance(value, dict):
            return {key: self._resolve_value(item, history) for key, item in value.items()}
        if isinstance(value, list):
            return [self._resolve_value(item, history) for item in value]
        return value

    def _resolve_string(self, text: str, history: Sequence[Step]) -> str:
        if text.startswith("$beneficiary_key:"):
            nickname = text[len("$beneficiary_key:") :]
            resolved = self._beneficiary_key(nickname, history)
            return resolved
        mapping = {
            "$principal_account": self._principal_account(),
            "$last_consent_id": self._last_result_field(history, {"request_consent"}, "consent_id"),
            "$last_transfer_id": self._last_transfer_id(history),
            "$last_challenge_id": self._last_result_field(
                history, {"request_step_up_auth"}, "challenge_id"
            ),
        }

        def _idem(match: re.Match[str]) -> str:
            return f"{self._task_id}-{match.group(1)}"

        resolved = _IDEMPOTENCY.sub(_idem, text)
        for placeholder, replacement in mapping.items():
            if placeholder in resolved:
                if replacement is None:
                    raise OraclePlanError(f"unresolvable oracle variable {placeholder}")
                resolved = resolved.replace(placeholder, replacement)
        if _UNRESOLVED.search(resolved):
            raise OraclePlanError(f"unresolvable oracle variable in {text!r}")
        return resolved

    def _principal_account(self) -> str:
        if self._reset is None or self._reset.principal is None:
            raise OraclePlanError("unresolvable $principal_account (no reset observation)")
        account_ids = self._reset.principal.get("account_ids")
        if not isinstance(account_ids, list) or not account_ids:
            raise OraclePlanError("unresolvable $principal_account")
        first = account_ids[0]
        if not isinstance(first, str):
            raise OraclePlanError("unresolvable $principal_account")
        return first

    def _beneficiary_key(self, nickname: str, history: Sequence[Step]) -> str:
        for step in reversed(history):
            obs = step.observation
            if obs.tool_name != "list_beneficiaries" or obs.result is None:
                continue
            rows = obs.result.get("beneficiaries")
            if not isinstance(rows, list):
                continue
            for row in rows:
                if isinstance(row, dict) and row.get("nickname") == nickname:
                    pix_key = row.get("pix_key")
                    if isinstance(pix_key, str):
                        return pix_key
            raise OraclePlanError(f"unresolvable $beneficiary_key:{nickname}")
        raise OraclePlanError(f"unresolvable $beneficiary_key:{nickname}")

    def _last_result_field(
        self, history: Sequence[Step], tool_names: set[str], field: str
    ) -> str | None:
        for step in reversed(history):
            obs = step.observation
            if obs.tool_name not in tool_names or obs.result is None:
                continue
            value = obs.result.get(field)
            return value if isinstance(value, str) else None
        return None

    def _last_transfer_id(self, history: Sequence[Step]) -> str | None:
        for step in reversed(history):
            obs = step.observation
            if obs.result is None:
                continue
            if obs.tool_name in {
                "create_transfer",
                "get_transfer",
                "get_transfer_by_idempotency_key",
            }:
                value = obs.result.get("transfer_id")
                if isinstance(value, str):
                    return value
            if obs.tool_name == "list_transfers":
                transfers = obs.result.get("transfers")
                if isinstance(transfers, list) and transfers:
                    first = transfers[0]
                    if isinstance(first, dict):
                        value = first.get("transfer_id")
                        if isinstance(value, str):
                            return value
        return None
