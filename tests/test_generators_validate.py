"""Tests for generated-task validity. T3.06."""

from __future__ import annotations

from agentic_payments_env.benchmark.v0 import load_task
from agentic_payments_env.contracts.common import TaskFamily
from agentic_payments_env.generators.base import GenParams, SeededRng
from agentic_payments_env.generators.routine import generate_routine
from agentic_payments_env.generators.validate import is_valid


def test_v0_rt001_is_valid() -> None:
    assert is_valid(load_task("v0/rt-001")) is True


def test_generated_routine_is_valid() -> None:
    task = generate_routine(
        SeededRng(0),
        GenParams(
            family=TaskFamily.ROUTINE_TRANSFER,
            amount_limit_ratio_numer=1,
            amount_limit_ratio_denom=20,
            n_recipients=1,
        ),
        "v1/gen-rt-001",
    )
    assert is_valid(task) is True
