"""Export oracle action traces for external SFT. M5 T5.02."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from agentic_payments_env.agents.presets import build
from agentic_payments_env.benchmark.loader import load_task
from agentic_payments_env.benchmark.runner import _drive


def export_sft(task_ids: Sequence[str], out_path: Path) -> None:
    """Write one JSONL record per task: oracle actions at seed 0. T5.02."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for task_id in task_ids:
        task = load_task(task_id)
        _env, trace = _drive(task, build("oracle", task), 0)
        payload = {
            "task_id": task_id,
            "agent": "oracle",
            "actions": [
                {"tool_name": step.action.tool_name, "arguments": step.action.arguments}
                for step in trace.steps
            ],
        }
        lines.append(json.dumps(payload, sort_keys=True, ensure_ascii=False))
    out_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
