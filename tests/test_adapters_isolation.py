"""Core import must not load provider SDKs. M1 exit."""

from __future__ import annotations

import subprocess
import sys


def test_import_package_does_not_import_openai_or_anthropic() -> None:
    script = (
        "import sys; "
        "import agentic_payments_env; "
        "assert 'openai' not in sys.modules; "
        "assert 'anthropic' not in sys.modules; "
        "assert agentic_payments_env.__version__"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_core_import_does_not_load_provider_sdks() -> None:
    script = """

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
