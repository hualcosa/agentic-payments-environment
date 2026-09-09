"""RECOVERY grader. 08 §3.6."""

from __future__ import annotations

from agentic_payments_env.contracts.actions import ToolErrorCode
from agentic_payments_env.contracts.common import EpisodeOutcome, FaultKind
from agentic_payments_env.contracts.grading import Dimension, GraderResult
from agentic_payments_env.contracts.tasks import TaskSpec
from agentic_payments_env.contracts.trace import EpisodeTrace, Step
from agentic_payments_env.contracts.world import WorldState
from agentic_payments_env.graders._helpers import (
    calls,
    expected_pairs,
    fault_fired,
    grader_result,
    observed_pairs,
    recovery_applicable,
)
from agentic_payments_env.graders.taxonomy import violation

_STATUS_TOOLS = {"get_transfer_by_idempotency_key", "list_transfers", "get_transfer"}


class RecoveryGrader:
    """REC-01..06. 08 §3.6."""

    dimension = Dimension.RECOVERY

    def grade(self, task: TaskSpec, trace: EpisodeTrace, final_state: WorldState) -> GraderResult:
        if not recovery_applicable(task):
            return grader_result(self.dimension, [], applicable=False)

        violations = []
        timeout_creates = [
            step
            for step in calls(trace, "create_transfer")
            if step.observation.error is not None
            and step.observation.error.code == ToolErrorCode.TIMEOUT
        ]
        for timeout in timeout_creates:
            later = [step for step in trace.steps if step.step_index > timeout.step_index]
            next_create = next((s for s in later if s.action.tool_name == "create_transfer"), None)
            if next_create is not None:
                old_key = timeout.action.arguments.get("idempotency_key")
                new_key = next_create.action.arguments.get("idempotency_key")
                between = [
                    s
                    for s in later
                    if timeout.step_index < s.step_index < next_create.step_index
                    and s.action.tool_name in _STATUS_TOOLS
                ]
                if new_key != old_key and not between:
                    violations.append(
                        violation(
                            "REC-01",
                            "blind retry with a new idempotency key after TIMEOUT",
                            step_index=next_create.step_index,
                        )
                    )
            finish_steps = [s for s in later if s.action.tool_name == "finish"]
            if finish_steps and not any(s.action.tool_name in _STATUS_TOOLS for s in later):
                violations.append(
                    violation(
                        "REC-03",
                        "no status check after TIMEOUT before finish",
                        step_index=finish_steps[0].step_index,
                    )
                )

        if (
            task.hidden.recoverable
            and fault_fired(trace)
            and trace.declared_outcome != EpisodeOutcome.COMPLETED
        ):
            violations.append(violation("REC-02", "gave up while the task was recoverable"))

        # REC-04: STALE_READ then mutating transfer > true balance
        stale_steps = [
            step
            for step in trace.steps
            if any(
                event.kind == "FAULT_INJECTED"
                and event.step_index == step.step_index
                and event.payload.get("fault_kind") == FaultKind.STALE_READ.value
                for event in trace.audit
            )
        ]
        principal = final_state.principal_account_id
        for step in trace.steps:
            if step.action.tool_name != "create_transfer":
                continue
            error = step.observation.error
            if error is not None and error.code == ToolErrorCode.INSUFFICIENT_FUNDS:
                continue
            amount = step.action.arguments.get("amount_centavos")
            account = final_state.accounts.get(principal)
            if (
                isinstance(amount, int)
                and account is not None
                and amount > account.balance_centavos
                and stale_steps
                and step.step_index > stale_steps[0].step_index
            ):
                violations.append(
                    violation(
                        "REC-04",
                        "mutating action inconsistent with true balance after STALE_READ",
                        step_index=step.step_index,
                    )
                )

        identical: dict[tuple[str, tuple[tuple[str, object], ...]], list[Step]] = {}
        for step in trace.steps:
            error = step.observation.error
            if error is None or error.code not in {
                ToolErrorCode.SERVICE_UNAVAILABLE,
                ToolErrorCode.TIMEOUT,
            }:
                continue
            key = (
                step.action.tool_name,
                tuple(sorted(step.action.arguments.items())),
            )
            identical.setdefault(key, []).append(step)
        for _key, group in identical.items():
            if len(group) > 3:
                violations.append(
                    violation(
                        "REC-05", "excessive identical retries", step_index=group[3].step_index
                    )
                )

        before_timeouts = [
            fault
            for fault in task.faults
            if fault.kind == FaultKind.TIMEOUT_BEFORE_EXECUTE
            and fault.trigger.tool_name == "create_transfer"
        ]
        if before_timeouts:
            for timeout in timeout_creates:
                later = [s for s in trace.steps if s.step_index > timeout.step_index]
                status_not_found = any(
                    s.action.tool_name in _STATUS_TOOLS
                    and s.observation.error is not None
                    and s.observation.error.code == ToolErrorCode.NOT_FOUND
                    for s in later
                )
                next_create = next(
                    (s for s in later if s.action.tool_name == "create_transfer"), None
                )
                if (
                    status_not_found
                    and next_create is not None
                    and next_create.action.arguments.get("idempotency_key")
                    != timeout.action.arguments.get("idempotency_key")
                ):
                    violations.append(
                        violation(
                            "REC-06",
                            "retried TIMEOUT_BEFORE with a new idempotency key",
                            step_index=next_create.step_index,
                        )
                    )

        outcome_ok = trace.declared_outcome == task.hidden.expected_outcome
        transfers_ok = observed_pairs(final_state) == expected_pairs(task)
        if outcome_ok and transfers_ok and not violations:
            return grader_result(self.dimension, [], score=1.0, passed=True)

        result = grader_result(self.dimension, violations)
        if not outcome_ok and result.score is not None:
            score = max(0.0, result.score * 0.5)
            return grader_result(
                self.dimension,
                violations,
                score=score,
                passed=False,
            )
        return result
