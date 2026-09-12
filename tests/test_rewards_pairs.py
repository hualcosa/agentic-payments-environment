"""Tests for preference pairs and export. T4.03."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentic_payments_env.agents.presets import build
from agentic_payments_env.benchmark.runner import _drive
from agentic_payments_env.benchmark.v0 import load_task
from agentic_payments_env.benchmark.v1 import all_tasks as all_v1
from agentic_payments_env.benchmark.v1_1 import all_tasks as all_v11
from agentic_payments_env.contracts.training import PreferenceRecord
from agentic_payments_env.graders import grade_episode
from agentic_payments_env.rewards.pairs import (
    assert_training_task_id,
    build_preference_records,
    dumps_preferences,
    export_preferences,
    oracle_vs_scripted_pairs,
    prefer,
    rank_key,
    training_task_ids,
)
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


def test_preference_record_validates() -> None:
    record = PreferenceRecord(
        task_id="v0/rt-001",
        chosen_agent="oracle",
        rejected_agent="quitter",
        chosen_actions=[{"tool_name": "finish", "arguments": {}}],
        rejected_actions=[{"tool_name": "finish", "arguments": {}}],
        rank_key_chosen=(True, 0, 500),
        rank_key_rejected=(False, 0, 0),
        provenance="oracle_vs_scripted",
    )
    assert record.chosen_agent == "oracle"


def test_preference_records_include_both_action_traces() -> None:
    records = build_preference_records(["v0/rt-001"], scripted_names=("quitter",))
    assert records
    assert records[0].chosen_actions
    assert records[0].rejected_actions
    assert all(
        "tool_name" in action and "arguments" in action for action in records[0].chosen_actions
    )


def test_preference_records_support_explicit_agent_pairs() -> None:
    records = build_preference_records(
        ["v0/rt-001"],
        agent_pairs=(("obedient", "quitter"),),
    )
    assert len(records) == 1
    assert (records[0].chosen_agent, records[0].rejected_agent) == ("obedient", "quitter")
    assert records[0].provenance == "agent_vs_agent"


def test_held_out_task_rejected_for_training_export() -> None:
    with pytest.raises(ValueError, match="held-out"):
        assert_training_task_id(all_v1()[0].task_id)
    with pytest.raises(ValueError, match="held-out"):
        assert_training_task_id(all_v11()[0].task_id)


def test_training_task_ids_exclude_held_out() -> None:
    ids = training_task_ids()
    assert "v0/rt-001" in ids
    assert all_v1()[0].task_id not in ids
    assert all_v11()[0].task_id not in ids
    assert any(task_id.startswith("v1.1/") for task_id in ids)


def test_committed_preferences_v11_rebuilds() -> None:
    path = Path("datasets/preferences-v1.1.jsonl")
    assert path.is_file()
    committed = path.read_text(encoding="utf-8")
    rebuilt = dumps_preferences(build_preference_records())
    assert rebuilt == committed


def test_preferences_rebuild_is_deterministic(tmp_path: Path) -> None:
    records = build_preference_records(["v0/rt-001", "v0/pc-001"])
    text = dumps_preferences(records)
    export_preferences(tmp_path / "prefs.jsonl", ["v0/rt-001", "v0/pc-001"])
    assert (tmp_path / "prefs.jsonl").read_text(encoding="utf-8") == text
    again = build_preference_records(["v0/rt-001", "v0/pc-001"])
    assert dumps_preferences(again) == text
