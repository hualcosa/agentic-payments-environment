"""Export action traces for external SFT. M5 T5.02. REQ-GRD-12."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from agentic_payments_env.agents.presets import NAMES, build
from agentic_payments_env.benchmark.loader import load_task
from agentic_payments_env.benchmark.runner import _drive
from agentic_payments_env.contracts.training import SFTRecord
from agentic_payments_env.graders import grade_episode
from agentic_payments_env.rewards.pairs import assert_training_task_id, training_task_ids


def _record(task_id: str, agent_name: str, seed: int) -> SFTRecord:
    assert_training_task_id(task_id)
    task = load_task(task_id)
    env, trace = _drive(task, build(agent_name, task), seed)
    result = grade_episode(task, trace, env.state)
    return SFTRecord(
        task_id=task_id,
        seed=seed,
        agent=agent_name,
        safe_success=result.safe_success,
        actions=[
            {"tool_name": step.action.tool_name, "arguments": step.action.arguments}
            for step in trace.steps
        ],
    )


def build_sft_records(
    task_ids: Sequence[str] | None = None,
    *,
    agents: Sequence[str] = ("oracle",),
    seed: int = 0,
    include_non_oracle_only_when_safe: bool = True,
) -> list[SFTRecord]:
    """Collect SFT rows; non-oracle agents require ``safe_success``. T5.02. REQ-GRD-12."""
    tasks = list(training_task_ids() if task_ids is None else task_ids)
    for task_id in tasks:
        assert_training_task_id(task_id)
    records: list[SFTRecord] = []
    for task_id in tasks:
        for agent_name in agents:
            if agent_name not in NAMES and agent_name != "oracle":
                continue
            record = _record(task_id, agent_name, seed)
            if (
                agent_name != "oracle"
                and include_non_oracle_only_when_safe
                and not record.safe_success
            ):
                continue
            records.append(record)
    return records


def dumps_sft(records: list[SFTRecord]) -> str:
    """Canonical JSONL text for SFT records. REQ-GRD-12."""
    lines = [
        json.dumps(record.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
        for record in records
    ]
    return "\n".join(lines) + ("\n" if lines else "")


def export_sft(task_ids: Sequence[str], out_path: Path, *, seed: int = 0) -> None:
    """Write oracle-only JSONL for the given training task ids. T5.02. REQ-GRD-12."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    records = build_sft_records(task_ids, agents=("oracle",), seed=seed)
    out_path.write_text(dumps_sft(records), encoding="utf-8")


def export_sft_benchmark(
    out_path: Path,
    *,
    agents: Sequence[str] = ("oracle", "quitter"),
    seed: int = 0,
) -> None:
    """Write SFT JSONL for all training tasks and selected agents. T5.02. REQ-GRD-12."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    records = build_sft_records(None, agents=agents, seed=seed)
    out_path.write_text(dumps_sft(records), encoding="utf-8")
