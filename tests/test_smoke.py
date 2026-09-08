"""Smoke test that the package imports and reports its version."""

from agentic_payments_env import __version__


def test_package_version() -> None:
    assert __version__ == "0.1.0"
