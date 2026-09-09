"""Deterministic transfer policy evaluation.

Satisfies: REQ-POL-01, REQ-POL-02, REQ-POL-04, REQ-POL-05, REQ-POL-06, REQ-POL-07,
REQ-POL-08, REQ-POL-09, REQ-POL-11, REQ-POL-12.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from agentic_payments_env.contracts.common import (
    AuthLevel,
    ConsentStatus,
    EnforcementMode,
    FrozenModel,
    PolicyRuleId,
    TransferStatus,
)
from agentic_payments_env.contracts.domain import NightWindow
from agentic_payments_env.world import WorldState


class PolicyFinding(FrozenModel):
    """A single fired policy rule. REQ-POL-06."""

    rule: PolicyRuleId
    mode: EnforcementMode
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class PolicyDecision(FrozenModel):
    """All findings for a proposed transfer, in catalog order. REQ-POL-06."""

    findings: list[PolicyFinding]

    @property
    def hard(self) -> list[PolicyFinding]:
        return [finding for finding in self.findings if finding.mode == EnforcementMode.HARD]

    @property
    def soft(self) -> list[PolicyFinding]:
        return [finding for finding in self.findings if finding.mode == EnforcementMode.SOFT]

    @property
    def silent(self) -> list[PolicyFinding]:
        return [finding for finding in self.findings if finding.mode == EnforcementMode.SILENT]

    @property
    def allowed(self) -> bool:
        return not self.hard


def in_window(now: datetime, window: NightWindow) -> bool:
    """Whether ``now`` falls in the (possibly wrapping) night window. REQ-POL-04."""
    start = window.start_hour_utc
    end = window.end_hour_utc
    hour = now.hour
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def consent_validity(
    state: WorldState,
    consent_id: str,
    from_account_id: str,
    pix_key: str,
    amount: int,
) -> tuple[bool, str | None]:
    """Return ``(True, None)`` if the consent is valid, else ``(False, reason)``. REQ-POL-07."""
    consent = state.consents.get(consent_id)
    if consent is None or consent.customer_id != state.principal_customer_id:
        return False, "NOT_FOUND"
    if consent.status == ConsentStatus.USED:
        return False, "ALREADY_USED"
    if consent.status == ConsentStatus.EXPIRED or consent.expires_at <= state.now:
        return False, "EXPIRED"
    if consent.status != ConsentStatus.GRANTED:
        return False, "NOT_GRANTED"
    scope = consent.scope
    if (
        scope.from_account_id != from_account_id
        or scope.pix_key != pix_key
        or scope.amount_centavos != amount
    ):
        return False, "SCOPE_MISMATCH"
    return True, None


def evaluate_transfer_policy(
    state: WorldState,
    from_account_id: str,
    pix_key: str,
    amount_centavos: int,
    consent_id: str | None,
) -> PolicyDecision:
    """Evaluate every policy rule with no short-circuit and no mutation. REQ-POL-06, REQ-POL-11."""
    policy = state.policy
    findings: list[PolicyFinding] = []

    limit = policy.per_transfer_limit_centavos
    if limit is not None and amount_centavos > limit:
        findings.append(
            _finding(
                state,
                PolicyRuleId.PER_TRANSFER_LIMIT,
                f"amount {amount_centavos} exceeds per-transfer limit {limit}",
                {"amount": amount_centavos, "limit": limit},
            )
        )

    daily_limit = policy.daily_limit_centavos
    used = _daily_used(state, from_account_id)
    if daily_limit is not None and used + amount_centavos > daily_limit:
        findings.append(
            _finding(
                state,
                PolicyRuleId.DAILY_LIMIT,
                (
                    f"daily limit {daily_limit} would be exceeded: "
                    f"used {used}, requested {amount_centavos}"
                ),
                {"limit": daily_limit, "used": used, "amount": amount_centavos},
            )
        )

    night_window = policy.night_window
    night_limit = policy.night_limit_centavos
    if (
        night_window is not None
        and in_window(state.now, night_window)
        and night_limit is not None
        and amount_centavos > night_limit
    ):
        findings.append(
            _finding(
                state,
                PolicyRuleId.NIGHT_LIMIT,
                f"amount {amount_centavos} exceeds night-time limit {night_limit}",
                {"amount": amount_centavos, "limit": night_limit},
            )
        )

    customer = state.customers[state.principal_customer_id]
    cap = policy.kyc_caps_centavos.get(customer.kyc_level)
    if cap is not None and amount_centavos > cap:
        findings.append(
            _finding(
                state,
                PolicyRuleId.KYC_AMOUNT_CAP,
                f"amount {amount_centavos} exceeds KYC {customer.kyc_level.value} cap {cap}",
                {"amount": amount_centavos, "level": customer.kyc_level.value, "cap": cap},
            )
        )

    if pix_key in policy.blocked_pix_keys:
        findings.append(
            _finding(
                state,
                PolicyRuleId.BLOCKED_RECIPIENT,
                "recipient key is blocked",
                {"pix_key": pix_key},
            )
        )

    cooling = policy.new_beneficiary_cooling_seconds
    if cooling > 0 and _cooling_fires(state, pix_key, cooling):
        findings.append(
            _finding(
                state,
                PolicyRuleId.NEW_BENEFICIARY_COOLING,
                f"recipient was added less than {cooling}s ago",
                {"cooling": cooling, "pix_key": pix_key},
            )
        )

    threshold = policy.step_up_threshold_centavos
    if (
        threshold is not None
        and amount_centavos >= threshold
        and _effective_auth_level(state) != AuthLevel.STEP_UP
    ):
        findings.append(
            _finding(
                state,
                PolicyRuleId.STEP_UP_REQUIRED,
                f"step-up authentication required for amounts >= {threshold}",
                {"threshold": threshold, "amount": amount_centavos},
            )
        )

    if policy.consent_required:
        if consent_id is None:
            findings.append(
                _finding(state, PolicyRuleId.CONSENT_REQUIRED, "explicit consent required", {})
            )
        else:
            valid, reason = consent_validity(
                state, consent_id, from_account_id, pix_key, amount_centavos
            )
            if not valid:
                findings.append(
                    _finding(
                        state,
                        PolicyRuleId.CONSENT_REQUIRED,
                        f"consent invalid: {reason}",
                        {"reason": reason},
                    )
                )

    return PolicyDecision(findings=findings)


def _finding(
    state: WorldState, rule: PolicyRuleId, message: str, data: dict[str, Any]
) -> PolicyFinding:
    return PolicyFinding(rule=rule, mode=state.policy.mode(rule), message=message, data=data)


def _daily_used(state: WorldState, from_account_id: str) -> int:
    today = state.now.date()
    used = 0
    for transfer in state.transfers.values():
        if transfer.from_account_id != from_account_id:
            continue
        if transfer.status != TransferStatus.COMPLETED:
            continue
        if transfer.reversal_of is not None:
            continue
        if transfer.created_at.date() != today:
            continue
        used += transfer.amount_centavos
    return used


def _cooling_fires(state: WorldState, pix_key: str, cooling: int) -> bool:
    matches = [
        ben
        for ben in state.beneficiaries.values()
        if ben.customer_id == state.principal_customer_id and ben.pix_key == pix_key
    ]
    if not matches:
        return True
    for ben in matches:
        if ben.trusted:
            continue
        age = (state.now - ben.created_at).total_seconds()
        if age < cooling:
            return True
    return False


def _effective_auth_level(state: WorldState) -> AuthLevel:
    """STEP_UP iff level is STEP_UP and TTL is still strictly in the future. REQ-POL-05."""
    auth = state.customers[state.principal_customer_id].auth
    if (
        auth.level == AuthLevel.STEP_UP
        and auth.step_up_valid_until is not None
        and auth.step_up_valid_until > state.now
    ):
        return AuthLevel.STEP_UP
    return AuthLevel.BASIC
