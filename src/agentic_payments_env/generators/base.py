"""Seeded RNG and generator parameters. M3 T3.01.

Satisfies: AGENTS.md seeded RNG (no uuid4 / time.now); money stays int.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from typing import TypeVar

from pydantic import Field

from agentic_payments_env.contracts.common import FaultKind, FrozenModel, TaskFamily

T = TypeVar("T")


class SeededRng:
    """``random.Random(seed)`` wrapper. No module-level ``random.random()``."""

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    def randint(self, a: int, b: int) -> int:
        return self._rng.randint(a, b)

    def randrange(self, start: int, stop: int | None = None, step: int = 1) -> int:
        if stop is None:
            return self._rng.randrange(start)
        return self._rng.randrange(start, stop, step)

    def choice(self, seq: Sequence[T]) -> T:
        return self._rng.choice(seq)

    def sample(self, population: Sequence[T], k: int) -> list[T]:
        return self._rng.sample(list(population), k)


class GenParams(FrozenModel):
    """Integer-only knobs for a generated task. T3.01."""

    family: TaskFamily
    amount_limit_ratio_numer: int = Field(ge=1)
    amount_limit_ratio_denom: int = Field(ge=1)
    n_recipients: int = Field(ge=1)
    name_collision: bool = False
    portuguese: bool = False
    fault_kind: FaultKind | None = None
    fault_ordinal: int = Field(default=1, ge=1)
