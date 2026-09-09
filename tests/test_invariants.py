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


def test_invariant_fuzz_200x15() -> None:
    for seed in range(200):
        rng = random.Random(seed)
        env = PaymentsEnvironment(default_task(), seed, strict=True)
        env.reset()
        for _ in range(15):
            env.step(random_action(rng, env))
            if env.done:
                break


def test_strict_raises_when_post_transfer_skips_ledger(monkeypatch: pytest.MonkeyPatch) -> None:
    original = WorldState.post_transfer

    def broken(self: WorldState, transfer: object) -> object:
        completed = original(self, transfer)  # type: ignore[arg-type]
        self.ledger = self.ledger[:-2]
        return completed

    monkeypatch.setattr(WorldState, "post_transfer", broken)
    task = default_task()
    world = task.world.model_copy(
        update={
            "policy": task.world.policy.model_copy(
                update={"consent_required": False, "step_up_threshold_centavos": None}
            )
        }
    )
    task = task.model_copy(update={"world": world})
    env = PaymentsEnvironment(task, 0, strict=True)
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
