"""Tests for the adversarial generator. T3.05."""

from __future__ import annotations

from agentic_payments_env.agents.presets import build
from agentic_payments_env.benchmark.runner import _drive
from agentic_payments_env.contracts.common import TaskFamily
from agentic_payments_env.generators.adversarial import generate_adversarial
from agentic_payments_env.generators.base import GenParams, InjectionPlacement, SeededRng
from agentic_payments_env.graders import grade_episode
from tests.conftest import run_oracle


def _params(**updates: object) -> GenParams:
    base: dict[str, object] = {
        "family": TaskFamily.ADVERSARIAL,
        "amount_limit_ratio_numer": 1,
        "amount_limit_ratio_denom": 20,
        "n_recipients": 1,
    }
    base.update(updates)
    return GenParams(**base)  # type: ignore[arg-type]


def test_generate_adversarial_oracle_ok_obedient_unsafe() -> None:
    task = generate_adversarial(SeededRng(0), _params(), "v1/gen-adv-001")
    assert task.hidden.injection_targets
    trace, state = run_oracle(task)
    oracle_result = grade_episode(task, trace, state)
    assert oracle_result.safe_success is True
    assert oracle_result.violations == []
    env, obedient_trace = _drive(task, build("obedient", task), 0)
    obedient = grade_episode(task, obedient_trace, env.state)
    assert obedient.safe_success is False


def test_adversarial_holder_name_placement() -> None:
    nickname = generate_adversarial(
        SeededRng(0),
        _params(injection_placement=InjectionPlacement.NICKNAME),
        "v1/gen-adv-nick",
    )
    holder = generate_adversarial(
        SeededRng(0),
        _params(injection_placement=InjectionPlacement.HOLDER_NAME),
        "v1/gen-adv-holder",
    )
    assert nickname.world.pix_directory != holder.world.pix_directory


def test_adversarial_seed_changes_amount() -> None:
    a = generate_adversarial(SeededRng(0), _params(), "v1/gen-adv-a")
    b = generate_adversarial(SeededRng(1), _params(), "v1/gen-adv-b")
    assert (
        a.hidden.expected_transfers[0].amount_centavos
        != b.hidden.expected_transfers[0].amount_centavos
    )
