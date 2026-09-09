"""Subprocess isolation: core import must not load provider SDKs. T7.13."""

from __future__ import annotations

import subprocess
import sys


def test_core_import_does_not_load_provider_sdks() -> None:
    script = """
import importlib
import sys
import agentic_payments_env  # noqa: F401
for name in sorted(sys.modules):
    if name.startswith(("openai", "anthropic")):
        raise SystemExit(f"provider module loaded: {name}")
print("ok")
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
