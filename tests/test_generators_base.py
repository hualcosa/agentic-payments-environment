"""Tests for SeededRng and GenParams. T3.01."""

from __future__ import annotations

from agentic_payments_env.contracts.common import TaskFamily
from agentic_payments_env.generators.base import GenParams, SeededRng


def test_seeded_rng_is_deterministic_and_seed_sensitive() -> None:
    first = SeededRng(0)
    second = SeededRng(0)
    other = SeededRng(1)
    seq_a = [first.randint(0, 10) for _ in range(8)]
    seq_b = [second.randint(0, 10) for _ in range(8)]
    seq_c = [other.randint(0, 10) for _ in range(8)]
    assert seq_a == seq_b
    assert seq_a != seq_c


def test_gen_params_int_ratios() -> None:
    params = GenParams(
        family=TaskFamily.ROUTINE_TRANSFER,
        amount_limit_ratio_numer=1,
        amount_limit_ratio_denom=2,
        n_recipients=1,
    )
    assert params.amount_limit_ratio_numer == 1
    assert params.fault_kind is None


def test_pick_recipients_respects_count() -> None:
    from agentic_payments_env.generators.base import pick_recipients

    params = GenParams(
        family=TaskFamily.ROUTINE_TRANSFER,
        amount_limit_ratio_numer=1,
        amount_limit_ratio_denom=2,
        n_recipients=2,
    )
    recipients = pick_recipients(SeededRng(0), params)
    assert len(recipients) == 2
