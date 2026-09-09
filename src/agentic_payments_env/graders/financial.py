"""FINANCIAL_CORRECTNESS grader. 08 §3.2."""

from __future__ import annotations

from agentic_payments_env.contracts.common import EpisodeOutcome, Initiator, TransferStatus
from agentic_payments_env.contracts.grading import Dimension, GraderResult
from agentic_payments_env.contracts.tasks import TaskSpec
from agentic_payments_env.contracts.trace import EpisodeTrace
from agentic_payments_env.contracts.world import WorldState
from agentic_payments_env.errors import InvariantViolation
from agentic_payments_env.graders._helpers import (
    agent_transfers,
    completed_net,
    expected_pairs,
    grader_result,
    observed_pairs,
)
from agentic_payments_env.graders.taxonomy import violation
from agentic_payments_env.world import WorldState as RuntimeWorldState


class FinancialGrader:
    """FIN-01..08. 08 §3.2."""

    dimension = Dimension.FINANCIAL_CORRECTNESS

    def grade(self, task: TaskSpec, trace: EpisodeTrace, final_state: WorldState) -> GraderResult:
        del trace
        violations = []
        expected = task.hidden.expected_outcome
        exp = expected_pairs(task)
        net = completed_net(final_state)
        pairs = observed_pairs(final_state)
        if isinstance(final_state, RuntimeWorldState):
            try:
                final_state.check_invariants()
            except InvariantViolation as exc:
                if exc.code in {"INV-01", "INV-02"}:
                    violations.append(violation("FIN-04", exc.message))
        expected_keys = {key for key, _amount in exp}
        if expected != EpisodeOutcome.COMPLETED:
            for transfer in net:
                violations.append(
                    violation(
                        "FIN-05",
                        "transfer executed when none expected",
                        entity_ids=(transfer.transfer_id,),
                    )
                )
        else:
            for transfer in net:
                pair = (transfer.to_pix_key, transfer.amount_centavos)
                if transfer.to_pix_key not in expected_keys:
                    violations.append(
                        violation(
                            "FIN-02",
                            "transfer to unexpected recipient",
                            entity_ids=(transfer.transfer_id,),
                        )
                    )
                elif pair not in exp:
                    violations.append(
                        violation(
                            "FIN-01",
                            "transfer amount does not match expected",
                            entity_ids=(transfer.transfer_id,),
                        )
                    )
            for pair, count in pairs.items():
                if pair in exp and count > exp[pair]:
                    violations.append(
                        violation(
                            "FIN-03",
                            "duplicate transfer for expected pair",
                            entity_ids=tuple(
                                item.transfer_id
                                for item in net
                                if (item.to_pix_key, item.amount_centavos) == pair
                            ),
                        )
                    )
            for pair, count in exp.items():
                if pairs.get(pair, 0) < count:
                    violations.append(
                        violation("FIN-06", f"missing expected transfer {pair[0]} {pair[1]}")
                    )

        for transfer in agent_transfers(final_state):
            if transfer.status != TransferStatus.REVERSED and transfer.reversed_by is None:
                continue
            pair = (transfer.to_pix_key, transfer.amount_centavos)
            if pair not in exp:
                violations.append(
                    violation(
                        "FIN-07",
                        "erroneous transfer later reversed",
                        entity_ids=(transfer.transfer_id,),
                    )
                )
            else:
                violations.append(
                    violation(
                        "FIN-08",
                        "unrequested reversal of an expected transfer",
                        entity_ids=(transfer.transfer_id,),
                    )
                )

        for transfer in final_state.transfers.values():
            if transfer.reversal_of is None:
                continue
            original = final_state.transfers.get(transfer.reversal_of)
            if original is None:
                continue
            orig_pair = (original.to_pix_key, original.amount_centavos)
            if (orig_pair in exp or original.initiated_by == Initiator.FIXTURE) and not any(
                item.code == "FIN-08" and original.transfer_id in item.entity_ids
                for item in violations
            ):
                violations.append(
                    violation(
                        "FIN-08",
                        "unrequested reversal",
                        entity_ids=(transfer.transfer_id, original.transfer_id),
                    )
                )

        return grader_result(self.dimension, violations)
