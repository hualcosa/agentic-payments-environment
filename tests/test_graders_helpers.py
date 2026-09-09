"""Taxonomy and grader helper tests. REQ-TAX-03, 08 §2."""

from __future__ import annotations

from agentic_payments_env.contracts.grading import Dimension, Severity
from agentic_payments_env.graders._helpers import (
    agent_transfers,
    completed_net,
    expected_pairs,
    recovery_applicable,
)
from agentic_payments_env.graders.taxonomy import CATASTROPHIC_CODES, TAXONOMY, violation
from tests.conftest import default_task

SPEC_CATASTROPHIC = frozenset(
    {
        "FIN-01",
        "FIN-02",
        "FIN-03",
        "FIN-04",
        "FIN-05",
        "AUTH-01",
        "AUTH-02",
        "AUTH-03",
        "AUTH-04",
        "POL-01",
        "POL-02",
        "POL-03",
        "SAF-01",
        "SAF-02",
        "SAF-04",
        "SAF-05",
        "AUD-02",
    }
)


def test_taxonomy_covers_09() -> None:
    assert CATASTROPHIC_CODES == SPEC_CATASTROPHIC
    for code in SPEC_CATASTROPHIC:
        assert TAXONOMY[code].severity == Severity.CATASTROPHIC
    prefixes = {
        "FIN": Dimension.FINANCIAL_CORRECTNESS,
        "AUTH": Dimension.AUTHORIZATION,
        "POL": Dimension.POLICY_COMPLIANCE,
        "SAF": Dimension.SAFETY,
        "REC": Dimension.RECOVERY,
        "EFF": Dimension.EFFICIENCY,
        "AUD": Dimension.AUDITABILITY,
        "TASK": Dimension.TASK_SUCCESS,
    }
    for code, entry in TAXONOMY.items():
        assert entry.dimension == prefixes[code.split("-", 1)[0]]
        assert entry.code == code


def test_violation_fills_severity_from_table() -> None:
    item = violation("FIN-03", "dup", step_index=2, entity_ids=("tx_000001",))
    assert item.severity == Severity.CATASTROPHIC
    assert item.dimension == Dimension.FINANCIAL_CORRECTNESS
    assert item.step_index == 2
    assert item.entity_ids == ["tx_000001"]


def test_helpers_on_default_task() -> None:
    task = default_task()
    assert expected_pairs(task) == {}
    assert recovery_applicable(task) is False


def test_agent_transfers_empty_world() -> None:
    from agentic_payments_env.world import WorldState

    state = WorldState.from_fixture(default_task().world)
    assert agent_transfers(state) == []
    assert completed_net(state) == []
