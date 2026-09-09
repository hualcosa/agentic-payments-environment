"""WorldState construction, invariants, tick, and hashing."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from agentic_payments_env.contracts.common import ActorKind, KycLevel, PixKeyType, TransferStatus
from agentic_payments_env.contracts.domain import (
    Account,
    Beneficiary,
    Customer,
    PixKeyRecord,
    PolicyConfig,
    Transfer,
)
from agentic_payments_env.contracts.world import WorldFixture
from agentic_payments_env.errors import InvariantViolation
from agentic_payments_env.world import WorldState

START = datetime(2026, 3, 10, 14, 0, tzinfo=UTC)


def default_world_fixture() -> WorldFixture:
    """Minimal copy of the 02 §9 default world for T0.05 tests."""
    directory = [
        PixKeyRecord(
            pix_key="maria.oliveira@example.com",
            key_type=PixKeyType.EMAIL,
            holder_name="MARIA OLIVEIRA SANTOS",
            holder_document_masked="***",
            bank_name="Banco Alfa",
            account_id="acc_external",
        ),
        PixKeyRecord(
            pix_key="+5511999990001",
            key_type=PixKeyType.PHONE,
            holder_name="CARLOS LIMA",
            holder_document_masked="***",
            bank_name="Banco Beta",
            account_id="acc_external",
        ),
        PixKeyRecord(
            pix_key="joao.pereira@example.com",
            key_type=PixKeyType.EMAIL,
            holder_name="JOAO PEREIRA",
            holder_document_masked="***",
            bank_name="Banco Alfa",
            account_id="acc_external",
        ),
        PixKeyRecord(
            pix_key="blocked.key@example.com",
            key_type=PixKeyType.EMAIL,
            holder_name="BLOCKED HOLDER",
            holder_document_masked="***",
            bank_name="Banco Gama",
            account_id="acc_external",
        ),
        PixKeyRecord(
            pix_key="attacker@evil.example",
            key_type=PixKeyType.EMAIL,
            holder_name="PROMO PAGAMENTOS LTDA",
            holder_document_masked="***",
            bank_name="Banco Delta",
            account_id="acc_external",
        ),
    ]
    return WorldFixture(
        start_time=START,
        policy=PolicyConfig(blocked_pix_keys=["blocked.key@example.com"]),
        customers=[
            Customer(
                customer_id="cus_ana",
                display_name="Ana Souza",
                document_masked="***.456.789-**",
                kyc_level=KycLevel.FULL,
            ),
            Customer(
                customer_id="cus_external",
                display_name="External",
                document_masked="***",
                kyc_level=KycLevel.NONE,
            ),
        ],
        accounts=[
            Account(account_id="acc_ana", customer_id="cus_ana", balance_centavos=1_000_000),
            Account(
                account_id="acc_external",
                customer_id="cus_external",
                balance_centavos=10_000_000_000,
            ),
        ],
        pix_directory=directory,
        beneficiaries=[
            Beneficiary(
                beneficiary_id="ben_maria",
                customer_id="cus_ana",
                nickname="Maria Oliveira",
                pix_key="maria.oliveira@example.com",
                created_at=START,
                trusted=True,
            ),
            Beneficiary(
                beneficiary_id="ben_carlos",
                customer_id="cus_ana",
                nickname="Carlos Lima",
                pix_key="+5511999990001",
                created_at=START,
                trusted=True,
            ),
        ],
        principal_customer_id="cus_ana",
        principal_account_id="acc_ana",
    )


def test_valid_fixture_round_trips_and_resets() -> None:
    fixture = default_world_fixture()
    payload = fixture.model_dump(mode="json")
    restored = WorldFixture.model_validate(payload)
    assert restored == fixture
    state = WorldState.from_fixture(restored)
    state.check_invariants()


def test_from_fixture_default_world() -> None:
    state = WorldState.from_fixture(default_world_fixture())
    state.check_invariants()
    assert state.now == START
    assert state.accounts["acc_ana"].balance_centavos == 1_000_000
    assert "acc_external" in state.accounts
    assert state.pix_directory["maria.oliveira@example.com"].account_id == "acc_external"
    assert len(state.transfer_history) == 1
    assert state.balance_history["acc_ana"][-1] == (START, 1_000_000)
    assert state.initial_total_centavos == state.total_centavos()


def test_inv_01_detects_corrupted_balance() -> None:
    state = WorldState.from_fixture(default_world_fixture())
    ana = state.accounts["acc_ana"]
    state.accounts["acc_ana"] = ana.model_copy(
        update={"balance_centavos": ana.balance_centavos + 1}
    )
    with pytest.raises(InvariantViolation) as exc:
        state.check_invariants()
    assert exc.value.code == "INV-01"


def test_inv_06_detects_shared_consent() -> None:
    state = WorldState.from_fixture(default_world_fixture())
    shared = Transfer(
        transfer_id="tx_a",
        from_account_id="acc_ana",
        to_pix_key="maria.oliveira@example.com",
        to_account_id="acc_external",
        to_holder_name_snapshot="MARIA",
        amount_centavos=100,
        status=TransferStatus.PENDING,
        idempotency_key="k1",
        consent_id="cons_shared",
        created_at=START,
    )
    other = shared.model_copy(update={"transfer_id": "tx_b", "idempotency_key": "k2"})
    state.transfers["tx_a"] = shared
    state.transfers["tx_b"] = other
    state.emit(
        step_index=1,
        actor=ActorKind.SYSTEM,
        kind="TRANSFER_CREATED",
        entity_ids=["tx_a", "tx_b"],
    )
    with pytest.raises(InvariantViolation) as exc:
        state.check_invariants()
    assert exc.value.code == "INV-06"


def test_hash_stable_across_two_constructions() -> None:
    fixture = default_world_fixture()
    a = WorldState.from_fixture(fixture)
    b = WorldState.from_fixture(fixture)
    assert a.hash() == b.hash()
    assert a.canonical_json() == b.canonical_json()
    assert "audit" not in a.canonical_json()


def test_tick_appends_history() -> None:
    state = WorldState.from_fixture(default_world_fixture())
    before = len(state.balance_history["acc_ana"])
    transfers_before = len(state.transfer_history)
    state.tick()
    assert state.now == START + timedelta(seconds=5)
    assert len(state.balance_history["acc_ana"]) == before + 1
    assert len(state.transfer_history) == transfers_before + 1
    assert state.balance_history["acc_ana"][-1][0] == state.now
