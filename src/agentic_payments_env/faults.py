"""Per-tool fault injection scheduler. REQ-ENV-05."""

from __future__ import annotations

from collections.abc import Sequence

from agentic_payments_env.contracts.tasks import FaultInjection
from agentic_payments_env.errors import TaskValidationError


class FaultScheduler:
    """Fires each configured fault once on the matching tool call ordinal. REQ-ENV-05."""

    def __init__(self, faults: Sequence[FaultInjection]) -> None:
        seen: set[tuple[str, int]] = set()
        for fault in faults:
            key = (fault.trigger.tool_name, fault.trigger.call_ordinal)
            if key in seen:
                raise TaskValidationError(f"two faults on the same call: {key[0]} ordinal {key[1]}")
            seen.add(key)
        self._faults = list(faults)
        self._call_counts: dict[str, int] = {}
        self._fired: list[FaultInjection] = []
        self._consumed: set[int] = set()

    def check(self, tool_name: str) -> FaultInjection | None:
        """Increment per-tool call counter; return matching unfired fault. REQ-ENV-05."""
        count = self._call_counts.get(tool_name, 0) + 1
        self._call_counts[tool_name] = count
        for index, fault in enumerate(self._faults):
            if index in self._consumed:
                continue
            if fault.trigger.tool_name == tool_name and fault.trigger.call_ordinal == count:
                self._consumed.add(index)
                self._fired.append(fault)
                return fault
        return None

    @property
    def fired(self) -> list[FaultInjection]:
        """Faults that have fired this episode. REQ-ENV-05."""
        return list(self._fired)
