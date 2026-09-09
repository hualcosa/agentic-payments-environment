"""Oracle agent passes every v0 task. REQ-TASK-04, REQ-TASK-06."""

from __future__ import annotations

from collections import Counter

import pytest

from agentic_payments_env.agents.oracle import OracleAgent
from agentic_payments_env.benchmark.runner import run_episode
from agentic_payments_env.benchmark.v0 import TASKS, load_task
from agentic_payments_env.contracts.common import Initiator, TerminationReason, TransferStatus
from agentic_payments_env.graders import grade_episode
from agentic_payments_env.world import WorldState
from tests.conftest import run_oracle


def completed_net(state: WorldState) -> Counter[tuple[str, int]]:
    """Non-fixture COMPLETED transfers that are not reversed. Moves to graders in T0.14."""
    reversed_ids = {
        transfer.transfer_id for transfer in state.transfers.values() if transfer.reversed_by
    }
    reversed_ids.update(
        transfer.reversal_of
        for transfer in state.transfers.values()
        if transfer.reversal_of is not None
    )
    net: Counter[tuple[str, int]] = Counter()
    for transfer in state.transfers.values():
        if transfer.initiated_by == Initiator.FIXTURE:
            continue
        if transfer.status != TransferStatus.COMPLETED:
            continue
        if transfer.reversal_of is not None:
            continue
        if transfer.transfer_id in reversed_ids:
            continue
        net[(transfer.to_pix_key, transfer.amount_centavos)] += 1
    return net


@pytest.mark.parametrize("task_id", sorted(TASKS))
def test_oracle_passes_every_task(task_id: str) -> None:
    task = load_task(task_id)
    trace, state = run_oracle(task)
    assert trace.termination == TerminationReason.FINISHED
    assert trace.declared_outcome == task.hidden.expected_outcome
    assert len(trace.steps) == task.hidden.oracle_steps
    expected = Counter(
        (item.pix_key, item.amount_centavos) for item in task.hidden.expected_transfers
    )
    assert completed_net(state) == expected
    graded = grade_episode(task, trace, state)
    assert graded.safe_success, graded.catastrophic_codes or graded.violations


@pytest.mark.parametrize("task_id", sorted(TASKS))
def test_oracle_determinism_every_task(task_id: str) -> None:
    task = load_task(task_id)
    agent_a = OracleAgent(task.hidden, task.task_id)
    agent_b = OracleAgent(task.hidden, task.task_id)
    trace_a = run_episode(task, agent_a, 0)
    trace_b = run_episode(task, agent_b, 0)
    assert trace_a == trace_b
    assert trace_a.final_state_hash == trace_b.final_state_hash
