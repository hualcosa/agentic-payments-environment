"""Tests for preference pairs. T4.03."""

from __future__ import annotations

from agentic_payments_env.agents.presets import build
from agentic_payments_env.benchmark.runner import _drive
from agentic_payments_env.benchmark.v0 import load_task
from agentic_payments_env.graders import grade_episode
from agentic_payments_env.rewards.pairs import oracle_vs_scripted_pairs, prefer, rank_key
from tests.conftest import run_oracle


def test_oracle_preferred_to_quitter_on_rt001() -> None:
    task = load_task("v0/rt-001")
    oracle_trace, oracle_state = run_oracle(task)
    oracle = grade_episode(task, oracle_trace, oracle_state)
    env, quit_trace = _drive(task, build("quitter", task), 0)
    quitter = grade_episode(task, quit_trace, env.state)
    assert prefer(oracle, quitter) == "A"
    assert rank_key(oracle) > rank_key(quitter)


def test_liar_not_preferred_to_oracle() -> None:
    pairs = oracle_vs_scripted_pairs(["v0/pc-001"], ["liar"])
    assert ("oracle", "liar") in pairs
    assert ("liar", "oracle") not in pairs
