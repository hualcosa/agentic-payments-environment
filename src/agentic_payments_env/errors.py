"""Package-level exceptions for invariants, task validation, and oracle plans."""

from __future__ import annotations


class InvariantViolation(Exception):
    """Raised when a world-state invariant fails. REQ-DOM-19."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class TaskValidationError(Exception):
    """Raised when a task fixture or spec cannot be used. REQ-CON-09."""


class OraclePlanError(Exception):
    """Raised when an oracle plan step cannot be resolved or executed."""
