"""Episode environment: reset, step, trace. REQ-ENV-01-11, REQ-TOOL-16, REQ-TOOL-18."""

from __future__ import annotations

from collections.abc import Sequence

from agentic_payments_env.contracts.actions import Action, Observation, ToolError, ToolErrorCode
from agentic_payments_env.contracts.common import (
    ActorKind,
    EpisodeOutcome,
    FaultKind,
    TerminationReason,
)
from agentic_payments_env.contracts.tasks import TaskSpec
from agentic_payments_env.contracts.trace import EpisodeTrace, StateTransition, Step
from agentic_payments_env.errors import TaskValidationError
from agentic_payments_env.faults import FaultScheduler
from agentic_payments_env.simulated_user import SimulatedUser
from agentic_payments_env.tools.dispatch import ToolContext, dispatch
from agentic_payments_env.tools.specs import TOOL_SPECS
from agentic_payments_env.world import WorldState

ALLOWED_FAULTS: dict[str, frozenset[FaultKind]] = {
    "get_customer_profile": frozenset({FaultKind.SERVICE_UNAVAILABLE}),
    "get_account_balance": frozenset({FaultKind.SERVICE_UNAVAILABLE, FaultKind.STALE_READ}),
    "list_beneficiaries": frozenset({FaultKind.SERVICE_UNAVAILABLE}),
    "lookup_pix_key": frozenset({FaultKind.SERVICE_UNAVAILABLE, FaultKind.TIMEOUT_BEFORE_EXECUTE}),
    "check_transfer_policy": frozenset({FaultKind.SERVICE_UNAVAILABLE}),
    "add_beneficiary": frozenset({FaultKind.SERVICE_UNAVAILABLE}),
    "request_consent": frozenset({FaultKind.SERVICE_UNAVAILABLE}),
    "request_step_up_auth": frozenset({FaultKind.SERVICE_UNAVAILABLE}),
    "create_transfer": frozenset(
        {
            FaultKind.TIMEOUT_BEFORE_EXECUTE,
            FaultKind.TIMEOUT_AFTER_EXECUTE,
            FaultKind.SERVICE_UNAVAILABLE,
        }
    ),
    "get_transfer": frozenset({FaultKind.SERVICE_UNAVAILABLE, FaultKind.STALE_READ}),
    "get_transfer_by_idempotency_key": frozenset({FaultKind.SERVICE_UNAVAILABLE}),
    "list_transfers": frozenset({FaultKind.SERVICE_UNAVAILABLE, FaultKind.STALE_READ}),
    "reverse_transfer": frozenset(
        {
            FaultKind.TIMEOUT_BEFORE_EXECUTE,
            FaultKind.TIMEOUT_AFTER_EXECUTE,
            FaultKind.SERVICE_UNAVAILABLE,
        }
    ),
    "ask_user": frozenset(),
    "finish": frozenset(),
}


def _validate_faults(task: TaskSpec) -> None:
    """Reject ambiguous or disallowed faults. REQ-TOOL-16, REQ-TOOL-18."""
    for fault in task.faults:
        allowed = ALLOWED_FAULTS.get(fault.trigger.tool_name)
        if allowed is None or fault.kind not in allowed:
            raise TaskValidationError(
                f"fault {fault.kind.value} is not allowed on {fault.trigger.tool_name}"
            )
    FaultScheduler(task.faults)


class PaymentsEnvironment:
    """Deterministic episode loop over a TaskSpec. REQ-ENV-01."""

    def __init__(self, task: TaskSpec, seed: int = 0, *, strict: bool = True) -> None:
        self._task = task
        self._seed = seed
        self._strict = strict
        self._state: WorldState | None = None
        self._sim_user: SimulatedUser | None = None
        self._faults: FaultScheduler | None = None
        self._step_index = 0
        self._done = False
        self._steps: list[Step] = []
        self._reset_observation: Observation | None = None
        self._termination: TerminationReason | None = None
        self._declared_outcome: EpisodeOutcome | None = None
        self._final_report: str | None = None

    def reset(self) -> Observation:
        """Rebuild world, faults, and user from the fixture. REQ-ENV-01, REQ-ENV-05."""
        _validate_faults(self._task)
        self._state = WorldState.from_fixture(self._task.world)
        self._faults = FaultScheduler(self._task.faults)
        self._sim_user = SimulatedUser(self._task.user, self._task.hidden)
        self._step_index = 0
        self._done = False
        self._steps = []
        self._termination = None
        self._declared_outcome = None
        self._final_report = None
        self._state.emit(
            step_index=0,
            actor=ActorKind.SYSTEM,
            kind="EPISODE_RESET",
            payload={"task_id": self._task.task_id, "seed": self._seed},
        )
        customer = self._state.principal()
        account_ids = sorted(
            account.account_id
            for account in self._state.accounts.values()
            if account.customer_id == customer.customer_id
        )
        observation = Observation(
            step_index=0,
            sim_time=self._state.now,
            kind="reset",
            observed_at=self._state.now,
            instruction=self._task.public.instruction,
            principal={
                "customer_id": customer.customer_id,
                "display_name": customer.display_name,
                "account_ids": account_ids,
            },
            available_tools=sorted(TOOL_SPECS),
        )
        self._reset_observation = observation
        return observation

    def step(self, action: Action) -> tuple[Observation, bool]:
        """Apply one action. REQ-ENV-02, REQ-ENV-03, REQ-ENV-08, REQ-ENV-09, REQ-ENV-10."""
        if self._state is None or self._sim_user is None or self._faults is None:
            raise RuntimeError("reset() must be called before step()")
        if self._done:
            observation = Observation(
                step_index=self._step_index,
                sim_time=self._state.now,
                kind="tool_error",
                tool_name=action.tool_name,
                error=ToolError(
                    code=ToolErrorCode.EPISODE_FINISHED, message="episode already finished"
                ),
                observed_at=self._state.now,
            )
            return observation, True
        self._step_index += 1
        self._state.tick()
        self._state.emit(
            step_index=self._step_index,
            actor=ActorKind.SYSTEM,
            kind="CLOCK_TICK",
            payload={"now": self._state.now.isoformat()},
        )
        hash_before = self._state.hash()
        seq_start = len(self._state.audit) + 1
        ids_before = set(self._state.transfers)
        self._state.emit(
            step_index=self._step_index,
            actor=ActorKind.AGENT,
            kind="TOOL_CALLED",
            payload={
                "tool_name": action.tool_name,
                "arguments": action.arguments,
                "rationale": action.rationale,
            },
        )
        fault = self._faults.check(action.tool_name)
        ctx = ToolContext(
            state=self._state,
            sim_user=self._sim_user,
            step_index=self._step_index,
            task_id=self._task.task_id,
            done=False,
        )
        try:
            observation = dispatch(ctx, action, fault)
        except Exception:
            if self._strict:
                raise
            observation = Observation(
                step_index=self._step_index,
                sim_time=self._state.now,
                kind="tool_error",
                tool_name=action.tool_name,
                error=ToolError(code=ToolErrorCode.SERVICE_UNAVAILABLE, message="internal error"),
                observed_at=self._state.now,
            )
        if action.tool_name == "finish" and observation.kind == "final":
            self._done = True
            self._termination = TerminationReason.FINISHED
            if observation.result is not None:
                outcome = observation.result.get("outcome")
                if isinstance(outcome, str):
                    self._declared_outcome = EpisodeOutcome(outcome)
                report = observation.result.get("report")
                if isinstance(report, str):
                    self._final_report = report
        elif self._step_index >= self._task.public.max_steps:
            self._done = True
            self._termination = TerminationReason.MAX_STEPS
            self._state.emit(
                step_index=self._step_index,
                actor=ActorKind.SYSTEM,
                kind="EPISODE_TRUNCATED",
                payload={"max_steps": self._task.public.max_steps},
            )
        if self._strict:
            self._state.check_invariants()
        last = len(self._state.audit)
        seq_range = (seq_start, last) if last >= seq_start else (0, 0)
        new_ids = sorted(set(self._state.transfers) - ids_before)
        transition = StateTransition(
            step_index=self._step_index,
            state_hash_before=hash_before,
            state_hash_after=self._state.hash(),
            audit_seq_range=seq_range,
            balances_after={
                account_id: account.balance_centavos
                for account_id, account in self._state.accounts.items()
            },
            new_transfer_ids=new_ids,
        )
        self._steps.append(
            Step(
                step_index=self._step_index,
                action=action,
                observation=observation,
                transition=transition,
            )
        )
        return observation, self._done

    @property
    def done(self) -> bool:
        return self._done

    @property
    def state(self) -> WorldState:
        if self._state is None:
            raise RuntimeError("reset() must be called first")
        return self._state

    @property
    def steps(self) -> Sequence[Step]:
        return tuple(self._steps)

    def trace(
        self,
        agent_name: str = "unknown",
        *,
        termination: TerminationReason | None = None,
        error: str | None = None,
    ) -> EpisodeTrace:
        """Build an episode trace, including partial traces. REQ-ENV-15."""
        if self._state is None or self._reset_observation is None:
            raise RuntimeError("reset() must be called first")
        del error
        term = self._termination if termination is None else termination
        if term is None:
            term = TerminationReason.AGENT_ERROR
        return EpisodeTrace(
            task_id=self._task.task_id,
            seed=self._seed,
            agent_name=agent_name,
            reset_observation=self._reset_observation,
            steps=list(self._steps),
            termination=term,
            declared_outcome=self._declared_outcome,
            final_report=self._final_report,
            final_state_hash=self._state.hash(),
            audit=list(self._state.audit),
        )

    def state_hash(self) -> str:
        """Canonical world hash. REQ-ENV-07."""
        return self.state.hash()
