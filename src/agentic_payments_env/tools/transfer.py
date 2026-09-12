"""create_transfer and reverse_transfer. REQ-POL-10, REQ-TOOL-11, REQ-TOOL-12,
REQ-DOM-18, REQ-GRD-07."""

from __future__ import annotations

from typing import Any

from agentic_payments_env.contracts.actions import Observation, PolicyWarning, ToolErrorCode
from agentic_payments_env.contracts.common import (
    AccountStatus,
    ActorKind,
    ConsentStatus,
    Initiator,
    PolicyRuleId,
    TransferStatus,
)
from agentic_payments_env.contracts.domain import Transfer
from agentic_payments_env.contracts.tasks import FaultInjection
from agentic_payments_env.policies import PolicyDecision, consent_validity, evaluate_transfer_policy
from agentic_payments_env.tools.dispatch import ToolContext, err, ok
from agentic_payments_env.tools.schemas import CreateTransferArgs, ReverseTransferArgs

_AUTH_RULES = {PolicyRuleId.STEP_UP_REQUIRED, PolicyRuleId.CONSENT_REQUIRED}


def _transfer_result(transfer: Transfer, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "transfer_id": transfer.transfer_id,
        "status": transfer.status.value,
        "from_account_id": transfer.from_account_id,
        "to_pix_key": transfer.to_pix_key,
        "to_holder_name": transfer.to_holder_name_snapshot,
        "amount_centavos": transfer.amount_centavos,
        "idempotency_key": transfer.idempotency_key,
        "consent_id": transfer.consent_id,
        "memo": transfer.memo,
        "created_at": transfer.created_at.isoformat(),
        "completed_at": None
        if transfer.completed_at is None
        else transfer.completed_at.isoformat(),
    }
    if extra:
        payload.update(extra)
    return payload


def _idempotency_tuple(args: CreateTransferArgs) -> tuple[str, str, int, str]:
    return (args.from_account_id, args.pix_key, args.amount_centavos, args.memo)


def handle_create_transfer(
    ctx: ToolContext, args: CreateTransferArgs, fault: FaultInjection | None
) -> Observation:
    """Normative create_transfer order from 05 §5. REQ-TOOL-11."""
    after = fault is not None and fault.kind.value == "TIMEOUT_AFTER_EXECUTE"
    observation = _create_transfer_body(ctx, args, record_success=not after)
    if after and observation.kind == "tool_result":
        return err(ctx, "create_transfer", ToolErrorCode.TIMEOUT, "request timed out")
    return observation


def _create_transfer_body(
    ctx: ToolContext, args: CreateTransferArgs, *, record_success: bool = True
) -> Observation:
    state = ctx.state
    account = state.owned_account(args.from_account_id)
    if account is None:
        return err(ctx, "create_transfer", ToolErrorCode.NOT_FOUND, "account not found")
    if account.status != AccountStatus.ACTIVE:
        return err(ctx, "create_transfer", ToolErrorCode.ACCOUNT_BLOCKED, "account is blocked")
    record = state.pix_directory.get(args.pix_key)
    if record is None:
        return err(ctx, "create_transfer", ToolErrorCode.NOT_FOUND, "pix key not found")
    for existing in state.transfers.values():
        if existing.idempotency_key != args.idempotency_key:
            continue
        same = (
            existing.from_account_id,
            existing.to_pix_key,
            existing.amount_centavos,
            existing.memo,
        ) == _idempotency_tuple(args)
        if same:
            return ok(
                ctx,
                "create_transfer",
                {**_transfer_result(existing), "idempotent_replay": True},
                record_tool_result=record_success,
            )
        return err(
            ctx,
            "create_transfer",
            ToolErrorCode.IDEMPOTENCY_CONFLICT,
            "idempotency key reused with different arguments",
        )
    decision = evaluate_transfer_policy(
        state, args.from_account_id, args.pix_key, args.amount_centavos, args.consent_id
    )
    ctx.state.emit(
        step_index=ctx.step_index,
        actor=ActorKind.SYSTEM,
        kind="POLICY_EVALUATED",
        payload={"findings": [finding.rule.value for finding in decision.findings]},
        visible_to_agent=False,
    )
    hard_obs = _first_hard(ctx, decision, args)
    if hard_obs is not None:
        return hard_obs
    if account.balance_centavos < args.amount_centavos:
        return err(ctx, "create_transfer", ToolErrorCode.INSUFFICIENT_FUNDS, "insufficient funds")
    pending = Transfer(
        transfer_id=state.next_id("tx"),
        from_account_id=args.from_account_id,
        to_pix_key=args.pix_key,
        to_account_id=record.account_id,
        to_holder_name_snapshot=record.holder_name,
        amount_centavos=args.amount_centavos,
        status=TransferStatus.PENDING,
        idempotency_key=args.idempotency_key,
        consent_id=args.consent_id,
        memo=args.memo,
        created_at=state.now,
        initiated_by=Initiator.AGENT,
    )
    state.transfers[pending.transfer_id] = pending
    state._record_creation(
        entity_id=pending.transfer_id,
        step_index=ctx.step_index,
        kind="TRANSFER_CREATED",
    )
    ctx.state.emit(
        step_index=ctx.step_index,
        actor=ActorKind.SYSTEM,
        kind="TRANSFER_CREATED",
        entity_ids=[pending.transfer_id],
        payload={"transfer_id": pending.transfer_id, "status": "PENDING"},
    )
    completed = state.post_transfer(pending)
    for entry in state.ledger[-2:]:
        state._record_creation(
            entity_id=entry.entry_id,
            step_index=ctx.step_index,
            kind="TRANSFER_COMPLETED",
        )
    consent_status = None
    scope_matched = False
    if args.consent_id is not None:
        valid, _reason = consent_validity(
            state, args.consent_id, args.from_account_id, args.pix_key, args.amount_centavos
        )
        consent = state.consents.get(args.consent_id)
        if consent is not None:
            consent_status = consent.status.value
            scope_matched = valid
            if valid:
                state.consents[args.consent_id] = consent.model_copy(
                    update={
                        "status": ConsentStatus.USED,
                        "used_by_transfer_id": completed.transfer_id,
                    }
                )
                consent_status = ConsentStatus.GRANTED.value
                ctx.state.emit(
                    step_index=ctx.step_index,
                    actor=ActorKind.SYSTEM,
                    kind="CONSENT_USED",
                    entity_ids=[args.consent_id, completed.transfer_id],
                    payload={"consent_id": args.consent_id, "transfer_id": completed.transfer_id},
                )
    auth_level = state.effective_auth_level().value
    ctx.state.emit(
        step_index=ctx.step_index,
        actor=ActorKind.SYSTEM,
        kind="TRANSFER_COMPLETED",
        entity_ids=[completed.transfer_id, *[entry.entry_id for entry in state.ledger[-2:]]],
        payload={
            "transfer_id": completed.transfer_id,
            "consent_id": args.consent_id,
            "consent_status_at_execution": consent_status,
            "consent_scope_matched": scope_matched,
            "auth_level_at_execution": auth_level,
        },
    )
    for finding in list(decision.soft) + list(decision.silent):
        ctx.state.emit(
            step_index=ctx.step_index,
            actor=ActorKind.SYSTEM,
            kind="POLICY_VIOLATION_EXECUTED",
            payload={"rule": finding.rule.value, "mode": finding.mode.value},
            visible_to_agent=False,
        )
    warnings = [
        PolicyWarning(rule=finding.rule, message=finding.message) for finding in decision.soft
    ]
    return ok(
        ctx,
        "create_transfer",
        _transfer_result(completed),
        warnings=warnings,
        record_tool_result=record_success,
    )


def _first_hard(
    ctx: ToolContext, decision: PolicyDecision, args: CreateTransferArgs
) -> Observation | None:
    for finding in decision.hard:
        if finding.rule == PolicyRuleId.STEP_UP_REQUIRED:
            return err(ctx, "create_transfer", ToolErrorCode.AUTH_REQUIRED, finding.message)
        if finding.rule == PolicyRuleId.CONSENT_REQUIRED:
            if args.consent_id is None:
                return err(ctx, "create_transfer", ToolErrorCode.CONSENT_REQUIRED, finding.message)
            _valid, reason = consent_validity(
                ctx.state,
                args.consent_id,
                args.from_account_id,
                args.pix_key,
                args.amount_centavos,
            )
            return err(
                ctx,
                "create_transfer",
                ToolErrorCode.CONSENT_INVALID,
                finding.message,
                details={"reason": reason},
            )
        violations = [
            {"rule": item.rule.value, "message": item.message}
            for item in decision.hard
            if item.rule not in _AUTH_RULES
        ]
        return err(
            ctx,
            "create_transfer",
            ToolErrorCode.POLICY_VIOLATION,
            finding.message,
            details={"violations": violations},
        )
    return None


def handle_reverse_transfer(
    ctx: ToolContext, args: ReverseTransferArgs, fault: FaultInjection | None
) -> Observation:
    after = fault is not None and fault.kind.value == "TIMEOUT_AFTER_EXECUTE"
    observation = _reverse_body(ctx, args, record_success=not after)
    if after and observation.kind == "tool_result":
        return err(ctx, "reverse_transfer", ToolErrorCode.TIMEOUT, "request timed out")
    return observation


def _reverse_body(
    ctx: ToolContext, args: ReverseTransferArgs, *, record_success: bool = True
) -> Observation:
    original = ctx.state.transfers.get(args.transfer_id)
    if original is None:
        return err(ctx, "reverse_transfer", ToolErrorCode.NOT_FOUND, "transfer not found")
    if original.reversal_of is not None:
        return err(
            ctx,
            "reverse_transfer",
            ToolErrorCode.REVERSAL_NOT_ALLOWED,
            "reversal not allowed",
            details={"reason": "IS_REVERSAL"},
        )
    sender = ctx.state.owned_account(original.from_account_id)
    if sender is None:
        return err(
            ctx,
            "reverse_transfer",
            ToolErrorCode.REVERSAL_NOT_ALLOWED,
            "reversal not allowed",
            details={"reason": "NOT_SENDER"},
        )
    if sender.status != AccountStatus.ACTIVE:
        return err(ctx, "reverse_transfer", ToolErrorCode.ACCOUNT_BLOCKED, "account is blocked")
    if original.status != TransferStatus.COMPLETED:
        reason = (
            "ALREADY_REVERSED" if original.status == TransferStatus.REVERSED else "NOT_COMPLETED"
        )
        return err(
            ctx,
            "reverse_transfer",
            ToolErrorCode.REVERSAL_NOT_ALLOWED,
            "reversal not allowed",
            details={"reason": reason},
        )
    if original.reversed_by is not None:
        return err(
            ctx,
            "reverse_transfer",
            ToolErrorCode.REVERSAL_NOT_ALLOWED,
            "reversal not allowed",
            details={"reason": "ALREADY_REVERSED"},
        )
    completed_at = original.completed_at
    if completed_at is None:
        return err(
            ctx,
            "reverse_transfer",
            ToolErrorCode.REVERSAL_NOT_ALLOWED,
            "reversal not allowed",
            details={"reason": "NOT_COMPLETED"},
        )
    elapsed = (ctx.state.now - completed_at).total_seconds()
    if elapsed > ctx.state.policy.reversal_window_seconds:
        return err(
            ctx,
            "reverse_transfer",
            ToolErrorCode.REVERSAL_NOT_ALLOWED,
            "reversal not allowed",
            details={"reason": "WINDOW_EXPIRED"},
        )
    dest_key = original.from_account_id
    for record in ctx.state.pix_directory.values():
        if record.account_id == original.from_account_id:
            dest_key = record.pix_key
            break
    pending = Transfer(
        transfer_id=ctx.state.next_id("tx"),
        from_account_id=original.to_account_id,
        to_pix_key=dest_key,
        to_account_id=original.from_account_id,
        to_holder_name_snapshot=ctx.state.principal().display_name,
        amount_centavos=original.amount_centavos,
        status=TransferStatus.PENDING,
        idempotency_key=f"rev-{original.transfer_id}",
        consent_id=None,
        memo=args.reason,
        created_at=ctx.state.now,
        reversal_of=original.transfer_id,
        initiated_by=Initiator.AGENT,
    )
    ctx.state.transfers[pending.transfer_id] = pending
    ctx.state._record_creation(
        entity_id=pending.transfer_id,
        step_index=ctx.step_index,
        kind="TRANSFER_REVERSED",
    )
    completed = ctx.state.post_transfer(pending)
    for entry in ctx.state.ledger[-2:]:
        ctx.state._record_creation(
            entity_id=entry.entry_id,
            step_index=ctx.step_index,
            kind="TRANSFER_REVERSED",
        )
    ctx.state.transfers[original.transfer_id] = original.model_copy(
        update={"status": TransferStatus.REVERSED, "reversed_by": completed.transfer_id}
    )
    ctx.state.emit(
        step_index=ctx.step_index,
        actor=ActorKind.SYSTEM,
        kind="TRANSFER_REVERSED",
        entity_ids=[
            original.transfer_id,
            completed.transfer_id,
            *[entry.entry_id for entry in ctx.state.ledger[-2:]],
        ],
        payload={"reversal_of": original.transfer_id, "transfer_id": completed.transfer_id},
    )
    return ok(
        ctx,
        "reverse_transfer",
        _transfer_result(completed, extra={"reversal_of": original.transfer_id}),
        record_tool_result=record_success,
    )


HANDLERS = {
    "create_transfer": handle_create_transfer,
    "reverse_transfer": handle_reverse_transfer,
}
