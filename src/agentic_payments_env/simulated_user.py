"""Scripted simulated user for consent, step-up, and clarification.

Satisfies: REQ-ENV-12, REQ-ENV-13, REQ-ENV-14.
"""

from __future__ import annotations

from agentic_payments_env.contracts.domain import ConsentScope
from agentic_payments_env.contracts.tasks import (
    ConsentResponse,
    StepUpResponse,
    TaskHidden,
    UserScript,
    UserVigilance,
)


class SimulatedUser:
    """Consumes a UserScript; sole holder of ``task.hidden``. REQ-ENV-12, REQ-ENV-13."""

    def __init__(self, script: UserScript, hidden: TaskHidden) -> None:
        self._script = script
        self._hidden = hidden
        self._consent_index = 0
        self._step_up_index = 0
        self._clarification_index = 0

    def respond_consent(self, scope: ConsentScope) -> ConsentResponse:
        """Next consent response, or DENY on vigilance mismatch without consuming. REQ-ENV-14."""
        if self._script.vigilance == UserVigilance.DENY_IF_SCOPE_MISMATCH:
            expected = {
                (item.pix_key, item.amount_centavos) for item in self._hidden.expected_transfers
            }
            if (scope.pix_key, scope.amount_centavos) not in expected:
                return ConsentResponse.DENY
        responses = self._script.consent_responses
        index = min(self._consent_index, len(responses) - 1)
        self._consent_index += 1
        return responses[index]

    def respond_step_up(self) -> StepUpResponse:
        """Return the next step-up response; last entry repeats. REQ-ENV-13."""
        responses = self._script.step_up_responses
        index = min(self._step_up_index, len(responses) - 1)
        self._step_up_index += 1
        return responses[index]

    def respond_clarification(self, question: str) -> str:
        """Return the next clarification string; last entry repeats. REQ-ENV-13."""
        del question
        responses = self._script.clarification_responses
        index = min(self._clarification_index, len(responses) - 1)
        self._clarification_index += 1
        return responses[index]
