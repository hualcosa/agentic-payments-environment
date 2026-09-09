"""Package import smoke test. T0.01."""

from agentic_payments_env import __version__


def test_version() -> None:
    assert __version__ == "0.1.0"
