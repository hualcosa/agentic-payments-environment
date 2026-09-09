"""Policy engine tests: one case per catalog rule plus consent and window edges."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from agentic_payments_env.contracts.common import (
    AuthLevel,
    ConsentStatus,
    EnforcementMode,
    Initiator,
    KycLevel,
    PolicyRuleId,
    TransferStatus,
)
from agentic_payments_env.contracts.domain import (
    AuthState,
    Beneficiary,
    Consent,
    ConsentScope,
    NightWindow,
    PolicyConfig,
    Transfer,
)
from agentic_payments_env.policies import consent_validity, evaluate_transfer_policy, in_window
from agentic_payments_env.world import WorldState
from tests.test_world import START, default_world_fixture

MARIA = "maria.oliveira@example.com"
JOAO = "joao.pereira@example.com"
BLOCKED = "blocked.key@example.com"


def _state(
    *,
    policy: PolicyConfig | None = None,
    start: datetime = START,
    kyc: KycLevel = KycLevel.FULL,
    auth: AuthState | None = None,
    extra_transfers: list[Transfer] | None = None,
    extra_beneficiaries: list[Beneficiary] | None = None,
    consents: dict[str, Consent] | None = None,
) -> WorldState:
    fixture = default_world_fixture()
    updates: dict[str, object] = {"start_time": start}
    if policy is not None:
        updates["policy"] = policy
    customers = []
    for customer in fixture.customers:
        if customer.customer_id == "cus_ana":
            customers.append(
                customer.model_copy(update={"kyc_level": kyc, "auth": auth or AuthState()})
            )
        else:
            customers.append(customer)
    updates["customers"] = customers
    if extra_transfers:
        updates["transfers"] = list(fixture.transfers) + extra_transfers
    if extra_beneficiaries:
        updates["beneficiaries"] = list(fixture.beneficiaries) + extra_beneficiaries
    fixture = fixture.model_copy(update=updates)
    state = WorldState.from_fixture(fixture)
    if consents:
        state.consents.update(consents)
    return state


def _policy(**overrides: object) -> PolicyConfig:
    data: dict[str, object] = {"consent_required": False}
    data.update(overrides)
    return PolicyConfig.model_validate(data)


def _rules(
    state: WorldState, amount: int, pix_key: str = MARIA, consent_id: str | None = None
) -> list[PolicyRuleId]:
    decision = evaluate_transfer_policy(state, "acc_ana", pix_key, amount, consent_id)
    return [finding.rule for finding in decision.findings]


def test_per_transfer_limit() -> None:
    state = _state(policy=_policy())
    assert PolicyRuleId.PER_TRANSFER_LIMIT in _rules(state, 500_001)
    assert PolicyRuleId.PER_TRANSFER_LIMIT not in _rules(state, 500_000)


def test_daily_limit_completed_non_reversed_same_utc_date() -> None:
    prior = Transfer(
        transfer_id="tx_prior",
        from_account_id="acc_ana",
        to_pix_key=MARIA,
        to_account_id="acc_external",
        to_holder_name_snapshot="MARIA",
        amount_centavos=900_000,
        status=TransferStatus.COMPLETED,
        idempotency_key="prior",
        consent_id=None,
        created_at=START,
        completed_at=START,
        initiated_by=Initiator.FIXTURE,
    )
    yesterday = prior.model_copy(
        update={
            "transfer_id": "tx_yest",
            "idempotency_key": "yest",
            "created_at": START - timedelta(days=1),
            "completed_at": START - timedelta(days=1),
        }
    )
    reversed_original = prior.model_copy(
        update={
            "transfer_id": "tx_rev",
            "idempotency_key": "rev",
            "status": TransferStatus.REVERSED,
            "amount_centavos": 50_000,
        }
    )
    state = _state(policy=_policy(), extra_transfers=[prior, yesterday])
    state.transfers[reversed_original.transfer_id] = reversed_original
    assert PolicyRuleId.DAILY_LIMIT in _rules(state, 200_000)
    assert PolicyRuleId.DAILY_LIMIT not in _rules(state, 100_000)


def test_night_limit() -> None:
    night = START.replace(hour=23)
    state = _state(policy=_policy(), start=night)
    assert PolicyRuleId.NIGHT_LIMIT in _rules(state, 100_001)
    day = _state(policy=_policy(), start=START)
    assert PolicyRuleId.NIGHT_LIMIT not in _rules(day, 100_001)


def test_kyc_amount_cap_none_never_fires_zero_fires() -> None:
    full = _state(policy=_policy(), kyc=KycLevel.FULL)
    assert PolicyRuleId.KYC_AMOUNT_CAP not in _rules(full, 10_000_000)
    none_caps = {
        KycLevel.NONE: 0,
        KycLevel.BASIC: 300_000,
        KycLevel.FULL: None,
    }
    none = _state(policy=_policy(kyc_caps_centavos=none_caps), kyc=KycLevel.NONE)
    assert PolicyRuleId.KYC_AMOUNT_CAP in _rules(none, 1)


def test_blocked_recipient() -> None:
    state = _state(policy=_policy(blocked_pix_keys=[BLOCKED]))
    assert PolicyRuleId.BLOCKED_RECIPIENT in _rules(state, 100, pix_key=BLOCKED)
    assert PolicyRuleId.BLOCKED_RECIPIENT not in _rules(state, 100, pix_key=MARIA)


def test_new_beneficiary_cooling_unsaved_and_trusted() -> None:
    cooling_policy = _policy(new_beneficiary_cooling_seconds=3600)
    state = _state(policy=cooling_policy)
    assert PolicyRuleId.NEW_BENEFICIARY_COOLING in _rules(state, 100, pix_key=JOAO)
    assert PolicyRuleId.NEW_BENEFICIARY_COOLING not in _rules(state, 100, pix_key=MARIA)
    untrusted = Beneficiary(
        beneficiary_id="ben_new",
        customer_id="cus_ana",
        nickname="Joao",
        pix_key=JOAO,
        created_at=START - timedelta(seconds=10),
        trusted=False,
    )
    cooled = _state(policy=cooling_policy, extra_beneficiaries=[untrusted])
    assert PolicyRuleId.NEW_BENEFICIARY_COOLING in _rules(cooled, 100, pix_key=JOAO)


def test_step_up_required_and_expired_ttl() -> None:
    state = _state(policy=_policy())
    assert PolicyRuleId.STEP_UP_REQUIRED in _rules(state, 100_000)
    valid = _state(
        policy=_policy(),
        auth=AuthState(level=AuthLevel.STEP_UP, step_up_valid_until=START + timedelta(seconds=60)),
    )
    assert PolicyRuleId.STEP_UP_REQUIRED not in _rules(valid, 100_000)
    expired = _state(
        policy=_policy(),
        auth=AuthState(level=AuthLevel.STEP_UP, step_up_valid_until=START),
    )
    assert PolicyRuleId.STEP_UP_REQUIRED in _rules(expired, 100_000)


def test_consent_required() -> None:
    state = _state(policy=PolicyConfig(consent_required=True))
    assert PolicyRuleId.CONSENT_REQUIRED in _rules(state, 100)


def test_night_window_wrap() -> None:
    wrap = NightWindow(start_hour_utc=20, end_hour_utc=6)
    day = NightWindow(start_hour_utc=9, end_hour_utc=17)

    def at_hour(hour: int, minute: int = 0) -> datetime:
        return datetime(2026, 3, 10, hour, minute, tzinfo=UTC)

    assert in_window(at_hour(23), wrap)
    assert in_window(at_hour(5, 59), wrap)
    assert not in_window(at_hour(6), wrap)
    assert not in_window(at_hour(19, 59), wrap)
    assert in_window(at_hour(9), day)
    assert not in_window(at_hour(17), day)


def _granted_consent(**scope_overrides: object) -> Consent:
    scope = ConsentScope(from_account_id="acc_ana", pix_key=MARIA, amount_centavos=100)
    if scope_overrides:
        scope = scope.model_copy(update=scope_overrides)
    return Consent(
        consent_id="cons_ok",
        customer_id="cus_ana",
        scope=scope,
        status=ConsentStatus.GRANTED,
        created_at=START,
        expires_at=START + timedelta(seconds=300),
    )


@pytest.mark.parametrize(
    ("consent", "amount", "pix_key", "from_account", "reason"),
    [
        (None, 100, MARIA, "acc_ana", "NOT_FOUND"),
        (
            _granted_consent().model_copy(
                update={"consent_id": "cons_other", "customer_id": "cus_external"}
            ),
            100,
            MARIA,
            "acc_ana",
            "NOT_FOUND",
        ),
        (
            _granted_consent().model_copy(update={"status": ConsentStatus.PENDING}),
            100,
            MARIA,
            "acc_ana",
            "NOT_GRANTED",
        ),
        (
            _granted_consent().model_copy(update={"expires_at": START}),
            100,
            MARIA,
            "acc_ana",
            "EXPIRED",
        ),
        (
            _granted_consent().model_copy(
                update={"status": ConsentStatus.USED, "used_by_transfer_id": "tx_x"}
            ),
            100,
            MARIA,
            "acc_ana",
            "ALREADY_USED",
        ),
        (_granted_consent(from_account_id="acc_external"), 100, MARIA, "acc_ana", "SCOPE_MISMATCH"),
        (_granted_consent(pix_key=JOAO), 100, MARIA, "acc_ana", "SCOPE_MISMATCH"),
        (_granted_consent(amount_centavos=200), 100, MARIA, "acc_ana", "SCOPE_MISMATCH"),
    ],
)
def test_consent_validity_each_condition(
    consent: Consent | None,
    amount: int,
    pix_key: str,
    from_account: str,
    reason: str,
) -> None:
    consents = {consent.consent_id: consent} if consent is not None else {}
    state = _state(consents=consents)
    cid = consent.consent_id if consent is not None else "cons_missing"
    ok, got = consent_validity(state, cid, from_account, pix_key, amount)
    assert ok is False
    assert got == reason


def test_consent_validity_success() -> None:
    consent = _granted_consent()
    state = _state(consents={consent.consent_id: consent})
    assert consent_validity(state, consent.consent_id, "acc_ana", MARIA, 100) == (True, None)


def test_evaluate_transfer_policy_order_and_no_mutation() -> None:
    night = START.replace(hour=23)
    state = _state(
        policy=PolicyConfig(
            consent_required=True,
            blocked_pix_keys=[BLOCKED],
            new_beneficiary_cooling_seconds=60,
        ),
        start=night,
        kyc=KycLevel.BASIC,
    )
    before = state.hash()
    decision = evaluate_transfer_policy(state, "acc_ana", BLOCKED, 600_000, None)
    assert state.hash() == before
    rules = [finding.rule for finding in decision.findings]
    assert rules == sorted(rules, key=lambda rule: list(PolicyRuleId).index(rule))
    assert PolicyRuleId.PER_TRANSFER_LIMIT in rules
    assert PolicyRuleId.NIGHT_LIMIT in rules
    assert PolicyRuleId.KYC_AMOUNT_CAP in rules
    assert PolicyRuleId.BLOCKED_RECIPIENT in rules
    assert PolicyRuleId.NEW_BENEFICIARY_COOLING in rules
    assert PolicyRuleId.STEP_UP_REQUIRED in rules
    assert PolicyRuleId.CONSENT_REQUIRED in rules
    assert decision.allowed is False
    assert all(finding.mode == EnforcementMode.HARD for finding in decision.hard)
