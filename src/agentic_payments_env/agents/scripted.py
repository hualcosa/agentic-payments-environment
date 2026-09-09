"""Scripted transfer agent used to validate graders. REQ-TEST-01."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from agentic_payments_env.contracts.actions import Action, Observation, ToolErrorCode
from agentic_payments_env.contracts.common import EpisodeOutcome, FrozenModel
from agentic_payments_env.contracts.tasks import TaskPublic


class ScriptedTarget(FrozenModel):
    """One scripted transfer target. REQ-TEST-01."""

    pix_key: str
    amount_centavos: int


class ScriptedAgentConfig(FrozenModel):
    """Configuration for ScriptedAgent presets. REQ-TEST-01."""

    name: str
    targets: list[ScriptedTarget]
    list_beneficiaries: bool = True
    lookup: bool = True
    step_up: bool = False
    consent: bool = True
    idempotency: Literal["stable", "fresh_each_call"] = "stable"
    on_error: Literal[
        "status_check",
        "retry_new_key",
        "retry_same_key",
        "finish_blocked",
        "finish_completed",
    ] = "status_check"
    on_reject: Literal["finish_declined", "finish_completed", "split", "ignore"] = "finish_declined"
    retry_after_denied: bool = False
    split_into: int = 2
    max_retries: int = 3
    finish_outcome: EpisodeOutcome = EpisodeOutcome.COMPLETED
    report_template: str = "Done. Transfers: {transfer_ids}"
    immediate_finish: EpisodeOutcome | None = None


class ScriptedAgent:
    """Configurable transfer agent that does not read the instruction. REQ-TEST-01."""

    def __init__(self, config: ScriptedAgentConfig) -> None:
        self._config = config
        self.name = config.name
        self._account_id = ""
        self._listed = False
        self._targets: list[ScriptedTarget] = list(config.targets)
        self._index = 0
        self._looked_up: set[int] = set()
        self._stepped_up = False
        self._consent_id: str | None = None
        self._consent_done: set[int] = set()
        self._denied_scopes: set[tuple[str, int]] = set()
        self._granted_scopes: set[tuple[str, int]] = set()
        self._create_calls = 0
        self._fresh_n = 0
        self._retries = 0
        self._awaiting: str | None = None
        self._status_pending_key: str | None = None
        self._transfer_ids: list[str] = []
        self._force_create_denied = False
        self._split_done = False

    def reset(self, public: TaskPublic, reset_observation: Observation) -> None:
        """Initialize scripted state from the reset observation. REQ-TEST-01."""
        del public
        principal = reset_observation.principal or {}
        ids = principal.get("account_ids") or []
        self._account_id = str(ids[0]) if ids else ""
        self._listed = False
        self._targets = list(self._config.targets)
        self._index = 0
        self._looked_up = set()
        self._stepped_up = False
        self._consent_id = None
        self._consent_done = set()
        self._denied_scopes = set()
        self._granted_scopes = set()
        self._create_calls = 0
        self._fresh_n = 0
        self._retries = 0
        self._awaiting = None
        self._status_pending_key = None
        self._transfer_ids = []
        self._force_create_denied = False
        self._split_done = False

    def _idem(self, target_index: int) -> str:
        if self._config.idempotency == "fresh_each_call":
            self._fresh_n += 1
            return f"fresh-{target_index}-{self._fresh_n}"
        suffix = 0 if self._config.on_error != "retry_new_key" else self._retries
        if self._config.on_error == "retry_new_key":
            return f"sk-{target_index}-{self._retries}"
        return f"sk-{target_index}-{suffix}"

    def _finish(self, outcome: EpisodeOutcome, extra: str = "") -> Action:
        ids = ",".join(self._transfer_ids)
        report = self._config.report_template.format(transfer_ids=ids) + extra
        return Action(tool_name="finish", arguments={"outcome": outcome.value, "report": report})

    def _next_target_action(self) -> Action:
        if self._index >= len(self._targets):
            return self._finish(self._config.finish_outcome)
        target = self._targets[self._index]
        if self._config.lookup and self._index not in self._looked_up:
            self._awaiting = "lookup"
            return Action(tool_name="lookup_pix_key", arguments={"pix_key": target.pix_key})
        if self._config.step_up and not self._stepped_up:
            self._awaiting = "step_up"
            return Action(tool_name="request_step_up_auth", arguments={})
        if self._config.consent and self._index not in self._consent_done:
            self._awaiting = "consent"
            return Action(
                tool_name="request_consent",
                arguments={
                    "from_account_id": self._account_id,
                    "pix_key": target.pix_key,
                    "amount_centavos": target.amount_centavos,
                    "description": f"scripted {target.amount_centavos}",
                },
            )
        self._awaiting = "create"
        self._create_calls += 1
        key = self._idem(self._index)
        self._status_pending_key = key
        args: dict[str, object] = {
            "from_account_id": self._account_id,
            "pix_key": target.pix_key,
            "amount_centavos": target.amount_centavos,
            "idempotency_key": key,
        }
        if self._consent_id is not None:
            args["consent_id"] = self._consent_id
        return Action(tool_name="create_transfer", arguments=args)

    def _handle_reject(self) -> Action:
        mode = self._config.on_reject
        if mode == "finish_declined":
            return self._finish(EpisodeOutcome.DECLINED, extra=" Rejected.")
        if mode == "finish_completed":
            return self._finish(EpisodeOutcome.COMPLETED)
        if mode == "split":
            if self._split_done:
                return self._finish(self._config.finish_outcome)
            self._split_done = True
            target = self._targets[self._index]
            parts = max(self._config.split_into, 2)
            base = target.amount_centavos // parts
            rem = target.amount_centavos - base * parts
            replacements = [
                ScriptedTarget(
                    pix_key=target.pix_key, amount_centavos=base + (rem if i == 0 else 0)
                )
                for i in range(parts)
                if base + (rem if i == 0 else 0) > 0
            ]
            self._targets = (
                self._targets[: self._index] + replacements + self._targets[self._index + 1 :]
            )
            self._looked_up.discard(self._index)
            self._consent_done.discard(self._index)
            self._consent_id = None
            return self._next_target_action()
        self._index += 1
        self._consent_id = None
        return self._next_target_action()

    def _handle_error(self, last: Observation) -> Action:
        error = last.error
        if error is None:
            return self._next_target_action()
        transient = error.code in {ToolErrorCode.TIMEOUT, ToolErrorCode.SERVICE_UNAVAILABLE}
        if transient:
            mode = self._config.on_error
            if mode == "finish_blocked":
                return self._finish(EpisodeOutcome.BLOCKED)
            if mode == "finish_completed":
                return self._finish(EpisodeOutcome.COMPLETED)
            if mode == "status_check":
                self._awaiting = "status"
                return Action(
                    tool_name="get_transfer_by_idempotency_key",
                    arguments={"idempotency_key": self._status_pending_key or ""},
                )
            if self._retries >= self._config.max_retries:
                return self._finish(EpisodeOutcome.BLOCKED)
            self._retries += 1
            if mode == "retry_new_key":
                self._consent_done.discard(self._index)
                self._consent_id = None
                return self._next_target_action()
            return self._next_target_action()
        if (
            self._config.retry_after_denied
            and not self._force_create_denied
            and error.code
            in {
                ToolErrorCode.CONSENT_REQUIRED,
                ToolErrorCode.CONSENT_INVALID,
                ToolErrorCode.POLICY_VIOLATION,
            }
        ):
            pass
        return self._handle_reject()

    def act(self, history: Sequence[object], last_observation: Observation) -> Action:
        """Return the next scripted tool action. REQ-TEST-01."""
        del history
        cfg = self._config
        if cfg.immediate_finish is not None and last_observation.kind == "reset":
            return self._finish(cfg.immediate_finish)
        if last_observation.kind == "reset":
            if cfg.list_beneficiaries and not self._listed:
                self._awaiting = "list"
                return Action(tool_name="list_beneficiaries", arguments={})
            return self._next_target_action()

        awaiting = self._awaiting
        result = last_observation.result or {}
        if last_observation.kind == "tool_error":
            if awaiting == "create":
                if (
                    cfg.retry_after_denied
                    and last_observation.error is not None
                    and last_observation.error.code
                    in {ToolErrorCode.CONSENT_INVALID, ToolErrorCode.CONSENT_REQUIRED}
                ):
                    return self._handle_reject()
                return self._handle_error(last_observation)
            if awaiting == "status":
                self._retries += 1
                if cfg.on_error == "retry_new_key":
                    return self._next_target_action()
                return self._next_target_action()
            return self._handle_reject()

        if awaiting == "list":
            self._listed = True
            return self._next_target_action()
        if awaiting == "lookup":
            self._looked_up.add(self._index)
            return self._next_target_action()
        if awaiting == "step_up":
            self._stepped_up = True
            status = result.get("status")
            if status == "DENIED":
                return self._handle_reject()
            return self._next_target_action()
        if awaiting == "consent":
            self._consent_done.add(self._index)
            status = result.get("status")
            cid = result.get("consent_id")
            target = self._targets[self._index]
            scope = (target.pix_key, target.amount_centavos)
            if status == "DENIED":
                self._denied_scopes.add(scope)
                if isinstance(cid, str):
                    self._consent_id = cid
                if cfg.retry_after_denied:
                    self._force_create_denied = True
                    self._awaiting = "create"
                    key = self._idem(self._index)
                    return Action(
                        tool_name="create_transfer",
                        arguments={
                            "from_account_id": self._account_id,
                            "pix_key": target.pix_key,
                            "amount_centavos": target.amount_centavos,
                            "idempotency_key": key,
                            "consent_id": cid,
                        },
                    )
                return self._handle_reject()
            if status == "GRANTED" and isinstance(cid, str):
                self._consent_id = cid
                self._granted_scopes.add(scope)
            return self._next_target_action()
        if awaiting == "create":
            tid = result.get("transfer_id")
            if isinstance(tid, str):
                self._transfer_ids.append(tid)
            self._index += 1
            self._consent_id = None
            self._retries = 0
            return self._next_target_action()
        if awaiting == "status":
            status = result.get("status")
            tid = result.get("transfer_id")
            if status == "COMPLETED":
                if isinstance(tid, str):
                    self._transfer_ids.append(tid)
                self._index += 1
                self._retries = 0
                return self._next_target_action()
            self._retries += 1
            return self._next_target_action()
        return self._finish(cfg.finish_outcome)
