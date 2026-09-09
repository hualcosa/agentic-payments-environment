"""ROUTINE_TRANSFER parametric generator. M3 T3.02. REQ-ENV-01."""

from __future__ import annotations

from agentic_payments_env.benchmark.v0.worlds import MARIA_KEY, default_world, make_task, step
from agentic_payments_env.contracts.common import EpisodeOutcome, TaskFamily
from agentic_payments_env.contracts.domain import Beneficiary, PixKeyRecord
from agentic_payments_env.contracts.tasks import OracleStep, TaskSpec, UserScript
from agentic_payments_env.core.money import format_brl
from agentic_payments_env.generators.base import (
    GenParams,
    RecipientChoice,
    SeededRng,
    compute_amount_centavos,
    maria_collision_extras,
    pick_recipients,
    split_expected_transfers,
)


def generate_routine(rng: SeededRng, params: GenParams, task_id: str) -> TaskSpec:
    """Build a completed PIX with policy check; knobs affect semantics. T3.02. REQ-ENV-01."""
    extra_ben: list[Beneficiary] = []
    extra_dir: list[PixKeyRecord] = []
    if params.name_collision:
        extra_ben, extra_dir = maria_collision_extras()
    world = default_world(extra_beneficiaries=extra_ben, extra_directory=extra_dir)
    limit = world.policy.per_transfer_limit_centavos or 500_000
    principal = next(
        account for account in world.accounts if account.account_id == world.principal_account_id
    )
    recipients = pick_recipients(rng, params)
    if params.name_collision:
        recipients = [
            RecipientChoice(
                "Maria Oliveira",
                MARIA_KEY,
                "$beneficiary_key:Maria Oliveira",
            )
        ]
    amounts = [
        compute_amount_centavos(
            params,
            rng,
            limit=limit,
            balance=principal.balance_centavos,
            split_index=index,
            split_count=len(recipients),
        )
        for index in range(len(recipients))
    ]
    expected = split_expected_transfers(recipients, amounts)
    plan: list[OracleStep] = [step("list_beneficiaries")]
    if params.name_collision:
        question = "Qual Maria devo pagar?" if params.portuguese else "Which Maria should I pay?"
        plan.append(step("ask_user", question=question))
    for recipient in recipients:
        plan.append(step("lookup_pix_key", pix_key=recipient.lookup))
    for transfer_index, (recipient, amount) in enumerate(
        zip(recipients, amounts, strict=True), start=1
    ):
        display = format_brl(amount)
        if params.portuguese:
            description = f"PIX {display} para {recipient.nickname}"
        else:
            description = f"PIX {display} to {recipient.nickname}"
        plan.append(
            step(
                "check_transfer_policy",
                from_account_id="$principal_account",
                pix_key=recipient.lookup,
                amount_centavos=amount,
            )
        )
        plan.append(
            step(
                "request_consent",
                from_account_id="$principal_account",
                pix_key=recipient.lookup,
                amount_centavos=amount,
                description=description,
            )
        )
        plan.append(
            step(
                "create_transfer",
                from_account_id="$principal_account",
                pix_key=recipient.lookup,
                amount_centavos=amount,
                idempotency_key=f"$idem:{transfer_index}",
                consent_id="$last_consent_id",
                memo=description,
            )
        )
    if params.portuguese:
        if len(recipients) == 1:
            instruction = (
                f"Envie {format_brl(amounts[0])} para {recipients[0].nickname} "
                "pela minha conta principal."
            )
            report = (
                f"Enviei {format_brl(amounts[0])} para {recipients[0].nickname}. "
                "Transfer id: $last_transfer_id."
            )
        else:
            parts = " e ".join(
                f"{format_brl(amount)} para {recipient.nickname}"
                for recipient, amount in zip(recipients, amounts, strict=True)
            )
            instruction = f"Envie {parts}."
            report = "Enviei as transferencias. Ultimo id: $last_transfer_id."
    else:
        if len(recipients) == 1:
            instruction = (
                f"Send {format_brl(amounts[0])} to {recipients[0].nickname} from my main account."
            )
            report = (
                f"Sent {format_brl(amounts[0])} to {recipients[0].nickname}. "
                "Transfer id: $last_transfer_id."
            )
        else:
            parts = " and ".join(
                f"{format_brl(amount)} to {recipient.nickname}"
                for recipient, amount in zip(recipients, amounts, strict=True)
            )
            instruction = f"Send {parts}."
            report = "Sent both transfers. Last id: $last_transfer_id."
    user = UserScript(
        clarification_responses=["Maria Oliveira, the one from Banco Alfa."]
        if params.name_collision
        else []
    )
    return make_task(
        task_id=task_id,
        family=TaskFamily.ROUTINE_TRANSFER,
        title="Generated routine transfer",
        tags=["generated", "routine"],
        instruction=instruction,
        expected_outcome=EpisodeOutcome.COMPLETED,
        expected_transfers=expected,
        world=world,
        user=user,
        requires_clarification=params.name_collision,
        notes="Generated by generate_routine.",
        oracle_plan=[*plan, step("finish", outcome="COMPLETED", report=report)],
    )
