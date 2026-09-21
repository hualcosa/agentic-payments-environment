"""WorldState construction, invariants, tick, and hashing."""

from __future__ import annotations

from datetime import timedelta

import pytest

from agentic_payments_env.contracts.common import ActorKind, TransferStatus
from agentic_payments_env.contracts.domain import Transfer
from agentic_payments_env.contracts.world import WorldFixture
from agentic_payments_env.errors import InvariantViolation
from agentic_payments_env.world import WorldState
from tests.conftest import START, default_world_fixture


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
    state._record_creation(entity_id="tx_a", step_index=1, kind="TRANSFER_CREATED")
    state._record_creation(entity_id="tx_b", step_index=1, kind="TRANSFER_CREATED")
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
