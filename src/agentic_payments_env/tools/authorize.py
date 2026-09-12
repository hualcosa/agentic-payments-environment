"""Authorization tools: consent and step-up. REQ-TOOL-10, REQ-POL (05 §6)."""

from __future__ import annotations

from datetime import timedelta

from agentic_payments_env.contracts.actions import Observation, ToolErrorCode
from agentic_payments_env.contracts.common import (
    ActorKind,
    AuthLevel,
    ChallengeStatus,
    ConsentStatus,
)
from agentic_payments_env.contracts.domain import AuthState, Consent, ConsentScope, StepUpChallenge
from agentic_payments_env.contracts.tasks import ConsentResponse, FaultInjection, StepUpResponse
from agentic_payments_env.tools.dispatch import ToolContext, err, ok
from agentic_payments_env.tools.schemas import RequestConsentArgs, RequestStepUpAuthArgs


def handle_request_consent(
    ctx: ToolContext, args: RequestConsentArgs, fault: FaultInjection | None
) -> Observation:
    del fault
    if ctx.state.owned_account(args.from_account_id) is None:
        return err(ctx, "request_consent", ToolErrorCode.NOT_FOUND, "account not found")
    if args.pix_key not in ctx.state.pix_directory:
        return err(ctx, "request_consent", ToolErrorCode.NOT_FOUND, "pix key not found")
    scope = ConsentScope(
        from_account_id=args.from_account_id,
        pix_key=args.pix_key,
        amount_centavos=args.amount_centavos,
    )
    expires_at = ctx.state.now + timedelta(seconds=ctx.state.policy.consent_ttl_seconds)
    consent_id = ctx.state.next_id("cons")
    consent = Consent(
        consent_id=consent_id,
        customer_id=ctx.state.principal_customer_id,
        scope=scope,
        status=ConsentStatus.PENDING,
        created_at=ctx.state.now,
        expires_at=expires_at,
        description=args.description,
    )
    ctx.state._record_creation(
        entity_id=consent_id,
        step_index=ctx.step_index,
        kind="CONSENT_REQUESTED",
    )
    ctx.state.emit(
        step_index=ctx.step_index,
        actor=ActorKind.SYSTEM,
        kind="CONSENT_REQUESTED",
        entity_ids=[consent_id],
        payload={"consent_id": consent_id},
    )
    response = ctx.sim_user.respond_consent(scope)
    if response == ConsentResponse.GRANT:
        consent = consent.model_copy(update={"status": ConsentStatus.GRANTED})
        ctx.state.emit(
            step_index=ctx.step_index,
            actor=ActorKind.USER,
            kind="CONSENT_GRANTED",
            entity_ids=[consent_id],
            payload={"consent_id": consent_id},
        )
    elif response == ConsentResponse.DENY:
        consent = consent.model_copy(update={"status": ConsentStatus.DENIED})
        ctx.state.emit(
            step_index=ctx.step_index,
            actor=ActorKind.USER,
            kind="CONSENT_DENIED",
            entity_ids=[consent_id],
            payload={"consent_id": consent_id},
        )
    ctx.state.consents[consent_id] = consent
    return ok(
        ctx,
        "request_consent",
        {
            "consent_id": consent.consent_id,
            "status": consent.status.value,
            "scope": {
                "from_account_id": scope.from_account_id,
                "pix_key": scope.pix_key,
                "amount_centavos": scope.amount_centavos,
            },
            "expires_at": expires_at.isoformat(),
        },
    )


def handle_request_step_up_auth(
    ctx: ToolContext, args: RequestStepUpAuthArgs, fault: FaultInjection | None
) -> Observation:
    del args, fault
    challenge_id = ctx.state.next_id("chal")
    challenge = StepUpChallenge(
        challenge_id=challenge_id,
        customer_id=ctx.state.principal_customer_id,
        status=ChallengeStatus.PENDING,
        created_at=ctx.state.now,
    )
    ctx.state._record_creation(
        entity_id=challenge_id,
        step_index=ctx.step_index,
        kind="STEP_UP_REQUESTED",
    )
    ctx.state.emit(
        step_index=ctx.step_index,
        actor=ActorKind.SYSTEM,
        kind="STEP_UP_REQUESTED",
        entity_ids=[challenge_id],
        payload={"challenge_id": challenge_id},
    )
    response = ctx.sim_user.respond_step_up()
    valid_until = None
    auth_level = ctx.state.effective_auth_level()
    if response == StepUpResponse.APPROVE:
        valid_until = ctx.state.now + timedelta(seconds=ctx.state.policy.step_up_ttl_seconds)
        challenge = challenge.model_copy(update={"status": ChallengeStatus.APPROVED})
        customer = ctx.state.principal()
        ctx.state.customers[customer.customer_id] = customer.model_copy(
            update={"auth": AuthState(level=AuthLevel.STEP_UP, step_up_valid_until=valid_until)}
        )
        auth_level = AuthLevel.STEP_UP
        ctx.state.emit(
            step_index=ctx.step_index,
            actor=ActorKind.USER,
            kind="STEP_UP_APPROVED",
            entity_ids=[challenge_id],
            payload={"challenge_id": challenge_id},
        )
    elif response == StepUpResponse.DENY:
        challenge = challenge.model_copy(update={"status": ChallengeStatus.DENIED})
        ctx.state.emit(
            step_index=ctx.step_index,
            actor=ActorKind.USER,
            kind="STEP_UP_DENIED",
            entity_ids=[challenge_id],
            payload={"challenge_id": challenge_id},
        )
    ctx.state.challenges[challenge_id] = challenge
    return ok(
        ctx,
        "request_step_up_auth",
        {
            "challenge_id": challenge_id,
            "status": challenge.status.value,
            "auth_level": auth_level.value,
            "step_up_valid_until": None if valid_until is None else valid_until.isoformat(),
        },
    )


HANDLERS = {
    "request_consent": handle_request_consent,
    "request_step_up_auth": handle_request_step_up_auth,
}
