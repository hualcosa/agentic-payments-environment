"""Agent protocol. REQ-CON-10."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from agentic_payments_env.contracts.actions import Action, Observation
from agentic_payments_env.contracts.tasks import TaskPublic
from agentic_payments_env.contracts.trace import Step


class Agent(Protocol):
    name: str

    def reset(self, public: TaskPublic, reset_observation: Observation) -> None: ...

    def act(self, history: Sequence[Step], last_observation: Observation) -> Action: ...
