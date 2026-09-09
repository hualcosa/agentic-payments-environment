"""Step- and episode-level annotation records. M2 T2.01; codes from 09."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path

from pydantic import field_validator

from agentic_payments_env.contracts.common import SCHEMA_VERSION, FrozenModel

_CODE = re.compile(r"^[A-Z]{3,4}-[0-9]{2}$")


def _validate_codes(codes: list[str]) -> list[str]:
    for code in codes:
        if not _CODE.fullmatch(code):
            raise ValueError(f"invalid taxonomy code {code!r}")
    return codes


class StepAnnotation(FrozenModel):
    """Labels for one episode step (1-based index, matching ``Step``)."""

    step_index: int
    codes: list[str] = []  # noqa: RUF012
    note: str = ""

    @field_validator("codes")
    @classmethod
    def _codes(cls, value: list[str]) -> list[str]:
        return _validate_codes(value)


class EpisodeAnnotation(FrozenModel):
    """Labels for one graded episode. T2.01."""

    schema_version: str = SCHEMA_VERSION
    task_id: str
    seed: int
    agent_name: str
    annotator: str
    episode_codes: list[str] = []  # noqa: RUF012
    steps: list[StepAnnotation] = []  # noqa: RUF012
    note: str = ""

    @field_validator("episode_codes")
    @classmethod
    def _episode_codes(cls, value: list[str]) -> list[str]:
        return _validate_codes(value)


def dumps_jsonl(records: Sequence[EpisodeAnnotation]) -> str:
    """Serialize annotations as one JSON object per line."""
    if not records:
        return ""
    lines = [
        json.dumps(record.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        for record in records
    ]
    return "\n".join(lines) + "\n"


def loads_jsonl(text: str) -> list[EpisodeAnnotation]:
    """Parse JSONL into ``EpisodeAnnotation`` rows; skip blank lines."""
    records: list[EpisodeAnnotation] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        records.append(EpisodeAnnotation.model_validate(json.loads(line)))
    return records


def write_jsonl(path: Path, records: Sequence[EpisodeAnnotation]) -> None:
    """Write JSONL to ``path``, creating parents."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps_jsonl(records), encoding="utf-8")


def read_jsonl(path: Path) -> list[EpisodeAnnotation]:
    """Read JSONL annotations from ``path``."""
    return loads_jsonl(path.read_text(encoding="utf-8"))
