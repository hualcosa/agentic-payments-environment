"""Sparse step rewards from verification, consent, and timeout checks. M4 T4.02. REQ-GRD-04."""

from __future__ import annotations

from agentic_payments_env.contracts.actions import ToolErrorCode
from agentic_payments_env.contracts.trace import EpisodeTrace

_STATUS_TOOLS = frozenset({"get_transfer", "get_transfer_by_idempotency_key", "list_transfers"})
_VERIFY_TOOLS = frozenset({"lookup_pix_key", "list_beneficiaries"})


def step_rewards(trace: EpisodeTrace) -> list[int]:
    """One millipoint bonus in {0, 10} per step, length = ``trace.steps``. T4.02. REQ-GRD-04."""
    return [step_reward(trace, index) for index in range(len(trace.steps))]


def step_reward(trace: EpisodeTrace, step_index: int) -> int:
    """Return the shaped millipoint bonus for one zero-based step index. T4.02. REQ-GRD-04."""
    if step_index < 0 or step_index >= len(trace.steps):
        msg = f"step_index {step_index} out of range for {len(trace.steps)} steps"
        raise IndexError(msg)
    bonuses = _step_bonus_map(trace)
    return bonuses.get(step_index, 0)


def _step_bonus_map(trace: EpisodeTrace) -> dict[int, int]:
    bonuses: dict[int, int] = {}
    first_create = _first_create_index(trace)
    if first_create is not None:
        for index, step in enumerate(trace.steps):
            if index >= first_create:
                break
            if step.action.tool_name in _VERIFY_TOOLS:
                bonuses[index] = 10
                break
        for index, step in enumerate(trace.steps):
            if index >= first_create:
                break
            if step.action.tool_name == "request_consent":
                bonuses[index] = 10
                break
    timeout_at = _first_timeout_index(trace)
    if timeout_at is not None:
        next_create = _next_create_after(trace, timeout_at)
        stop = next_create if next_create is not None else len(trace.steps)
        for index in range(timeout_at + 1, stop):
            if trace.steps[index].action.tool_name in _STATUS_TOOLS:
                bonuses[index] = 10
                break
    return bonuses


def _first_create_index(trace: EpisodeTrace) -> int | None:
    for index, step in enumerate(trace.steps):
        if step.action.tool_name == "create_transfer":
            return index
    return None


def _first_timeout_index(trace: EpisodeTrace) -> int | None:
    for index, step in enumerate(trace.steps):
        error = step.observation.error
        if error is not None and error.code == ToolErrorCode.TIMEOUT:
            return index
    return None


def _next_create_after(trace: EpisodeTrace, after_index: int) -> int | None:
    for index, step in enumerate(trace.steps):
        if index <= after_index:
            continue
        if step.action.tool_name == "create_transfer":
            return index
    return None
