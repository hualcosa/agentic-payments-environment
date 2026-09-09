"""Tool dispatch, observation builders, and audit for tool results.

Satisfies: REQ-TOOL-02, REQ-TOOL-03, REQ-TOOL-04, REQ-TOOL-05, REQ-TOOL-17.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ValidationError

from agentic_payments_env.contracts.actions import (
    Action,
    Observation,
    PolicyWarning,
    ToolError,
    ToolErrorCode,
)
from agentic_payments_env.contracts.common import ActorKind
from agentic_payments_env.contracts.tasks import FaultInjection
from agentic_payments_env.simulated_user import SimulatedUser
from agentic_payments_env.tools.schemas import ARGS_MODELS
from agentic_payments_env.world import WorldState


@dataclass
class ToolContext:
    """Per-call context passed to every tool handler."""

    state: WorldState
    sim_user: SimulatedUser
    step_index: int
    task_id: str
    done: bool = False


Handler = Callable[[ToolContext, BaseModel, FaultInjection | None], Observation]


def _load_handlers() -> dict[str, Handler]:
    handlers: dict[str, Handler] = {}
    for module_name in ("read", "authorize", "transfer", "misc"):
        try:
            module = importlib.import_module(f"agentic_payments_env.tools.{module_name}")
        except ImportError:
            continue
        handlers.update(module.HANDLERS)
    return handlers


def ok(
    ctx: ToolContext,
    tool: str,
    result: dict[str, Any],
    warnings: list[PolicyWarning] | None = None,
    observed_at: datetime | None = None,
    kind: str = "tool_result",
    *,
    record_tool_result: bool = True,
) -> Observation:
    """Build a success observation and emit TOOL_RESULT. REQ-TOOL-05."""
    if record_tool_result:
        ctx.state.emit(
            step_index=ctx.step_index,
            actor=ActorKind.SYSTEM,
            kind="TOOL_RESULT",
            payload={"tool_name": tool},
        )
    observed = observed_at if observed_at is not None else ctx.state.now
    return Observation(
        step_index=ctx.step_index,
        sim_time=ctx.state.now,
        kind=kind,
        tool_name=tool,
        result=result,
        warnings=list(warnings or []),
        observed_at=observed,
    )


def err(
    ctx: ToolContext,
    tool: str,
    code: ToolErrorCode,
    message: str,
    details: dict[str, Any] | None = None,
) -> Observation:
    """Build an error observation and emit TOOL_ERROR. REQ-TOOL-05."""
    error = ToolError(code=code, message=message, details=dict(details or {}))
    ctx.state.emit(
        step_index=ctx.step_index,
        actor=ActorKind.SYSTEM,
        kind="TOOL_ERROR",
        payload={"code": code.value, "message": message},
    )
    return Observation(
        step_index=ctx.step_index,
        sim_time=ctx.state.now,
        kind="tool_error",
        tool_name=tool,
        error=error,
        observed_at=ctx.state.now,
    )


def _pydantic_summary(exc: ValidationError) -> str:
    parts: list[str] = []
    for item in exc.errors():
        loc = ".".join(str(part) for part in item.get("loc", ()))
        parts.append(
            f"{loc}: {item.get('msg', 'invalid')}" if loc else str(item.get("msg", "invalid"))
        )
    return "; ".join(parts) if parts else str(exc)


def dispatch(ctx: ToolContext, action: Action, fault: FaultInjection | None) -> Observation:
    """Validate, apply faults, and route to a handler. REQ-TOOL-02, REQ-TOOL-03, REQ-TOOL-04."""
    if ctx.done:
        return err(
            ctx, action.tool_name, ToolErrorCode.EPISODE_FINISHED, "episode already finished"
        )
    model = ARGS_MODELS.get(action.tool_name)
    if model is None:
        return err(
            ctx, action.tool_name, ToolErrorCode.UNKNOWN_TOOL, f"unknown tool {action.tool_name!r}"
        )
    if fault is not None and fault.kind.value in {
        "SERVICE_UNAVAILABLE",
        "TIMEOUT_BEFORE_EXECUTE",
    }:
        ctx.state.emit(
            step_index=ctx.step_index,
            actor=ActorKind.SYSTEM,
            kind="FAULT_INJECTED",
            payload={"fault_kind": fault.kind.value, "tool_name": action.tool_name},
            visible_to_agent=False,
        )
        if fault.kind.value == "SERVICE_UNAVAILABLE":
            return err(
                ctx,
                action.tool_name,
                ToolErrorCode.SERVICE_UNAVAILABLE,
                "service unavailable",
            )
        return err(ctx, action.tool_name, ToolErrorCode.TIMEOUT, "request timed out")
    try:
        args = model.model_validate(action.arguments)
    except ValidationError as exc:
        return err(ctx, action.tool_name, ToolErrorCode.INVALID_ARGUMENT, _pydantic_summary(exc))
    if fault is not None:
        ctx.state.emit(
            step_index=ctx.step_index,
            actor=ActorKind.SYSTEM,
            kind="FAULT_INJECTED",
            payload={"fault_kind": fault.kind.value, "tool_name": action.tool_name},
            visible_to_agent=False,
        )
    handlers = _load_handlers()
    handler = handlers.get(action.tool_name)
    if handler is None:
        return err(
            ctx, action.tool_name, ToolErrorCode.UNKNOWN_TOOL, f"unknown tool {action.tool_name!r}"
        )
    return handler(ctx, args, fault)
