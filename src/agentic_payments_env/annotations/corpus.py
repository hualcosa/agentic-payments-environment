"""Build the committed scripted-agent annotation corpus. M2 T2.03. REQ-GRD-11."""

from __future__ import annotations

from pathlib import Path

from agentic_payments_env.agents.presets import build
from agentic_payments_env.annotations.from_grade import from_episode
from agentic_payments_env.annotations.schema import EpisodeAnnotation, dumps_jsonl, write_jsonl
from agentic_payments_env.benchmark.runner import _drive
from agentic_payments_env.benchmark.v0 import all_tasks
from agentic_payments_env.graders import grade_episode

PRESETS: tuple[str, ...] = ("oracle", "quitter", "liar", "naive_retry")


def corpus_path() -> Path:
    """Repository ``annotations/v0-scripted.jsonl``. REQ-GRD-11."""
    return Path(__file__).resolve().parents[3] / "annotations" / "v0-scripted.jsonl"


def build_scripted_corpus() -> list[EpisodeAnnotation]:
    """Grade four presets on every v0 task at seed 0. T2.03. REQ-GRD-11."""
    records: list[EpisodeAnnotation] = []
    for task in all_tasks():
        for name in PRESETS:
            env, trace = _drive(task, build(name, task), 0)
            result = grade_episode(task, trace, env.state)
            records.append(from_episode(task, trace, result))
    return records


def write_scripted_corpus(path: Path | None = None) -> Path:
    """Write the corpus JSONL and return the path. REQ-GRD-11."""
    target = path if path is not None else corpus_path()
    write_jsonl(target, build_scripted_corpus())
    return target


def dumps_scripted_corpus() -> str:
    """Canonical JSONL text of a freshly built corpus. REQ-GRD-11."""
    return dumps_jsonl(build_scripted_corpus())
