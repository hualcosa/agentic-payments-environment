"""Tests for difficulty scoring and curriculum order. T3.07."""

from __future__ import annotations

from agentic_payments_env.contracts.common import TaskFamily
from agentic_payments_env.generators.base import GenParams, SeededRng
from agentic_payments_env.generators.difficulty import curriculum_order, difficulty_score
from agentic_payments_env.generators.routine import generate_routine


def _routine(*, numer: int, denom: int, task_id: str, portuguese: bool = False):
    return generate_routine(
        SeededRng(0),
        GenParams(
            family=TaskFamily.ROUTINE_TRANSFER,
            amount_limit_ratio_numer=numer,
            amount_limit_ratio_denom=denom,
            n_recipients=1,
            portuguese=portuguese,
        ),
        task_id,
    )


def test_difficulty_increases_with_amount_ratio() -> None:
    easy = _routine(numer=1, denom=20, task_id="v1/a")
    hard = _routine(numer=1, denom=2, task_id="v1/b")
    assert difficulty_score(easy) < difficulty_score(hard)


def test_curriculum_order_stable_by_score_then_id() -> None:
    first = _routine(numer=1, denom=20, task_id="v1/z")
    second = _routine(numer=1, denom=20, task_id="v1/a")
    third = _routine(numer=1, denom=2, task_id="v1/m")
    ordered = curriculum_order([third, first, second])
    assert [task.task_id for task in ordered] == ["v1/a", "v1/z", "v1/m"]
    again = curriculum_order([third, first, second])
    assert [task.task_id for task in again] == [task.task_id for task in ordered]
