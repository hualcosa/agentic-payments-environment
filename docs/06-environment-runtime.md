# 06 — Environment runtime

This document owns the lifecycle of an episode: construction, `reset`,
`step`, termination, trace recording, state hashing, replay, and the runner
that connects an `Agent` to the environment.

## 1. Public API

```python
# NORMATIVE — src/agentic_payments_env/environment.py
class PaymentsEnvironment:
    def __init__(self, task: TaskSpec, seed: int = 0, *, strict: bool = True) -> None: ...
    def reset(self) -> Observation: ...
    def step(self, action: Action) -> tuple[Observation, bool]: ...   # (observation, done)
    @property
    def done(self) -> bool: ...
    @property
    def state(self) -> WorldState: ...            # hidden state; never given to agents
    @property
    def steps(self) -> Sequence[Step]: ...        # steps so far (read-only view)
    def trace(self, agent_name: str = "unknown", *,
              termination: TerminationReason | None = None,
              error: str | None = None) -> EpisodeTrace: ...
        # may be called mid-episode (partial trace); the runner passes termination=AGENT_ERROR on agent crashes
    def state_hash(self) -> str: ...
```

- **REQ-ENV-01** `reset()` MUST be callable multiple times; each call
  rebuilds `WorldState` from the fixture, resets the fault schedule, the
  simulated user cursors, the step counter and the trace. Two resets with the
  same `(task, seed)` produce identical `state_hash()`.
- **REQ-ENV-02** `step()` before `reset()` raises `RuntimeError`.
- **REQ-ENV-03** `step()` after `done` returns
  `(Observation(kind="tool_error", error=EPISODE_FINISHED), True)` without
  mutating state or advancing the clock.
- **REQ-ENV-04** `strict=True` runs `WorldState.check_invariants()` after
  every step and raises `InvariantViolation` on failure. Tests always use
  `strict=True`.

## 2. The seed

In v0 nothing is randomized, so the seed only labels the episode. It is
still threaded through `EpisodeTrace.seed` and reserved for M3, where task
generators and fault schedulers draw from `random.Random(seed)`. The
environment MUST NOT ignore the argument: it stores it and includes it in the
trace (REQ-ENV-05). No component may create an unseeded RNG (REQ-ENV-06).

## 3. `WorldState` methods (implemented in `world.py`)

```python
# NORMATIVE
class WorldState(MutableModel):
    ...
    @classmethod
    def from_fixture(cls, fixture: WorldFixture) -> "WorldState": ...
    def next_id(self, prefix: str) -> str: ...                    # "tx" -> "tx_000001"
    def tick(self) -> None: ...                                    # now += tick_seconds; append balance/transfer history
    def emit(self, *, step_index: int, actor: ActorKind, kind: str,
             entity_ids: list[str] | None = None, payload: dict[str, Any] | None = None,
             visible_to_agent: bool = True) -> AuditEvent: ...
    def principal(self) -> Customer: ...
    def owned_account(self, account_id: str) -> Account | None: ...
    def daily_used(self, account_id: str) -> Centavos: ...
    def effective_auth_level(self) -> AuthLevel: ...
    def post_transfer(self, transfer: Transfer) -> Transfer: ...  # PENDING->COMPLETED, ledger, balances, audit
    def total_centavos(self) -> Centavos: ...
    def check_invariants(self) -> None: ...                        # raises InvariantViolation
    def canonical_json(self) -> str: ...
    def hash(self) -> str: ...                                     # sha256 of canonical_json
```

`canonical_json` MUST exclude `audit` (audit events include payloads whose
ordering is already canonical, but the audit log is compared separately in
replay tests) and MUST include everything else. Two states are "equal" iff
their hashes are equal (REQ-ENV-07).

## 4. Step algorithm

```
step(action):
  1. if done: return EPISODE_FINISHED error, True
  2. step_index += 1
  3. state.tick(); audit CLOCK_TICK(step_index)
  4. hash_before = state.hash(); seq_start = len(state.audit) + 1
  5. audit TOOL_CALLED(actor=AGENT, payload={tool_name, arguments, rationale})
  6. fault = fault_scheduler.check(action.tool_name)          # increments the per-tool call counter
  7. observation = tools.dispatch(ToolContext(state, sim_user, step_index, task_id), action, fault)
        - unknown tool -> UNKNOWN_TOOL
        - args validation -> INVALID_ARGUMENT
        - tool body per 04/05
  8. audit TOOL_RESULT or TOOL_ERROR
  9. if action.tool_name == "finish" and no error: done = True, termination = FINISHED
     elif step_index >= max_steps: done = True, termination = MAX_STEPS; audit EPISODE_TRUNCATED
 10. if strict: state.check_invariants()
 11. transition = StateTransition(step_index, hash_before, state.hash(),
        (seq_start, len(state.audit)) or (0,0), balances_after, new_transfer_ids)
 12. append Step(step_index, action, observation, transition) to trace
 13. return observation, done
```

- **REQ-ENV-08** The clock ticks even when the action fails.
- **REQ-ENV-09** `Observation.step_index == step_index` and
  `Observation.sim_time == state.now` after the tick.
- **REQ-ENV-10** When `MAX_STEPS` is hit on a non-`finish` action, the
  observation for that step is still the tool's normal observation; the
  trace's `declared_outcome` and `final_report` stay `None`.
- **REQ-ENV-11** An exception raised inside a tool body is a bug. In
  `strict=False` mode the environment MAY convert it into
  `ToolError(SERVICE_UNAVAILABLE, "internal error")` and log it; in strict
  mode it propagates.

## 5. Reset algorithm

```
reset():
  state = WorldState.from_fixture(task.world)
  validate task against 03 §6 rules and 04 §4 (REQ-TOOL-16/18) -> TaskValidationError
  fault_scheduler = FaultScheduler(task.faults)
  sim_user = SimulatedUser(task.user, task.hidden)      # hidden used only for DENY_IF_SCOPE_MISMATCH
  step_index = 0; done = False; trace steps = []
  audit EPISODE_RESET (step 0)
  record balance/transfer history at step 0
  return Observation(step_index=0, kind="reset", instruction=task.public.instruction,
                     principal={customer_id, display_name, account_ids},
                     available_tools=sorted(TOOL_SPECS), sim_time=state.now, observed_at=state.now)
```

- **REQ-ENV-12** The simulated user object is constructed with
  `task.hidden` because vigilance mode needs the expected transfers. The
  environment MUST NOT pass `task.hidden` to anything else, and no
  `Observation` field may be derived from it. Test `test_hidden_never_leaks`
  serializes every observation of every v0 task's oracle run and asserts that
  no value from `hidden` (transfer amounts+keys aside, which legitimately
  appear as the agent acts) appears: specifically `notes`, `oracle_plan`,
  `expected_outcome`, `injection_targets`, `forbidden_pix_keys`.

## 6. Fault scheduler

```python
# NORMATIVE — src/agentic_payments_env/faults.py
class FaultScheduler:
    def __init__(self, faults: Sequence[FaultInjection]) -> None: ...
    def check(self, tool_name: str) -> FaultInjection | None: ...
        # increments call_counts[tool_name]; returns the fault whose trigger matches, marks it fired
    @property
    def fired(self) -> list[FaultInjection]: ...
```

## 7. Simulated user

```python
# NORMATIVE — src/agentic_payments_env/simulated_user.py
class SimulatedUser:
    def __init__(self, script: UserScript, hidden: TaskHidden) -> None: ...
    def respond_consent(self, scope: ConsentScope) -> ConsentResponse: ...
    def respond_step_up(self) -> StepUpResponse: ...
    def respond_clarification(self, question: str) -> str: ...
```

- Each `respond_*` consumes the next scripted entry; when the list is
  exhausted, the last entry repeats (REQ-ENV-13).
- With `vigilance == DENY_IF_SCOPE_MISMATCH`, `respond_consent` returns
  `DENY` if `(scope.pix_key, scope.amount_centavos)` is not among
  `hidden.expected_transfers`, **without** consuming a scripted entry;
  otherwise it follows the script (REQ-ENV-14).
- The simulated user never initiates messages in v0.

## 8. Trace and replay

- **REQ-ENV-15** `env.trace(agent_name)` returns an `EpisodeTrace` with the
  reset observation, all steps, `termination`, `declared_outcome`,
  `final_report`, `final_state_hash` and the complete audit log.
- **REQ-ENV-16** `replay.replay(task, trace) -> ReplayResult` constructs a
  fresh environment with `trace.seed`, resets, re-applies `step.action` for
  every step, and returns
  `ReplayResult(matches: bool, first_divergence_step: int | None,
  expected_hash: str, actual_hash: str)`. Matching means every
  `StateTransition.state_hash_after` and every observation are equal, and
  the audit logs are equal field by field.
- **REQ-ENV-17** Traces are written as one JSON document per episode:
  `runs/<run_id>/<task_id with '/' replaced by '_'>/seed-<n>.trace.json`,
  alongside `seed-<n>.result.json`. `runs/` is git-ignored.

## 9. Runner

```python
# NORMATIVE — src/agentic_payments_env/benchmark/runner.py
def run_episode(task: TaskSpec, agent: Agent, seed: int = 0, *, strict: bool = True) -> EpisodeTrace:
    env = PaymentsEnvironment(task, seed, strict=strict)
    obs = env.reset()
    agent.reset(task.public, obs)
    history: list[Step] = []
    while not env.done:
        try:
            action = agent.act(history, obs)
        except Exception as exc:          # agent bugs are the agent's failure, not the env's
            return env.trace(agent.name, termination=TerminationReason.AGENT_ERROR, error=str(exc))
        obs, done = env.step(action)
        history = list(env.steps)
    return env.trace(agent.name)

def run_benchmark(tasks: Sequence[TaskSpec], agent_factory: Callable[[], Agent],
                  seeds: Sequence[int], graders: Sequence[Grader], out_dir: Path) -> BenchmarkReport: ...
```

`AGENT_ERROR` traces are graded like any other (they will fail task success)
so that an agent that crashes is counted, not skipped (REQ-ENV-18).

## 10. CLI (M0 scope)

`python -m agentic_payments_env.cli <command>`:

| command | behavior |
|---|---|
| `list-tasks [--benchmark v0]` | prints task ids, family, title |
| `show-task <task_id>` | prints the public part and the world summary; `--hidden` prints the hidden part |
| `run --task <id> --agent <name> [--seed 0] [--out runs/<id>]` | runs one episode with a scripted agent, writes trace + result, prints the result summary |
| `bench --benchmark v0 --agent <name> [--seeds 0,1,2] --out runs/<id>` | runs all tasks, writes traces/results and `report.json` + `report.md` |
| `replay <trace.json>` | replays and prints `ReplayResult` |
| `export-tasks --benchmark v0 --out benchmarks/v0` | writes the frozen task JSON files |

Scripted agent names available in M0 (see 10 §4.3): `oracle`, `naive_retry`,
`no_consent`, `no_step_up`, `after_denial`, `obedient`, `splitter`,
`wrong_amount`, `wrong_recipient`, `liar`, `quitter`, `ignores_policy`.
