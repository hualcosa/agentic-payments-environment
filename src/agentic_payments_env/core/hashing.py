"""Canonical JSON and SHA-256 helpers for deterministic hashing.

Satisfies: REQ-CON-04.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(obj: Any) -> str:
    """Serialize *obj* to compact, sorted JSON for stable hashing. REQ-ENV-08, REQ-CON-04."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(text: str) -> str:
    """Return the SHA-256 hex digest of *text* encoded as UTF-8. REQ-ENV-08, REQ-CON-04."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
