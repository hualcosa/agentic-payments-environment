"""Read tools: profile, balances, directory, policy dry-run, and transfer lookup.

Satisfies: REQ-TOOL-06, REQ-TOOL-07, REQ-TOOL-09, REQ-TOOL-14, REQ-POL-03.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from agentic_payments_env.contracts.actions import Observation, ToolErrorCode
from agentic_payments_env.contracts.common import ActorKind, PolicyRuleId, TransferStatus
from agentic_payments_env.contracts.domain import Transfer
from agentic_payments_env.contracts.tasks import FaultInjection
from agentic_payments_env.policies import evaluate_transfer_policy
from agentic_payments_env.tools.dispatch import ToolContext, err, ok
from agentic_payments_env.tools.schemas import (
    CheckTransferPolicyArgs,
    GetAccountBalanceArgs,
    GetCustomerProfileArgs,
    GetTransferArgs,
    GetTransferByIdempotencyKeyArgs,
    ListBeneficiariesArgs,
    ListTransfersArgs,
    LookupPixKeyArgs,
)
from agentic_payments_env.world import WorldState


def _iso(value: datetime) -> str:
    return value.isoformat()


def _daily_used_created_at(state: WorldState, account_id: str) -> int:
    today = state.now.date()
    used = 0
    for transfer in state.transfers.values():
        if transfer.from_account_id != account_id:
            continue
        if transfer.status != TransferStatus.COMPLETED:
            continue
        if transfer.reversal_of is not None:
            continue
        if transfer.created_at.date() != today:
            continue
        used += transfer.amount_centavos
    return used


def _transfer_payload(transfer: Transfer, *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {
        "transfer_id": transfer.transfer_id,
        "status": transfer.status.value,
        "from_account_id": transfer.from_account_id,
        "to_pix_key": transfer.to_pix_key,
        "to_holder_name": transfer.to_holder_name_snapshot,
        "amount_centavos": transfer.amount_centavos,
        "idempotency_key": transfer.idempotency_key,
        "consent_id": transfer.consent_id,
        "memo": transfer.memo,
        "created_at": _iso(transfer.created_at),
        "completed_at": None if transfer.completed_at is None else _iso(transfer.completed_at),
        "reversal_of": transfer.reversal_of,
        "reversed_by": transfer.reversed_by,
        "failure_reason": transfer.failure_reason,
    }
    if extra:
        payload.update(extra)
    return payload


def _principal_can_see(state: WorldState, transfer: Transfer) -> bool:
    from_acc = state.accounts.get(transfer.from_account_id)
    to_acc = state.accounts.get(transfer.to_account_id)
    principal = state.principal_customer_id
    if from_acc is not None and from_acc.customer_id == principal:
        return True
    return to_acc is not None and to_acc.customer_id == principal


def _history_index(length: int, stale_age_steps: int) -> int:
    idx = length - 1 - stale_age_steps
    return 0 if idx < 0 else idx


def handle_get_customer_profile(
    ctx: ToolContext, args: GetCustomerProfileArgs, fault: FaultInjection | None
) -> Observation:
    del args, fault
    state = ctx.state
    customer = state.principal()
    accounts = [
        {"account_id": account.account_id, "status": account.status.value}
        for account in sorted(state.accounts.values(), key=lambda item: item.account_id)
        if account.customer_id == customer.customer_id
    ]
    policy = state.policy
    night = policy.night_window
    result = {
        "customer_id": customer.customer_id,
        "display_name": customer.display_name,
        "document_masked": customer.document_masked,
        "kyc_level": customer.kyc_level.value,
        "auth_level": state.effective_auth_level().value,
        "step_up_valid_until": (
            None
            if customer.auth.step_up_valid_until is None
            else _iso(customer.auth.step_up_valid_until)
        ),
        "accounts": accounts,
        "limits": {
            "per_transfer_limit_centavos": policy.per_transfer_limit_centavos,
            "daily_limit_centavos": policy.daily_limit_centavos,
            "daily_used_centavos": _daily_used_created_at(state, state.principal_account_id),
            "night_limit_centavos": policy.night_limit_centavos,
            "night_window_utc": (
                None if night is None else [night.start_hour_utc, night.end_hour_utc]
            ),
            "step_up_threshold_centavos": policy.step_up_threshold_centavos,
            "consent_required": policy.consent_required,
        },
    }
    return ok(ctx, "get_customer_profile", result)


def handle_get_account_balance(
    ctx: ToolContext, args: GetAccountBalanceArgs, fault: FaultInjection | None
) -> Observation:
    account = ctx.state.owned_account(args.account_id)
    if account is None:
        return err(ctx, "get_account_balance", ToolErrorCode.NOT_FOUND, "account not found")
    if fault is not None and fault.kind.value == "STALE_READ":
        history = ctx.state.balance_history.get(args.account_id, [])
        if not history:
            as_of = ctx.state.now
            balance = account.balance_centavos
        else:
            age = fault.stale_age_steps or 0
            ts, balance = history[_history_index(len(history), age)]
            as_of = ts
        result = {
            "account_id": account.account_id,
            "balance_centavos": balance,
            "status": account.status.value,
            "as_of": _iso(as_of),
        }
        return ok(ctx, "get_account_balance", result, observed_at=as_of)
    result = {
        "account_id": account.account_id,
        "balance_centavos": account.balance_centavos,
        "status": account.status.value,
        "as_of": _iso(ctx.state.now),
    }
    return ok(ctx, "get_account_balance", result)


def handle_list_beneficiaries(
    ctx: ToolContext, args: ListBeneficiariesArgs, fault: FaultInjection | None
) -> Observation:
    del args, fault
    rows = []
    for ben in sorted(ctx.state.beneficiaries.values(), key=lambda item: item.beneficiary_id):
        if ben.customer_id != ctx.state.principal_customer_id:
            continue
        rows.append(
            {
                "beneficiary_id": ben.beneficiary_id,
                "nickname": ben.nickname,
                "pix_key": ben.pix_key,
                "created_at": _iso(ben.created_at),
                "trusted": ben.trusted,
            }
        )
    return ok(ctx, "list_beneficiaries", {"beneficiaries": rows})


def handle_lookup_pix_key(
    ctx: ToolContext, args: LookupPixKeyArgs, fault: FaultInjection | None
) -> Observation:
    del fault
    record = ctx.state.pix_directory.get(args.pix_key)
    if record is None:
        return err(ctx, "lookup_pix_key", ToolErrorCode.NOT_FOUND, "pix key not found")
    return ok(
        ctx,
        "lookup_pix_key",
        {
            "pix_key": record.pix_key,
            "key_type": record.key_type.value,
            "holder_name": record.holder_name,
            "holder_document_masked": record.holder_document_masked,
            "bank_name": record.bank_name,
        },
    )


def handle_check_transfer_policy(
    ctx: ToolContext, args: CheckTransferPolicyArgs, fault: FaultInjection | None
) -> Observation:
    del fault
    account = ctx.state.owned_account(args.from_account_id)
    if account is None:
        return err(ctx, "check_transfer_policy", ToolErrorCode.NOT_FOUND, "account not found")
    if args.pix_key not in ctx.state.pix_directory:
        return err(ctx, "check_transfer_policy", ToolErrorCode.NOT_FOUND, "pix key not found")
    decision = evaluate_transfer_policy(
        ctx.state, args.from_account_id, args.pix_key, args.amount_centavos, None
    )
    skip_auth = {PolicyRuleId.STEP_UP_REQUIRED, PolicyRuleId.CONSENT_REQUIRED}
    violations = [
        {"rule": finding.rule.value, "message": finding.message}
        for finding in decision.hard
        if finding.rule not in skip_auth
    ]
    warnings = [
        {"rule": finding.rule.value, "message": finding.message} for finding in decision.soft
    ]
    step_up = next((f for f in decision.findings if f.rule == PolicyRuleId.STEP_UP_REQUIRED), None)
    consent = next((f for f in decision.findings if f.rule == PolicyRuleId.CONSENT_REQUIRED), None)
    requires_step_up = step_up is not None and step_up.mode.value != "SILENT"
    requires_consent = consent is not None and consent.mode.value != "SILENT"
    sufficient = account.balance_centavos >= args.amount_centavos
    if violations:
        would_fail_with: str | None = "POLICY_VIOLATION"
    elif not sufficient:
        would_fail_with = "INSUFFICIENT_FUNDS"
    else:
        would_fail_with = None
    ctx.state.emit(
        step_index=ctx.step_index,
        actor=ActorKind.SYSTEM,
        kind="POLICY_EVALUATED",
        payload={"tool": "check_transfer_policy"},
        visible_to_agent=False,
    )
    return ok(
        ctx,
        "check_transfer_policy",
        {
            "allowed": would_fail_with is None,
            "violations": violations,
            "warnings": warnings,
            "requires_step_up": requires_step_up,
            "requires_consent": requires_consent,
            "sufficient_funds": sufficient,
            "would_fail_with": would_fail_with,
        },
    )


def _stale_transfer(ctx: ToolContext, transfer_id: str, stale_age_steps: int) -> Transfer | None:
    history = ctx.state.transfer_history
    if not history:
        return None
    snapshot = history[_history_index(len(history), stale_age_steps)]
    if transfer_id not in snapshot:
        return None
    current = ctx.state.transfers.get(transfer_id)
    if current is None:
        return None
    return current.model_copy(update={"status": snapshot[transfer_id]})


def handle_get_transfer(
    ctx: ToolContext, args: GetTransferArgs, fault: FaultInjection | None
) -> Observation:
    transfer: Transfer | None
    if fault is not None and fault.kind.value == "STALE_READ":
        transfer = _stale_transfer(ctx, args.transfer_id, fault.stale_age_steps or 0)
        if transfer is None:
            return err(ctx, "get_transfer", ToolErrorCode.NOT_FOUND, "transfer not found")
        hist = ctx.state.balance_history.get(ctx.state.principal_account_id, [])
        if hist:
            observed_at = hist[_history_index(len(hist), fault.stale_age_steps or 0)][0]
        else:
            observed_at = ctx.state.now
        if not _principal_can_see(ctx.state, transfer):
            return err(ctx, "get_transfer", ToolErrorCode.NOT_FOUND, "transfer not found")
        return ok(ctx, "get_transfer", _transfer_payload(transfer), observed_at=observed_at)
    transfer = ctx.state.transfers.get(args.transfer_id)
    if transfer is None or not _principal_can_see(ctx.state, transfer):
        return err(ctx, "get_transfer", ToolErrorCode.NOT_FOUND, "transfer not found")
    return ok(ctx, "get_transfer", _transfer_payload(transfer))


def handle_get_transfer_by_idempotency_key(
    ctx: ToolContext, args: GetTransferByIdempotencyKeyArgs, fault: FaultInjection | None
) -> Observation:
    del fault
    found = next(
        (
            transfer
            for transfer in ctx.state.transfers.values()
            if transfer.idempotency_key == args.idempotency_key
        ),
        None,
    )
    if found is None or not _principal_can_see(ctx.state, found):
        return err(
            ctx,
            "get_transfer_by_idempotency_key",
            ToolErrorCode.NOT_FOUND,
            "transfer not found",
        )
    return ok(ctx, "get_transfer_by_idempotency_key", _transfer_payload(found))


def handle_list_transfers(
    ctx: ToolContext, args: ListTransfersArgs, fault: FaultInjection | None
) -> Observation:
    if ctx.state.owned_account(args.account_id) is None:
        return err(ctx, "list_transfers", ToolErrorCode.NOT_FOUND, "account not found")
    stale_status: dict[str, TransferStatus] | None = None
    observed_at = None
    if fault is not None and fault.kind.value == "STALE_READ":
        history = ctx.state.transfer_history
        if history:
            stale_status = history[_history_index(len(history), fault.stale_age_steps or 0)]
        hist = ctx.state.balance_history.get(args.account_id, [])
        if hist:
            observed_at = hist[_history_index(len(hist), fault.stale_age_steps or 0)][0]
    rows: list[dict[str, Any]] = []
    for transfer in ctx.state.transfers.values():
        if stale_status is not None and transfer.transfer_id not in stale_status:
            continue
        outgoing = transfer.from_account_id == args.account_id
        incoming = transfer.to_account_id == args.account_id
        if not outgoing and not incoming:
            continue
        shown = transfer
        if stale_status is not None:
            shown = transfer.model_copy(update={"status": stale_status[transfer.transfer_id]})
        payload = _transfer_payload(shown, extra={"direction": "OUT" if outgoing else "IN"})
        rows.append(payload)
    rows.sort(key=lambda row: (row["created_at"], row["transfer_id"]), reverse=True)
    return ok(ctx, "list_transfers", {"transfers": rows[: args.limit]}, observed_at=observed_at)


HANDLERS = {
    "get_customer_profile": handle_get_customer_profile,
    "get_account_balance": handle_get_account_balance,
    "list_beneficiaries": handle_list_beneficiaries,
    "lookup_pix_key": handle_lookup_pix_key,
    "check_transfer_policy": handle_check_transfer_policy,
    "get_transfer": handle_get_transfer,
    "get_transfer_by_idempotency_key": handle_get_transfer_by_idempotency_key,
    "list_transfers": handle_list_transfers,
}
