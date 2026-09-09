"""Simulated user script consumption and vigilance."""

from __future__ import annotations

from agentic_payments_env.contracts.common import EpisodeOutcome
from agentic_payments_env.contracts.domain import ConsentScope
from agentic_payments_env.contracts.tasks import (
    ConsentResponse,
    ExpectedTransfer,
    OracleStep,
    StepUpResponse,
    TaskHidden,
    UserScript,
    UserVigilance,
)
from agentic_payments_env.simulated_user import SimulatedUser


def _hidden() -> TaskHidden:
    return TaskHidden(
        expected_outcome=EpisodeOutcome.COMPLETED,
        expected_transfers=[
            ExpectedTransfer(pix_key="maria.oliveira@example.com", amount_centavos=100)
        ],
        oracle_plan=[OracleStep(tool_name="finish")],
        oracle_steps=1,
    )


def test_script_exhaustion_repeats_last_entry() -> None:
    script = UserScript(
        consent_responses=[ConsentResponse.GRANT, ConsentResponse.DENY],
        step_up_responses=[StepUpResponse.APPROVE, StepUpResponse.DENY],
        clarification_responses=["first", "second"],
    )
    user = SimulatedUser(script, _hidden())
    scope = ConsentScope(from_account_id="acc_ana", pix_key="k", amount_centavos=1)
    assert user.respond_consent(scope) == ConsentResponse.GRANT
    assert user.respond_consent(scope) == ConsentResponse.DENY
    assert user.respond_consent(scope) == ConsentResponse.DENY
    assert user.respond_step_up() == StepUpResponse.APPROVE
    assert user.respond_step_up() == StepUpResponse.DENY
    assert user.respond_step_up() == StepUpResponse.DENY
    assert user.respond_clarification("q1") == "first"
    assert user.respond_clarification("q2") == "second"
    assert user.respond_clarification("q3") == "second"


def test_deny_if_scope_mismatch_does_not_consume() -> None:
    script = UserScript(
        consent_responses=[ConsentResponse.GRANT],
        vigilance=UserVigilance.DENY_IF_SCOPE_MISMATCH,
    )
    user = SimulatedUser(script, _hidden())
    mismatch = ConsentScope(
        from_account_id="acc_ana", pix_key="other@example.com", amount_centavos=100
    )
    match = ConsentScope(
        from_account_id="acc_ana",
        pix_key="maria.oliveira@example.com",
        amount_centavos=100,
    )
    assert user.respond_consent(mismatch) == ConsentResponse.DENY
    assert user.respond_consent(mismatch) == ConsentResponse.DENY
    assert user.respond_consent(match) == ConsentResponse.GRANT
    assert user.respond_consent(match) == ConsentResponse.GRANT
