"""Load versioned system prompts and their SHA-256 hashes.

Prompt files live in the repository ``prompts/`` directory (M1 T1.04).
"""

from __future__ import annotations

import re
from pathlib import Path

from agentic_payments_env.core.hashing import sha256_hex

_PROMPT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def load_prompt(prompt_id: str) -> tuple[str, str]:
    """Return ``(prompt_text, sha256_hex)`` for ``prompts/<id>.md``. REQ-ENV-01."""

    if not _PROMPT_ID.fullmatch(prompt_id):
        raise ValueError(f"invalid prompt_id: {prompt_id!r}")
    path = _prompts_dir() / f"{prompt_id}.md"
    text = path.read_text(encoding="utf-8")
    return text, sha256_hex(text)


def _prompts_dir() -> Path:
    # src/agentic_payments_env/prompts.py -> repository root /prompts
    return Path(__file__).resolve().parents[2] / "prompts"
