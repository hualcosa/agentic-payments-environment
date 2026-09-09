"""Authorization and misc tool tests."""

from __future__ import annotations

from datetime import timedelta

from agentic_payments_env.contracts.actions import Action, ToolErrorCode
from agentic_payments_env.contracts.common import ConsentStatus, EpisodeOutcome
from agentic_payments_env.contracts.domain import PolicyConfig
from agentic_payments_env.contracts.tasks import (
    ConsentResponse,
    ExpectedTransfer,
    OracleStep,
    StepUpResponse,
    TaskHidden,
    UserScript,
)
from agentic_payments_env.simulated_user import SimulatedUser
from agentic_payments_env.tools.dispatch import ToolContext, dispatch
from agentic_payments_env.tools.read import handle_get_customer_profile
from agentic_payments_env.tools.schemas import GetCustomerProfileArgs
from agentic_payments_env.world import WorldState
from tests.conftest import START, default_world_fixture

MARIA = "maria.oliveira@example.com"
JOAO = "joao.pereira@example.com"


def _hidden() -> TaskHidden:
    return TaskHidden(
        expected_outcome=EpisodeOutcome.COMPLETED,
        expected_transfers=[ExpectedTransfer(pix_key=MARIA, amount_centavos=100)],
        oracle_plan=[OracleStep(tool_name="finish")],
        oracle_steps=1,
    )


def _ctx(script: UserScript, *, ttl: int = 300) -> ToolContext:
    fixture = default_world_fixture().model_copy(
        update={"policy": PolicyConfig(step_up_ttl_seconds=ttl, consent_ttl_seconds=ttl)}
    )
    return ToolContext(
        state=WorldState.from_fixture(fixture),
        sim_user=SimulatedUser(script, _hidden()),
        step_index=1,
        task_id="v0/auth",
    )


def _call(ctx: ToolContext, tool: str, arguments: dict[str, object] | None = None):
    return dispatch(ctx, Action(tool_name=tool, arguments=arguments or {}), None)


def test_consent_granted_denied_pending_audit_and_ttl() -> None:
    granted = _ctx(UserScript(consent_responses=[ConsentResponse.GRANT]))
    obs = _call(
        granted,
        "request_consent",
        {
            "from_account_id": "acc_ana",
            "pix_key": MARIA,
            "amount_centavos": 100,
            "description": "pay maria",
        },
    )
    assert obs.result is not None
    assert obs.result["status"] == ConsentStatus.GRANTED.value
    assert obs.result["expires_at"] == (START + timedelta(seconds=300)).isoformat()
    kinds = [event.kind for event in granted.state.audit]
    assert kinds.count("CONSENT_REQUESTED") == 1
    assert kinds.count("CONSENT_GRANTED") == 1

    denied = _ctx(UserScript(consent_responses=[ConsentResponse.DENY]))
    obs_d = _call(
        denied,
        "request_consent",
        {
            "from_account_id": "acc_ana",
            "pix_key": MARIA,
            "amount_centavos": 100,
            "description": "pay maria",
        },
    )
    assert obs_d.result is not None
    assert obs_d.result["status"] == ConsentStatus.DENIED.value
    assert "CONSENT_DENIED" in [event.kind for event in denied.state.audit]

    pending = _ctx(UserScript(consent_responses=[ConsentResponse.NO_RESPONSE]))
    obs_p = _call(
        pending,
        "request_consent",
        {
            "from_account_id": "acc_ana",
            "pix_key": MARIA,
            "amount_centavos": 100,
            "description": "pay maria",
        },
    )
    assert obs_p.result is not None
    assert obs_p.result["status"] == ConsentStatus.PENDING.value


def test_step_up_approve_then_ttl_expires() -> None:
    ctx = _ctx(UserScript(step_up_responses=[StepUpResponse.APPROVE]), ttl=5)
    obs = _call(ctx, "request_step_up_auth")
    assert obs.result is not None
    assert obs.result["status"] == "APPROVED"
    assert obs.result["auth_level"] == "STEP_UP"
    profile = handle_get_customer_profile(ctx, GetCustomerProfileArgs(), None)
    assert profile.result is not None
    assert profile.result["auth_level"] == "STEP_UP"
    ctx.state.tick()
    profile_after = handle_get_customer_profile(ctx, GetCustomerProfileArgs(), None)
    assert profile_after.result is not None
    assert profile_after.result["auth_level"] == "BASIC"


def test_add_beneficiary_duplicate_key() -> None:
    ctx = _ctx(UserScript())
    first = _call(ctx, "add_beneficiary", {"pix_key": JOAO, "nickname": "Joao"})
    assert first.result is not None
    assert first.result["trusted"] is False
    dup = _call(ctx, "add_beneficiary", {"pix_key": JOAO, "nickname": "Joao again"})
    assert dup.error is not None
    assert dup.error.code == ToolErrorCode.INVALID_ARGUMENT


def test_ask_user_consumes_script() -> None:
    ctx = _ctx(UserScript(clarification_responses=["one", "two"]))
    assert _call(ctx, "ask_user", {"question": "q1"}).result == {"reply": "one"}
    assert _call(ctx, "ask_user", {"question": "q2"}).result == {"reply": "two"}


def test_finish_returns_final_kind() -> None:
    ctx = _ctx(UserScript())
    obs = _call(ctx, "finish", {"outcome": "COMPLETED", "report": "done"})
    assert obs.kind == "final"
    assert obs.result == {"outcome": "COMPLETED", "report": "done"}
    again = _call(ctx, "get_customer_profile")
    assert again.error is not None
    assert again.error.code == ToolErrorCode.EPISODE_FINISHED
