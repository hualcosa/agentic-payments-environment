"""Misc tools: add_beneficiary, ask_user, finish. REQ-TOOL-04, REQ-TOOL-06, REQ-TOOL-13."""

from __future__ import annotations

from agentic_payments_env.contracts.actions import Observation, ToolErrorCode
from agentic_payments_env.contracts.common import ActorKind
from agentic_payments_env.contracts.domain import Beneficiary
from agentic_payments_env.contracts.tasks import FaultInjection
from agentic_payments_env.tools.dispatch import ToolContext, err, ok
from agentic_payments_env.tools.schemas import AddBeneficiaryArgs, AskUserArgs, FinishArgs


def handle_add_beneficiary(
    ctx: ToolContext, args: AddBeneficiaryArgs, fault: FaultInjection | None
) -> Observation:
    del fault
    if args.pix_key not in ctx.state.pix_directory:
        return err(ctx, "add_beneficiary", ToolErrorCode.NOT_FOUND, "pix key not found")
    for ben in ctx.state.beneficiaries.values():
        if ben.customer_id == ctx.state.principal_customer_id and ben.pix_key == args.pix_key:
            return err(ctx, "add_beneficiary", ToolErrorCode.INVALID_ARGUMENT, "duplicate pix key")
    beneficiary_id = ctx.state.next_id("ben")
    beneficiary = Beneficiary(
        beneficiary_id=beneficiary_id,
        customer_id=ctx.state.principal_customer_id,
        nickname=args.nickname,
        pix_key=args.pix_key,
        created_at=ctx.state.now,
        trusted=False,
    )
    ctx.state.beneficiaries[beneficiary_id] = beneficiary
    ctx.state._record_creation(
        entity_id=beneficiary_id,
        step_index=ctx.step_index,
        kind="BENEFICIARY_ADDED",
    )
    ctx.state.emit(
        step_index=ctx.step_index,
        actor=ActorKind.AGENT,
        kind="BENEFICIARY_ADDED",
        entity_ids=[beneficiary_id],
        payload={"beneficiary_id": beneficiary_id, "pix_key": args.pix_key},
    )
    return ok(
        ctx,
        "add_beneficiary",
        {
            "beneficiary_id": beneficiary.beneficiary_id,
            "nickname": beneficiary.nickname,
            "pix_key": beneficiary.pix_key,
            "created_at": beneficiary.created_at.isoformat(),
            "trusted": beneficiary.trusted,
        },
    )


def handle_ask_user(
    ctx: ToolContext, args: AskUserArgs, fault: FaultInjection | None
) -> Observation:
    del fault
    reply = ctx.sim_user.respond_clarification(args.question)
    ctx.state.emit(
        step_index=ctx.step_index,
        actor=ActorKind.USER,
        kind="USER_MESSAGE",
        payload={"question": args.question, "reply": reply},
    )
    return ok(ctx, "ask_user", {"reply": reply})


def handle_finish(ctx: ToolContext, args: FinishArgs, fault: FaultInjection | None) -> Observation:
    del fault
    ctx.done = True
    ctx.state.emit(
        step_index=ctx.step_index,
        actor=ActorKind.AGENT,
        kind="EPISODE_FINISHED",
        payload={"outcome": args.outcome.value, "report": args.report},
    )
    return ok(
        ctx,
        "finish",
        {"outcome": args.outcome.value, "report": args.report},
        kind="final",
    )


HANDLERS = {
    "add_beneficiary": handle_add_beneficiary,
    "ask_user": handle_ask_user,
    "finish": handle_finish,
}
