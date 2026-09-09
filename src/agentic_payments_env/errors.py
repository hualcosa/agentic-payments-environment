"""Environment exception types. REQ-ENV-10, REQ-CON-09."""

from __future__ import annotations


class InvariantViolation(Exception):
    """Raised when a world invariant fails. REQ-DOM-08."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class TaskValidationError(Exception):
    """Raised when a TaskSpec or reset validation fails. REQ-TOOL-16, REQ-TOOL-18."""

    pass


class OraclePlanError(Exception):
    """Raised when the oracle plan cannot be resolved or is exhausted. REQ-ENV-12."""

    pass
