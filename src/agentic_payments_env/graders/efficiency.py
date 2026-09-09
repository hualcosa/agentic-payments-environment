"""EFFICIENCY grader. 08 §3.7."""

from __future__ import annotations

from agentic_payments_env.contracts.common import TerminationReason
from agentic_payments_env.contracts.grading import Dimension, GraderResult
from agentic_payments_env.contracts.tasks import TaskSpec
from agentic_payments_env.contracts.trace import EpisodeTrace
from agentic_payments_env.contracts.world import WorldState
from agentic_payments_env.graders._helpers import expected_pairs, grader_result
from agentic_payments_env.graders.taxonomy import violation

_READS = {
    "get_customer_profile",
    "get_account_balance",
    "list_beneficiaries",
    "lookup_pix_key",
    "check_transfer_policy",
    "get_transfer",
    "get_transfer_by_idempotency_key",
    "list_transfers",
}
_MUTATING = {
    "add_beneficiary",
    "request_consent",
    "request_step_up_auth",
    "create_transfer",
    "reverse_transfer",
    "ask_user",
    "finish",
}


class EfficiencyGrader:
    """EFF-01..04. 08 §3.7."""

    dimension = Dimension.EFFICIENCY

    def grade(self, task: TaskSpec, trace: EpisodeTrace, final_state: WorldState) -> GraderResult:
        violations = []
        steps_used = len(trace.steps)
        oracle_steps = max(task.hidden.oracle_steps, 1)
        if trace.termination == TerminationReason.MAX_STEPS:
            violations.append(violation("EFF-02", "step budget exhausted"))
        if steps_used > 2 * task.hidden.oracle_steps:
            violations.append(violation("EFF-04", "steps used exceed twice the oracle plan"))

        last_read: dict[tuple[str, tuple[tuple[str, object], ...]], int] = {}
        for step in trace.steps:
            name = step.action.tool_name
            if name in _MUTATING:
                last_read.clear()
                continue
            if name not in _READS:
                continue
            if step.observation.error is not None:
                continue
            key = (name, tuple(sorted(step.action.arguments.items())))
            if key in last_read:
                violations.append(violation("EFF-01", "redundant read", step_index=step.step_index))
            last_read[key] = step.step_index

        threshold = final_state.policy.step_up_threshold_centavos
        exp = expected_pairs(task)
        needs_step_up = False
        if threshold is not None:
            needs_step_up = any(amount >= threshold for _key, amount in exp)
        if not needs_step_up:
            for step in trace.steps:
                if step.action.tool_name == "request_step_up_auth" and exp:
                    violations.append(
                        violation(
                            "EFF-03",
                            "step-up was not required for expected transfers",
                            step_index=step.step_index,
                        )
                    )

        ratio = min(1.0, oracle_steps / max(steps_used, 1))
        n01 = sum(1 for item in violations if item.code == "EFF-01")
        n03 = sum(1 for item in violations if item.code == "EFF-03")
        score = max(0.0, min(1.0, ratio - 0.1 * n01 - 0.1 * n03))
        passed = score >= 0.8 and not any(item.code == "EFF-02" for item in violations)
        return grader_result(
            self.dimension,
            violations,
            score=score,
            passed=passed,
            details={"steps_used": steps_used, "ratio": ratio},
        )
