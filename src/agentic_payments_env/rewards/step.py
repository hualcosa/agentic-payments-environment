"""Sparse step rewards from verification, consent, and timeout checks. M4 T4.02."""

from __future__ import annotations

from agentic_payments_env.contracts.actions import ToolErrorCode
from agentic_payments_env.contracts.trace import EpisodeTrace

_STATUS_TOOLS = frozenset({"get_transfer", "get_transfer_by_idempotency_key", "list_transfers"})
_VERIFY_TOOLS = frozenset({"lookup_pix_key", "list_beneficiaries"})


def step_rewards(trace: EpisodeTrace) -> list[int]:
    """One millipoint bonus in {0, 10, 20, 30} per step, length = steps. T4.02."""
    rewards = [0 for _ in trace.steps]
    first_create: int | None = None
    for index, step in enumerate(trace.steps):
        if step.action.tool_name == "create_transfer" and first_create is None:
            first_create = index
    if first_create is not None:
        for index, step in enumerate(trace.steps):
            if index >= first_create:
                break
            if step.action.tool_name in _VERIFY_TOOLS:
                rewards[index] += 10
                break
        for index, step in enumerate(trace.steps):
            if index >= first_create:
                break
            if step.action.tool_name == "request_consent":
                rewards[index] += 10
                break
    timeout_at: int | None = None
    for index, step in enumerate(trace.steps):
        error = step.observation.error
        if error is not None and error.code == ToolErrorCode.TIMEOUT:
            timeout_at = index
            break
    if timeout_at is not None:
        next_create: int | None = None
        for index, step in enumerate(trace.steps):
            if index <= timeout_at:
                continue
            if step.action.tool_name == "create_transfer":
                next_create = index
                break
        stop = next_create if next_create is not None else len(trace.steps)
        for index in range(timeout_at + 1, stop):
            if trace.steps[index].action.tool_name in _STATUS_TOOLS:
                rewards[index] += 10
                break
    return rewards
