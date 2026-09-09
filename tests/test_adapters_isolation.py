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
