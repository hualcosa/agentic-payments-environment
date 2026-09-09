"""Invariant fuzz and strict-mode ledger guard. REQ-DOM-19, REQ-TEST-03."""

from __future__ import annotations

import random

import pytest

from agentic_payments_env.contracts.actions import Action
from agentic_payments_env.environment import PaymentsEnvironment
from agentic_payments_env.errors import InvariantViolation
from agentic_payments_env.world import WorldState
from tests.conftest import default_task

TOOLS = [
    "get_customer_profile",
    "get_account_balance",
    "list_beneficiaries",
    "lookup_pix_key",
    "check_transfer_policy",
    "add_beneficiary",
    "request_consent",
    "request_step_up_auth",
    "create_transfer",
    "get_transfer",
    "get_transfer_by_idempotency_key",
    "list_transfers",
    "reverse_transfer",
    "ask_user",
    "finish",
]


def random_action(rng: random.Random, env: PaymentsEnvironment) -> Action:
    tool = TOOLS[rng.randrange(len(TOOLS))]
    plausible = rng.random() < 0.7
    keys = list(env.state.pix_directory)
    accounts = list(env.state.accounts)
    transfers = list(env.state.transfers)
    pool = [f"k{i}" for i in range(5)]
    if not plausible:
        return Action(tool_name=tool, arguments={"garbage": "x", "amount_centavos": -1})
    if tool in {"get_customer_profile", "list_beneficiaries", "request_step_up_auth"}:
        arguments: dict[str, object] = {}
    elif tool == "get_account_balance":
        arguments = {"account_id": rng.choice(accounts)}
    elif tool == "lookup_pix_key":
        arguments = {"pix_key": rng.choice(keys)}
    elif tool == "check_transfer_policy":
        arguments = {
            "from_account_id": "acc_ana",
            "pix_key": rng.choice(keys),
            "amount_centavos": rng.choice([100, 500_001]),
        }
    elif tool == "add_beneficiary":
        arguments = {"pix_key": rng.choice(keys), "nickname": "N"}
    elif tool == "request_consent":
        arguments = {
            "from_account_id": "acc_ana",
            "pix_key": rng.choice(keys),
            "amount_centavos": 100,
            "description": "d",
        }
    elif tool == "create_transfer":
        arguments = {
            "from_account_id": "acc_ana",
            "pix_key": rng.choice(keys),
            "amount_centavos": 100,
            "idempotency_key": rng.choice(pool),
        }
    elif tool == "get_transfer":
        arguments = {"transfer_id": rng.choice(transfers) if transfers else "tx_missing"}
    elif tool == "get_transfer_by_idempotency_key":
        arguments = {"idempotency_key": rng.choice(pool)}
    elif tool == "list_transfers":
        arguments = {"account_id": "acc_ana", "limit": 20}
    elif tool == "reverse_transfer":
        arguments = {
            "transfer_id": rng.choice(transfers) if transfers else "tx_missing",
            "reason": "undo",
        }
    elif tool == "ask_user":
        arguments = {"question": "why?"}
    else:
        arguments = {"outcome": rng.choice(["COMPLETED", "DECLINED", "BLOCKED"]), "report": "r"}
    return Action(tool_name=tool, arguments=arguments)


def _permissive_task():
    task = default_task()
    world = task.world.model_copy(
        update={
            "policy": task.world.policy.model_copy(
                update={"consent_required": False, "step_up_threshold_centavos": None}
            )
        }
    )
    return task.model_copy(update={"world": world})


def test_invariant_fuzz_200x15() -> None:
    for seed in range(200):
        rng = random.Random(seed)
        env = PaymentsEnvironment(default_task(), seed, strict=True)
        env.reset()
        for _ in range(15):
            env.step(random_action(rng, env))
            if env.done:
                break


@pytest.mark.parametrize(
    ("mutator_name", "mutator"),
    [
        (
            "one_entry",
            lambda state: setattr(state, "ledger", state.ledger[: state._fixture_entry_count + 1]),
        ),
        (
            "three_entries",
            lambda state: state.ledger.append(
                state.ledger[state._fixture_entry_count].model_copy(
                    update={"entry_id": "led_extra"}
                )
            ),
        ),
        (
            "zero_delta",
            lambda state: state.ledger.__setitem__(
                state._fixture_entry_count,
                state.ledger[state._fixture_entry_count].model_copy(
                    update={"delta_centavos": 0}
                ),
            ),
        ),
        (
            "wrong_account",
            lambda state: state.ledger.__setitem__(
                state._fixture_entry_count,
                state.ledger[state._fixture_entry_count].model_copy(
                    update={"account_id": "acc_external"}
                ),
            ),
        ),
    ],
)
def test_inv_02_rejects_bad_ledger_shapes(
    mutator_name: str, mutator: object
) -> None:
    del mutator_name
    env = PaymentsEnvironment(_permissive_task(), 0, strict=False)
    env.reset()
    env.step(
        Action(
            tool_name="create_transfer",
            arguments={
                "from_account_id": "acc_ana",
                "pix_key": "maria.oliveira@example.com",
                "amount_centavos": 100,
                "idempotency_key": "inv02",
            },
        )
    )
    assert len(env.state.ledger) > env.state._fixture_entry_count
    mutator(env.state)  # type: ignore[operator]
    with pytest.raises(InvariantViolation) as exc:
        env.state.check_invariants()
    assert exc.value.code == "INV-02"


def test_inv_04_rejects_late_creation_audit() -> None:
    env = PaymentsEnvironment(_permissive_task(), 0, strict=False)
    env.reset()
    env.step(
        Action(
            tool_name="create_transfer",
            arguments={
                "from_account_id": "acc_ana",
                "pix_key": "maria.oliveira@example.com",
                "amount_centavos": 100,
                "idempotency_key": "inv04",
            },
        )
    )
    transfer_id = next(
        tid for tid in env.state.transfers if tid not in env.state._fixture_transfer_ids
    )
    env.state.audit = [
        event
        for event in env.state.audit
        if not (event.kind == "TRANSFER_CREATED" and transfer_id in event.entity_ids)
    ]
    env.state.audit.append(
        env.state.audit[-1].model_copy(
            update={
                "seq": len(env.state.audit) + 1,
                "step_index": env.state.audit[-1].step_index + 1,
                "kind": "TRANSFER_CREATED",
                "entity_ids": [transfer_id],
            }
        )
    )
    with pytest.raises(InvariantViolation) as exc:
        env.state.check_invariants()
    assert exc.value.code == "INV-04"


def test_strict_raises_when_post_transfer_skips_ledger(monkeypatch: pytest.MonkeyPatch) -> None:
    original = WorldState.post_transfer

    def broken(self: WorldState, transfer: object) -> object:
        completed = original(self, transfer)  # type: ignore[arg-type]
        self.ledger = self.ledger[:-2]
        return completed

    monkeypatch.setattr(WorldState, "post_transfer", broken)
    env = PaymentsEnvironment(_permissive_task(), 0, strict=True)
    env.reset()
    with pytest.raises(InvariantViolation):
        env.step(
            Action(
                tool_name="create_transfer",
                arguments={
                    "from_account_id": "acc_ana",
                    "pix_key": "maria.oliveira@example.com",
                    "amount_centavos": 100,
                    "idempotency_key": "fuzz",
                },
            )
        )
