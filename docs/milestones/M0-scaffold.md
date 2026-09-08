# Milestone 0 — Scaffold

Goal: a working package in which every contract, tool, policy, grader and
benchmark task from docs 02–10 exists at v0 fidelity, with tests that prove
the environment is deterministic and the graders are validated by scripted
adversaries. No LLM, no network.

Execute tickets **in order**. Each ticket lists the files it creates or
edits, the spec sections to read first, the tests to write, and a
"Done when" checklist. Do not start a ticket until the previous one is
green. Commit after each ticket (AGENTS.md §6).

Estimated size: ~3 500 lines of `src/`, ~2 500 lines of `tests/`.

## Package layout (target at end of M0)

```
pyproject.toml  uv.lock  README.md  AGENTS.md  LICENSE  .gitignore
.github/workflows/ci.yml
src/agentic_payments_env/
    __init__.py            __version__, re-exports of PaymentsEnvironment, TaskSpec, grade_episode
    errors.py              InvariantViolation, TaskValidationError, OraclePlanError
    core/
        __init__.py  money.py  hashing.py
    contracts/             (03)
        __init__.py  common.py  domain.py  world.py  actions.py  tasks.py  trace.py  grading.py
    world.py               (02, 06 §3)
    policies.py            (05)
    simulated_user.py      (06 §7)
    faults.py              (06 §6)
    tools/
        __init__.py  schemas.py  specs.py  dispatch.py  read.py  authorize.py  transfer.py  misc.py
    environment.py         (06 §1, §4, §5)
    replay.py              (06 §8)
    agents/
        __init__.py  base.py  oracle.py  scripted.py  presets.py
    graders/
        __init__.py  base.py  taxonomy.py  _helpers.py  task_success.py  financial.py
        authorization.py  policy.py  safety.py  recovery.py  efficiency.py  auditability.py  aggregate.py
    benchmark/
        __init__.py  loader.py  runner.py  report.py
        v0/  __init__.py  worlds.py  tasks_routine.py  tasks_policy.py  tasks_recovery.py  tasks_adversarial.py
    cli.py
benchmarks/v0/*.json       (frozen export)
reports/v0/oracle.md       (sanity report)
tests/
    conftest.py  test_smoke.py  test_contracts.py  test_money.py  test_world.py  test_policies.py
    test_simulated_user.py  test_faults.py  test_tools_read.py  test_tools_authorize.py
    test_tools_transfer.py  test_environment.py  test_replay.py  test_invariants.py
    test_determinism.py  test_hidden_leak.py  test_benchmark_v0.py  test_oracle.py
    test_graders_helpers.py  test_grader_matrix.py  test_report.py  test_cli.py
```

---

## T0.01 — Repository scaffold and toolchain

**Files**: `pyproject.toml`, `uv.lock`, `.github/workflows/ci.yml`,
`src/agentic_payments_env/__init__.py`, `src/agentic_payments_env/errors.py`,
`tests/conftest.py` (empty fixtures for now), `tests/test_smoke.py`.
**Spec**: AGENTS.md §4–5, 10 §7, 12 D-01.

Steps:
1. `pyproject.toml` with `[project] name="agentic-payments-env"`,
   `requires-python=">=3.11"`, `dependencies=["pydantic>=2.7,<3"]`,
   `[project.optional-dependencies] dev=["pytest>=8","ruff>=0.5","mypy>=1.10"]`,
   build backend `hatchling`, `[tool.hatch.build.targets.wheel] packages=["src/agentic_payments_env"]`,
   `[project.scripts] apenv = "agentic_payments_env.cli:main"`.
2. `[tool.ruff] line-length=100 target-version="py311"`; `select=["E","F","I","UP","B","SIM","RUF"]`.
3. `[tool.mypy] strict=true, python_version="3.11", plugins=["pydantic.mypy"]`, `files=["src"]`.
4. `[tool.pytest.ini_options] testpaths=["tests"]`, `addopts="-q"`.
5. `errors.py`: three exception classes; `InvariantViolation(code: str, message: str)`.
6. `__init__.py`: `__version__ = "0.1.0"` only (re-exports added in T0.11).
7. CI per 10 §7.
8. `tests/test_smoke.py`: imports the package and asserts `__version__`.

Done when:
- [ ] `uv sync --all-extras` succeeds and `uv.lock` is committed.
- [ ] All four verification commands pass.
- [ ] CI file present and valid YAML.

## T0.02 — Core utilities

**Files**: `core/money.py`, `core/hashing.py`, `tests/test_money.py`.
**Spec**: 02 §1, 03 §1 REQ-CON-04.

- `money.format_brl(centavos: int) -> str` → `"R$1.234,56"`, negative as
  `"-R$0,50"`. `money.parse_brl("R$1.234,56") -> int` (used only by tests
  and CLI).
- `hashing.canonical_json(obj: Any) -> str` (sort_keys, compact separators,
  ensure_ascii=False; datetimes must already be strings — callers pass
  `model_dump(mode="json")`). `hashing.sha256_hex(text: str) -> str`.

Tests: round-trip 20 values including 0, 1, 99, 100, 123456789; parse
rejects `"R$1.5"`.

Done when: tests pass; no float anywhere in `core/`.

## T0.03 — Contracts: common and domain

**Files**: `contracts/__init__.py`, `contracts/common.py`,
`contracts/domain.py`, `tests/test_contracts.py` (part 1).
**Spec**: 03 §1–3 (transcribe), 02 §4.

- Add a shared validator `_require_aware(dt)` applied to every `datetime`
  field via `field_validator` (REQ-CON-05). Put it in `common.py` as
  `aware_datetime_validator` and reuse.
- `PolicyConfig.mode()` method as specified.

Tests: each enum's values equal names; naive datetime rejected in
`Beneficiary`, `Consent`, `Transfer`, `AuditEvent`; `Transfer.amount_centavos=0`
rejected; extra field rejected (`extra="forbid"`); `PolicyConfig().mode(X)
== HARD` for all rules.

## T0.04 — Contracts: world, actions, tasks, trace, grading

**Files**: `contracts/world.py`, `contracts/actions.py`, `contracts/tasks.py`,
`contracts/trace.py`, `contracts/grading.py`, `contracts/__init__.py`
(re-export everything), `agents/base.py`, `graders/base.py`,
`tests/test_contracts.py` (part 2).
**Spec**: 03 §4–9 (transcribe), 02 §4.

- `TaskSpec` model validator implementing REQ-CON-09 (all five rules).
- `Observation` model validator implementing REQ-CON-08.
- `FaultInjection` validator: `stale_age_steps` present iff `STALE_READ`.
- `Agent` and `Grader` protocols in `agents/base.py`, `graders/base.py`.

Tests: REQ-CON-09 rules each rejected individually; Observation with both
`result` and `error` rejected; `EpisodeTrace` JSON round-trip equality.

Done when: `from agentic_payments_env.contracts import *` exposes every
class named in 03; mypy strict clean.

## T0.05 — World state, ledger, invariants, hashing

**Files**: `world.py`, `tests/test_world.py`.
**Spec**: 02 §2–6, 06 §3, 03 §4.

Implement every method in 06 §3. Details:
- `from_fixture`: copies entities into dicts; validates that
  `acc_external` exists, that all `pix_directory.account_id`s exist, that
  fixture transfers are COMPLETED and initiated_by FIXTURE, and inserts
  ledger entries for fixture transfers **without** changing balances
  (balances in the fixture already reflect them; INV-02 therefore uses
  `initial_balances` captured *after* insertion as the base and only sums
  entries created after reset — store `fixture_entry_count` to know where
  runtime entries begin). Seeds `balance_history` from
  `balance_history_seed` then appends `(start_time, balance)`; seeds
  `transfer_history[0]`.
- `tick()`: `now += tick_seconds`; append current balances to
  `balance_history`; append transfer status snapshot to `transfer_history`.
- `post_transfer(t)`: asserts PENDING; creates two `LedgerEntry`s; updates
  both account balances (replace frozen `Account` instances); sets
  COMPLETED and `completed_at=now`; returns the new `Transfer`. Does not
  emit audit (the tool does, so it can include consent/auth payload).
- `check_invariants()` implements INV-01..08 exactly; each raises
  `InvariantViolation("INV-0n", ...)`.
- `canonical_json()` excludes `audit`; `hash()` = sha256 of it.

Tests: from_fixture on default world; INV-01 detects a manually corrupted
balance; INV-06 detects two transfers sharing a consent; `hash()` stable
across two constructions; `tick()` appends history.

## T0.06 — Policy engine

**Files**: `policies.py`, `tests/test_policies.py`.
**Spec**: 05 §3–5 (rules table, `in_window`, consent validity, `PolicyDecision`).

- `PolicyFinding`, `PolicyDecision`, `evaluate_transfer_policy` exactly as
  05 §5. Also export `consent_validity(state, consent_id, from_account_id,
  pix_key, amount) -> tuple[bool, str | None]` returning `(True, None)` or
  `(False, reason)` with reasons from 05 §4.
- `in_window(now, window)` as a module-level function.

Tests (one per row of the rules table, plus):
- night window wrap: `(20, 6)` → 23:00 in, 05:59 in, 06:00 out, 19:59 out;
  `(9, 17)` → 9:00 in, 17:00 out.
- daily limit counts only COMPLETED non-reversed same-UTC-date outgoing.
- KYC cap `None` never fires; `NONE` cap 0 fires for any amount.
- cooling: unsaved key fires when cooling > 0; trusted beneficiary never fires.
- step-up: expired `step_up_valid_until` → fires.
- consent validity: all six conditions, each failing alone.
- `evaluate_transfer_policy` returns all findings in table order and never
  mutates `state` (compare `hash()` before/after).

## T0.07 — Simulated user and fault scheduler

**Files**: `simulated_user.py`, `faults.py`, `tests/test_simulated_user.py`,
`tests/test_faults.py`.
**Spec**: 06 §6–7, 03 §6 (UserScript, FaultInjection).

Tests: script exhaustion repeats last entry; `DENY_IF_SCOPE_MISMATCH` denies
a non-expected scope without consuming; scheduler fires on the exact
ordinal once; counts errors as calls; two faults on the same call raise
`TaskValidationError` at construction.

## T0.08 — Tool schemas, specs, dispatch, read tools

**Files**: `tools/schemas.py`, `tools/specs.py`, `tools/dispatch.py`,
`tools/read.py`, `tests/test_tools_read.py`.
**Spec**: 04 §1–2, §3.1–3.5, §3.10–3.12, §4.

- `schemas.py`: one args model per tool (`GetAccountBalanceArgs`, …,
  `FinishArgs`), all `FrozenModel`s; `ARGS_MODELS: dict[str, type[BaseModel]]`.
- `specs.py`: `ToolSpec(name, description, args_schema: dict)` and
  `TOOL_SPECS` built from `ARGS_MODELS` (`model_json_schema()`).
- `dispatch.py`: `dispatch(ctx: ToolContext, action, fault) -> Observation`
  where `ToolContext(state, sim_user, step_index, task_id)`. Handles
  UNKNOWN_TOOL, INVALID_ARGUMENT, EPISODE_FINISHED, and routes to
  `read.py` / `authorize.py` / `transfer.py` / `misc.py` handlers with
  signature `handle(ctx, args, fault) -> Observation`. Provides
  `ok(ctx, tool, result, warnings=[], observed_at=None)` and
  `err(ctx, tool, code, message, details={})` builders that also emit
  `TOOL_RESULT` / `TOOL_ERROR` audit events.
- `read.py`: profile, balance (with STALE_READ), beneficiaries, lookup,
  check_transfer_policy, get_transfer (with STALE_READ via
  `transfer_history`), get_transfer_by_idempotency_key, list_transfers.

Tests: every read tool happy path against the default world; NOT_FOUND for
foreign account; STALE_READ returns the older balance with older `as_of`
and `observed_at`; SERVICE_UNAVAILABLE fault returns the error and emits
`FAULT_INJECTED` invisible; `check_transfer_policy` output for a
too-large amount lists `PER_TRANSFER_LIMIT` and `would_fail_with ==
"POLICY_VIOLATION"`; hidden fields (`account_id` in lookup) absent.

## T0.09 — Authorization and misc tools

**Files**: `tools/authorize.py` (request_consent, request_step_up_auth),
`tools/misc.py` (add_beneficiary, ask_user, finish),
`tests/test_tools_authorize.py`.
**Spec**: 04 §3.6–3.8, §3.14–3.15, 05 §6.

Tests: consent GRANTED/DENIED/PENDING per script with correct audit kinds;
`expires_at = now + ttl`; step-up APPROVE sets auth with TTL and profile
reports `STEP_UP`; after TTL passes (tick past it) profile reports `BASIC`;
add_beneficiary duplicate key → INVALID_ARGUMENT; ask_user consumes script;
finish returns `kind="final"`.

## T0.10 — Transfer and reversal tools

**Files**: `tools/transfer.py`, `tests/test_tools_transfer.py`.
**Spec**: 05 §5 (the whole order, normative), 04 §3.9, §3.13, 02 §5,
08 REQ-GRD-07 (payload fields on `TRANSFER_COMPLETED`).

Tests (each is a numbered requirement; name tests after the step):
- step 0: BEFORE fault → TIMEOUT, no transfer, key unused.
- step 3/4/8: ACCOUNT_BLOCKED, NOT_FOUND, INSUFFICIENT_FUNDS regardless of
  enforcement modes.
- step 5: identical replay returns same id with `idempotent_replay=True`,
  balances unchanged; different args → IDEMPOTENCY_CONFLICT.
- step 7: HARD step-up → AUTH_REQUIRED; HARD consent missing →
  CONSENT_REQUIRED; invalid → CONSENT_INVALID with each reason; HARD limit
  → POLICY_VIOLATION with `details.violations`.
- SOFT limit executes with `warnings`; SILENT executes with no warnings;
  both emit `POLICY_VIOLATION_EXECUTED`.
- step 9: balances, two ledger entries summing to zero, consent USED,
  `TRANSFER_CREATED` then `TRANSFER_COMPLETED` with the REQ-GRD-07 payload.
- step 10: AFTER fault → TIMEOUT returned, but transfer exists COMPLETED
  and `get_transfer_by_idempotency_key` finds it.
- reversal: happy path restores balances (INV-01 holds), original
  REVERSED with `reversed_by`, second reversal → ALREADY_REVERSED; window
  expired; non-sender; reversing a reversal → IS_REVERSAL.
- invariants hold after every test (call `check_invariants()` in a fixture
  teardown).

## T0.11 — Environment and replay

**Files**: `environment.py`, `replay.py`, `src/agentic_payments_env/__init__.py`
(re-exports), `tests/test_environment.py`, `tests/test_replay.py`,
`tests/test_invariants.py`, `tests/test_determinism.py` (partial: default
task only; extended in T0.13).
**Spec**: 06 §1–5, §8, 10 §2–3.

- Implement `PaymentsEnvironment` per 06 §4–5 including reset validation
  (REQ-TOOL-16/18 and 03 REQ-CON-09).
- `trace()` builds `EpisodeTrace`; support `termination=` and `error=`
  keyword overrides for the runner (AGENT_ERROR).
- `replay.replay(task, trace) -> ReplayResult`.

Tests: REQ-ENV-01/02/03/08/09/10; fuzz test per 10 §2 (200 × 15, strict);
replay matches; mutated trace diverges at the right step; `strict=True`
raises if a test monkeypatches `post_transfer` to skip a ledger entry.

## T0.12 — Benchmark v0 worlds and tasks

**Files**: `benchmark/v0/worlds.py`, `benchmark/v0/tasks_routine.py`,
`benchmark/v0/tasks_policy.py`, `benchmark/v0/tasks_recovery.py`,
`benchmark/v0/tasks_adversarial.py`, `benchmark/v0/__init__.py` (`TASKS`
registry, `load_task(task_id)`, `all_tasks()`), `benchmark/loader.py`
(`load_task_file`, `export_tasks`), `benchmarks/v0/*.json`,
`tests/test_benchmark_v0.py` (part 1: validation and freeze).
**Spec**: 02 §9, 07 §1–2, §5–7, §9.

- `worlds.default_world(**overrides) -> WorldFixture` with keyword
  overrides for `policy`, `start_time`, `principal_kyc`, `balance`,
  `extra_beneficiaries`, `extra_directory`, `fixture_transfers`,
  `balance_history_seed`, `beneficiary_nickname_overrides`,
  `holder_name_overrides`.
- One builder per task in 07 §7 with the exact instruction text, world
  modifications, user script, faults, hidden ground truth and oracle plan
  (using `$variables`). `oracle_steps` must equal the table.
- `export_tasks(benchmark_id, out_dir)` writes `<suffix>.json` with
  `indent=2, sort_keys=True, ensure_ascii=False` and a trailing newline.
- Commit the exported files.

Tests: all 31 ids present with the families and expected outcomes of
07 §8; every task validates and `reset()` succeeds; freeze test: export to a
temp dir equals committed bytes file by file.

## T0.13 — Oracle agent

**Files**: `agents/oracle.py`, `agents/__init__.py`, `tests/test_oracle.py`,
extend `tests/test_determinism.py` and add `tests/test_hidden_leak.py`.
**Spec**: 07 §6, 10 §3, §6, 06 REQ-ENV-12, 03 §9.

- `OracleAgent(hidden, task_id)`; variable resolution per 07 §6 including
  substitution inside string arguments; `OraclePlanError` on failure.
- A minimal `run_episode` may be placed in `benchmark/runner.py` now
  (06 §9) since tests need it.

Tests: `test_oracle_passes_every_task` — for every v0 task, run oracle,
grade is not yet available, so assert: `termination == FINISHED`,
`declared_outcome == expected_outcome`, `steps_used == oracle_steps`, and
final `completed_net` transfers equal `expected_transfers` (write a local
helper; it moves to `graders/_helpers.py` in T0.14). Determinism across
two runs for every task. Hidden-leak test per 10 §6.

If a task's oracle plan cannot pass, the **task builder** is wrong (or the
environment is); fix it and note it in `12-decisions.md`.

## T0.14 — Graders

**Files**: `graders/taxonomy.py`, `graders/_helpers.py`, one module per
dimension, `graders/aggregate.py`, `graders/__init__.py`
(`DEFAULT_GRADERS`, `grade_episode`), `tests/test_graders_helpers.py`.
**Spec**: 08 (all), 09 (all).

- `taxonomy.py`: `TaxonomyEntry`, `TAXONOMY` with every code from 09,
  `CATASTROPHIC_CODES`; helper `violation(code, message, step_index=None,
  entity_ids=()) -> Violation` that fills severity and dimension from the
  table (graders never hand-write severities).
- Each grader implements its section of 08 §3 and emits only codes from
  09 for its prefix (plus documented co-fires).
- `aggregate.grade_episode` per 08 §4.

Tests here cover helpers and taxonomy consistency (every code in 09 §1–8
is in `TAXONOMY`; catastrophic set equals 09 §9). Behavioral grader tests
are the matrix in T0.15. Extend `test_oracle.py` to assert
`grade_episode(...).safe_success` for every task.

## T0.15 — Scripted agents and the grader matrix

**Files**: `agents/scripted.py`, `agents/presets.py`,
`tests/test_grader_matrix.py`.
**Spec**: 10 §4–5 (normative config and matrix), 09.

- `ScriptedAgentConfig`, `ScriptedTarget`, `ScriptedAgent` per 10 §4.2,
  including `retry_after_denied: bool = False` for the `after_denial`
  preset.
- `presets.build(name, task) -> Agent` and `presets.NAMES`.
- Matrix test parametrized over every row of 10 §5, asserting exact
  catastrophic sets and required majors. Test-local task variants
  (`pc-004` with SILENT blocked recipient; `rt-001` with `max_steps=2`)
  are built with `model_copy(update=...)`.

This ticket is expected to surface grader bugs. Fix graders, not tests.

## T0.16 — Runner, report, CLI, sanity report

**Files**: `benchmark/runner.py` (complete `run_benchmark`),
`benchmark/report.py`, `cli.py`, `reports/v0/oracle.md`,
`tests/test_report.py`, `tests/test_cli.py`.
**Spec**: 06 §9–10, 08 §5, 12 D-14.

- `run_benchmark` writes traces and results per REQ-ENV-17 plus
  `report.json` and `report.md`.
- `report.py`: `summarize(episodes) -> list[FamilySummary]`,
  `render_markdown(report) -> str` in the 08 §5 layout; `debatable`
  exclusion (REQ-GRD-10).
- `cli.py` with `argparse` and the six commands of 06 §10; `main()` entry
  point.
- Run `apenv bench --benchmark v0 --agent oracle --seeds 0 --out runs/oracle`
  and copy `report.md` to `reports/v0/oracle.md`. This is a sanity artifact
  (expected 100% safe success); it is not a benchmark result.

Tests: summaries on a hand-built list of `EpisodeResult`s (rates, per-code
counts, debatable exclusion, `None` for non-applicable means); CLI
`list-tasks`; `run` on rt-001 with `oracle` and with `quitter`; `replay` on
the produced trace file.

## T0.17 — Documentation sync and exit review

**Files**: `README.md` (status section, quick start, sanity report link),
`docs/12-decisions.md` (all open questions resolved or carried), this
file (tick the exit checklist).

README quick start:

```bash
uv sync --all-extras
uv run apenv list-tasks
uv run apenv run --task v0/fr-001 --agent naive_retry --out runs/demo
uv run apenv bench --benchmark v0 --agent oracle --seeds 0 --out runs/oracle
```

Also add a "Limitations of v0" section to the README listing: synchronous
settlement, single currency, single principal, English-only instructions,
rule-based graders only, no LLM agents yet, no OTP, seed unused for
randomness in v0.

## M0 exit checklist

- [ ] All four verification commands pass locally and in CI on 3.11 and 3.12.
- [ ] `tests/test_grader_matrix.py` passes every row of 10 §5.
- [ ] `test_oracle_passes_every_task`: 31/31 with exact `oracle_steps`.
- [ ] Determinism, replay, fuzz-invariant and hidden-leak tests pass.
- [ ] `benchmarks/v0/*.json` frozen; freeze test passes.
- [ ] `reports/v0/oracle.md` committed and linked from README.
- [ ] README distinguishes the project from an applied demo and lists
      limitations; no unmeasured numbers anywhere.
- [ ] `docs/12-decisions.md` has no unresolved open question that blocks M1.
- [ ] Every `REQ-` id in docs 02–10 is referenced from at least one
      docstring, comment or test name (`grep -r "REQ-" src tests`).
