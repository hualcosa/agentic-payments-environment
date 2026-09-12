# Milestone 7 — Post-implementation spec conformance

Goal: close every repository-local gap found by the post-M6 audit of
`composer25@0418671`, without inventing live-model results or weakening the
normative behavior in docs 02–11.

This is a corrective milestone, not a feature expansion. Execute tickets **in
order**, one commit per ticket. Before each ticket, read every section listed
under **Spec references**; do not work from this plan alone. The existing v0
and v1 frozen bytes are immutable. If corrected generators change a freeze,
publish v1.1 beside v1 rather than rewriting v1.

After **every** ticket run the full repository gate:

```bash
uv sync --all-extras
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest -q
```

Paste the tail in the ticket handoff. A green legacy test is not proof of
conformance when the ticket adds a stronger behavioral assertion.

---

## Phase 0 — Documentation discovery and binding interpretations

The audit read `AGENTS.md`, docs 02–12, milestones M0–M6, all source and test
modules, every frozen benchmark family, annotations, prompts and reports.
These are the allowed implementation mechanisms:

- Pydantic v2 `Field`, `field_validator`, `model_validator`,
  `model_validate` and `model_dump(mode="json")` as established in
  `contracts/` and `benchmark/loader.py`.
- Standard-library `json`, `datetime`, `pathlib`, `hashlib`, `argparse` and
  `random.Random` behind `SeededRng`.
- Existing `WorldState`, `PaymentsEnvironment`, `OracleAgent`, scripted
  presets, graders, loaders and report renderers. Extend these APIs only where
  a ticket explicitly says so.
- Provider SDKs only inside `adapters/`, behind optional extras. Core imports,
  tests and benchmark generation remain network-free.

Anti-pattern guards for the entire milestone:

- Do not edit frozen v0/v1 JSON by hand or in place. Regenerate through a
  builder/exporter, and version any changed freeze.
- Do not use `model_copy(update=...)` at an input or fixture-validation
  boundary; it bypasses Pydantic validation.
- Do not satisfy REQ coverage with a comment bank, an `assert True`, or a
  docstring unrelated to the implementation.
- Do not add runtime dependencies, wall-clock calls, unseeded randomness,
  network access to the core, hidden ground truth in observations, or floats
  for money.
- Do not hide an oracle violation, catastrophic code, invariant failure or
  report discrepancy by weakening a test.

### T7.01 — Record the audit's binding decisions

**Files**: `docs/12-decisions.md`, `AGENTS.md`.

**Spec references**: AGENTS.md §§1–3 and §7; `docs/02-domain-model.md` §2–4,
§6; `docs/03-contracts.md` §1, §3; `docs/07-tasks-and-benchmark-v0.md` §1,
§7.2–7.4; `docs/09-failure-taxonomy.md` AUTH-07 and REC-04;
`docs/10-testing-strategy.md` §5; `docs/11-roadmap.md` M1, M3–M6.

Append decisions; never delete or renumber existing entries:

- The exact adv-001 fixture in 07 §7.4 wins over the generic 80-character
  beneficiary cap. Frozen fixtures may hold nicknames up to 200 characters;
  agent-facing `add_beneficiary` remains capped at 80.
- Money boundaries are strict: reject `bool`, strings, `float` and `Decimal`,
  even when Pydantic could coerce them to an integer. This is the conservative
  interpretation of REQ-DOM-01/03 for agent actions.
- Datetimes with non-zero UTC offset are rejected; UTC `Z`/`+00:00` is
  accepted. Do not silently normalize a non-UTC fixture.
- Schema versions must be syntactically `major.minor`; v0 contracts accept
  major `0` and reject every unknown major.
- The specific runtime API in 06 §3 wins over the general `IdGenerator` and
  `SimClock` wording: `WorldState.next_id()` and `tick()` remain the
  implementation. The unused `evt_` prefix is reserved; `AuditEvent.seq`
  remains its normative identity.
- The oracle row in the normative grader matrix wins over broad AUTH-07 and
  REC-04 readings. AUTH-07 requires observable scope drift followed by a
  correction; an honestly denied intended scope is not drift. A transfer
  rejected by the true-state insufficient-funds guard on the prescribed
  fr-004 path is not REC-04.
- Optional provider networking is allowed only in M1+ adapter modules behind
  extras; importing the package/core must not load an SDK or read credentials.
- The M4 task-success reward gate, the annotation-code regex correction and
  the long-form M3–M6 roadmap deliverables are explicit conformance work in
  this milestone, not undocumented scope reductions.
- Supersede the incorrect Q-06 claim: `uv run pytest -q` is the canonical gate
  and is proven by local and CI runs.

Clarify the contradictory network bullets in `AGENTS.md` without broadening
adapter authority beyond the paragraph above.

**Tests / verification**: no behavioral test in this documentation-only
ticket; grep all `Q-nn`/`D-nn` references and confirm every referenced id now
exists in `docs/12-decisions.md`.

**Done when**: the decisions are explicit enough that later tickets require no
silent interpretation; the full gate passes.

### T7.02 — Enforce top-level artifact versions and required fields

**Files**: `src/agentic_payments_env/contracts/common.py`,
`src/agentic_payments_env/contracts/tasks.py`,
`src/agentic_payments_env/contracts/trace.py`,
`src/agentic_payments_env/contracts/grading.py`,
`src/agentic_payments_env/benchmark/loader.py`, `tests/test_contracts.py`,
`tests/test_report.py`.

**Spec references**: `docs/03-contracts.md` REQ-CON-03/04/06 and §§6–8;
`docs/08-graders-and-metrics.md` REQ-GRD-04/05/06 and §4.

- Add one shared schema-version validator. Apply it to `TaskSpec`,
  `EpisodeTrace`, `EpisodeResult` and `BenchmarkReport`, including loader
  entry points.
- Reject malformed versions and unknown majors; keep `SCHEMA_VERSION = "0.1"`
  as the emitted default.
- Restore the six normative required fields by removing defaults from
  `EpisodeTrace.audit`, `EpisodeResult.violations`,
  `EpisodeResult.catastrophic_codes`, `FamilySummary.violation_counts`,
  `FamilySummary.catastrophic_counts` and `BenchmarkReport.summaries`.
- Preserve JSON round-trip equality for valid artifacts.

**Tests**: parameterize all four top-level artifacts for accepted `0.1` and
rejected malformed/unknown-major versions; remove each required field from a
valid payload and assert `ValidationError`; exercise `load_task_file()` with an
unknown major.

**Done when**: incomplete or incompatible artifacts fail at load time and the
full gate passes.

### T7.03 — Harden money, time, observations and audit payload contracts

**Files**: `src/agentic_payments_env/contracts/common.py`,
`src/agentic_payments_env/contracts/actions.py`,
`src/agentic_payments_env/contracts/domain.py`,
`src/agentic_payments_env/contracts/world.py`,
`src/agentic_payments_env/tools/schemas.py`, `tests/test_contracts.py`,
`tests/test_money.py`.

**Spec references**: `docs/02-domain-model.md` REQ-DOM-01/02/03/07/15;
`docs/03-contracts.md` REQ-CON-04/05/08 and §§3–5;
`docs/04-tools-and-actions.md` §1.

- Define a reusable strict-centavos annotation/validator using only Pydantic;
  retain integer arithmetic and reject coercion from `bool`, strings, floats
  and `Decimal` at every monetary contract and tool boundary.
- Make the shared datetime validator require an aware zero-offset UTC value.
  Apply it to every direct datetime and to every tuple in
  `WorldFixture.balance_history_seed` and `WorldState.balance_history`.
- Validate `AuditEvent.payload` recursively as JSON values at construction so
  a trace cannot fail only during serialization. Reject sets, callables,
  arbitrary objects, NaN and infinities.
- Require a `final` observation to have a result, no error, and string
  `outcome`/`report` members. Preserve the existing tool-result/tool-error
  exclusivity.

**Tests**: cover every monetary model family and every datetime-bearing model;
test nested histories; test accepted JSON payload nesting and rejected
non-JSON values; test all invalid final-observation shapes. Keep BRL parser
grouping tests strict.

**Done when**: invalid values fail before state mutation and the full gate
passes without `Decimal` or float money appearing in `src/`.

### T7.04 — Validate fixture structure at the contract boundary

**Files**: `src/agentic_payments_env/contracts/world.py`,
`src/agentic_payments_env/contracts/tasks.py`,
`src/agentic_payments_env/world.py`,
`src/agentic_payments_env/benchmark/loader.py`, `tests/test_contracts.py`,
`tests/test_world.py`.

**Spec references**: `docs/02-domain-model.md` §4.3–4.9 and REQ-DOM-10/11;
`docs/03-contracts.md` REQ-CON-07/09 and §4;
`docs/06-environment-runtime.md` §3–4 and REQ-TOOL-16/18.

- Reject duplicate customer, account, directory-key, beneficiary and transfer
  identities before dict construction can collapse them.
- Require exactly one `acc_external`, owned by `cus_external`.
- Require principal customer/account existence and ownership at model load.
- Require directory account references and fixture-transfer endpoints to
  exist. Fixture transfers must be `COMPLETED`, `initiated_by=FIXTURE`, have a
  valid destination key/account relationship and usable timestamps.
- Keep `WorldState.from_fixture()` defensive, but do not rely on reset as the
  first validation boundary.

**Tests**: one negative test per rule through both `TaskSpec.model_validate`
and `load_task_file`; a valid fixture still resets and round-trips.

**Done when**: malformed fixtures produce validation errors rather than a
later `KeyError`/runtime crash and the full gate passes.

### T7.05 — Make grading contracts internally consistent

**Files**: `src/agentic_payments_env/contracts/grading.py`,
`src/agentic_payments_env/graders/__init__.py`, `tests/test_contracts.py`,
`tests/test_report.py`, `tests/test_rewards_episode.py`.

**Spec references**: `docs/03-contracts.md` §8;
`docs/08-graders-and-metrics.md` REQ-GRD-03–06 and §4;
`docs/09-failure-taxonomy.md` §9.

- Constrain every applicable score to finite `[0, 1]`.
  `applicable=False` requires `score=None`; `applicable=True` requires a
  score. Validate `passed` against the normative threshold and severities.
- Require all eight dimensions in a default aggregated `EpisodeResult`.
- Require `catastrophic_codes` to equal the sorted, de-duplicated codes of
  catastrophic violations; require `task_success` to equal the
  TASK_SUCCESS result and `safe_success == task_success and not cats`.
- Keep aggregation as the canonical producer; the contract must reject a
  hand-built result that hides a catastrophic violation.

**Tests**: reject out-of-range, NaN/infinite and applicability mismatches;
reject missing dimensions and inconsistent catastrophic/task/safe flags;
accept the boundaries and all real aggregated results.

**Done when**: catastrophic failures cannot be serialized as safe through a
malformed `EpisodeResult` and the full gate passes.

### T7.06 — Enforce exact ledger and same-step audit invariants

**Files**: `src/agentic_payments_env/world.py`,
`src/agentic_payments_env/tools/authorize.py`,
`src/agentic_payments_env/tools/misc.py`,
`src/agentic_payments_env/tools/transfer.py`, `tests/test_invariants.py`,
`tests/test_world.py`, `tests/test_graders_helpers.py`.

**Spec references**: `docs/02-domain-model.md` REQ-DOM-14/15/19, INV-02 and
INV-04, §§6–7; `docs/06-environment-runtime.md` §3;
`docs/08-graders-and-metrics.md` FIN-04 and AUD-02.

- For every COMPLETED or REVERSED transfer require exactly two ledger entries:
  the correct debit/credit accounts, deltas `-amount/+amount`, matching
  transfer id, and zero sum. Zero, one, three, zero-valued or wrong-account
  entries must fail INV-02. Preserve the fixture-ledger accounting decision.
- Track or deterministically derive the creation step for runtime transfers,
  ledger entries, consents, challenges and beneficiaries. INV-04 must require
  a normative creation event with the entity id at that exact step; a later
  generic reference is insufficient.
- Keep creation metadata private and excluded from canonical state hashes.

**Tests**: targeted negative mutations for every ledger shape and each entity
kind; wrong-step and wrong-event-kind audit references; verify FIN-04/AUD-02
surface the invariant; replay/determinism hashes remain stable.

**Done when**: the previously accepted missing-ledger and late-audit probes
raise the correct invariant codes and the full gate passes.

### T7.07 — Correct fault order and terminal audit emission

**Files**: `src/agentic_payments_env/tools/dispatch.py`,
`src/agentic_payments_env/tools/transfer.py`,
`src/agentic_payments_env/environment.py`, `tests/test_faults.py`,
`tests/test_tools_transfer.py`, `tests/test_environment.py`.

**Spec references**: `docs/04-tools-and-actions.md` REQ-TOOL-02/05/13/17 and
§3.9; `docs/05-policies-and-authorization.md` §5;
`docs/06-environment-runtime.md` REQ-ENV-10/11.

- Apply and invisibly audit `TIMEOUT_BEFORE_EXECUTE` and
  `SERVICE_UNAVAILABLE` before argument validation. A scheduled fault is not
  silently consumed by an `INVALID_ARGUMENT` response.
- For successful TIMEOUT_AFTER execution, perform the mutation but emit only
  the terminal `TOOL_ERROR`, never both `TOOL_RESULT` and `TOOL_ERROR`.
  Preserve all domain mutation/audit events and the returned timeout.
- Apply the same rule to create and reverse transfer, including idempotent
  paths and rejected operations.
- When `strict=False` sanitizes an unexpected handler exception, emit exactly
  one audited `TOOL_ERROR`; with `strict=True`, propagate the original bug.

**Tests**: invalid args plus each pre-execution fault; exact audit sequence for
before/after faults; create/reverse timeout-after state checks; monkeypatched
internal error under both strict modes. Assert every call has one and only one
terminal tool audit event.

**Done when**: fault ordering matches the normative chain and the full gate
passes.

### T7.08 — Repair frozen-task validation without rewriting v0

**Files**: `src/agentic_payments_env/contracts/domain.py`,
`src/agentic_payments_env/benchmark/v0/worlds.py`,
`src/agentic_payments_env/benchmark/loader.py`,
`tests/test_benchmark_v0.py`, `tests/test_benchmark_v1.py`,
`docs/12-decisions.md` only if T7.01 needs a factual addendum.

**Spec references**: `docs/03-contracts.md` Beneficiary;
`docs/07-tasks-and-benchmark-v0.md` REQ-TASK-01/02/04 and §7.4;
`docs/milestones/M0-scaffold.md` T0.12; D-10 and the T7.01 decision.

- Allow the exact long adv-001 nickname at the frozen fixture contract while
  retaining the 80-character agent tool limit.
- Replace unvalidated beneficiary nickname overrides with a validating
  construction path.
- Strengthen freeze tests so every committed JSON in v0, v1 and v1-train is
  loaded from bytes with `TaskSpec.model_validate`, reset successfully, and
  remains byte-identical to its exporter.
- Do not change any existing v0 JSON byte.

**Tests**: explicitly load `benchmarks/v0/adv-001.json`; iterate all committed
task JSON; prove a 201-character fixture nickname and an 81-character
`add_beneficiary` argument are rejected.

**Done when**: all 271 existing frozen JSON files validate and reset, v0 bytes
are unchanged, and the full gate passes.

### T7.09 — Make the normative oracle row truly violation-free

**Files**: `src/agentic_payments_env/graders/authorization.py`,
`src/agentic_payments_env/graders/recovery.py`,
`tests/test_grader_matrix.py`, `tests/test_oracle.py`,
`reports/v0/oracle.md`, `docs/12-decisions.md` only for a T7.01 addendum.

**Spec references**: `docs/07-tasks-and-benchmark-v0.md` REQ-TASK-04,
pc-005 and fr-004; `docs/09-failure-taxonomy.md` AUTH-07/REC-04;
`docs/10-testing-strategy.md` §5; the T7.01 precedence decision.

- AUTH-07 must detect an unused wrong scope followed by correction, not the
  intended consent that the user honestly denied in pc-005.
- REC-04 must not flag the prescribed fr-004 action that is safely rejected by
  the true-state insufficient-funds guard and ends honestly BLOCKED. Preserve
  detection for genuinely unsafe stale-data behavior.
- Strengthen the matrix's `every v0 task | oracle` row to require
  `result.violations == []`, not merely empty catastrophic codes.
- Regenerate the oracle report from the corrected grader output; never edit
  its numbers by hand.

**Tests**: explicit pc-005 and fr-004 oracle regressions plus positive AUTH-07
and REC-04 adversarial cases.

**Done when**: all 31 oracle episodes have exact steps, safe success and zero
violations; the report is reproducible; the full gate passes.

### T7.10 — Restore genuinely parametric synthetic generators

**Files**: `src/agentic_payments_env/generators/base.py`,
`src/agentic_payments_env/generators/routine.py`,
`src/agentic_payments_env/generators/policy.py`,
`src/agentic_payments_env/generators/recovery.py`,
`src/agentic_payments_env/generators/adversarial.py`,
`src/agentic_payments_env/generators/validate.py`,
`tests/test_generators_base.py`, `tests/test_generators_routine.py`,
`tests/test_generators_policy.py`, `tests/test_generators_recovery.py`,
`tests/test_generators_adversarial.py`, `tests/test_generators_validate.py`.

**Spec references**: `docs/11-roadmap.md` M3;
`docs/milestones/M3-synthetic.md` T3.01–T3.06.

- Make seed/RNG, recipient count, name collision, Portuguese, supported fault
  kind/ordinal, injection template/placement and user-script variation affect
  generated semantics. Extend `GenParams` only for knobs explicitly named by
  the roadmap.
- The routine oracle must include the required `check_transfer_policy` step
  and update its oracle step count.
- Constrain fault ordinals to calls that exist in the generated oracle; every
  configured fault must fire in its oracle trace.
- Same seed/params/task id yields byte-identical tasks; selected different
  seeds or knob values must yield a documented semantic difference.
- Every accepted task passes its oracle with zero violations and fails at
  least one scripted adversary.

**Tests**: one paired test per knob, exact routine tool sequence, fault-fired
audit assertion, determinism and validity across a representative parameter
matrix.

**Done when**: no declared generator knob is discarded and the full gate
passes.

### T7.11 — Publish a complete v1.1 pool and measured difficulty artifact

**Files**: `src/agentic_payments_env/generators/pool.py`,
`src/agentic_payments_env/benchmark/loader.py`,
`src/agentic_payments_env/benchmark/v1_1/__init__.py`,
`benchmarks/v1.1/`, `benchmarks/v1.1-train/`,
`reports/v1.1/difficulty.md`, `tests/test_benchmark_v1_1.py`,
`tests/test_generators_difficulty.py`.

**Spec references**: `docs/11-roadmap.md` M3 exit and M3 detail;
`docs/milestones/M3-synthetic.md` T3.07–T3.08; D-10.

- Generate and validate at least 1,000 tasks before splitting. Freeze exactly
  200 deterministic held-out tasks in v1.1 and keep the rest as training data.
  Preserve all v1 files unchanged.
- Rebuild both splits from generator configs in a test; compare file names and
  bytes, not merely files loaded from the freeze itself.
- Compute deterministic scripted-adversary failure rate per task using the
  five named presets, correlate it with `difficulty_score`, and publish sample
  size, family distribution, coefficient and interpretation. Label only live
  LLM correlation as not yet measured.
- Keep held-out and training sets disjoint by task id and content hash.

**Tests**: candidate/valid count, 200/rest split, family balance,
reconstruction, disjointness, all-JSON validation, deterministic correlation
recalculation matching the report.

**Done when**: the M3 headline exit is evidenced rather than asserted and the
full gate passes within the repository's test-time budget.

### T7.12 — Enable end-to-end evaluation for every frozen benchmark

**Files**: `src/agentic_payments_env/cli.py`,
`src/agentic_payments_env/benchmark/loader.py`,
`src/agentic_payments_env/benchmark/runner.py`, `tests/test_cli.py`,
`tests/test_benchmark_v1.py`, `tests/test_benchmark_v1_1.py`.

**Spec references**: `docs/06-environment-runtime.md` §10;
`docs/milestones/M3-synthetic.md` T3.08;
`docs/11-roadmap.md` M5 evaluation loop.

- Route task and benchmark selection through the general loader instead of
  importing v0 directly.
- Support list-tasks, run, bench, replay and export-tasks for v0, v1 and v1.1.
- Add an optional one-task selector to bench for deterministic smoke tests; do
  not change the full-benchmark default.
- Preserve the hidden-data boundary for every agent type.

**Tests**: CLI smoke for each command/version; a one-task v1.1 fake-LLM bench
must write trace, result, report and meta artifacts.

**Done when**: the frozen held-out sets are actually runnable from the public
CLI and the full gate passes.

### T7.13 — Persist normalized LLM turns outside provider-agnostic traces

**Files**: `src/agentic_payments_env/adapters/base.py`,
`src/agentic_payments_env/agents/llm.py`,
`src/agentic_payments_env/benchmark/runner.py`,
`src/agentic_payments_env/cli.py`, `tests/test_agents_llm.py`,
`tests/test_cli.py`, `tests/test_adapters_isolation.py`.

**Spec references**: `docs/11-roadmap.md` M1 run harness;
`docs/milestones/M1-baseline-agents.md` constraints and T1.03–T1.05;
`docs/03-contracts.md` REQ-CON-10.

- Record a normalized model-turn log containing model id, text, parsed tool
  calls and usage for every completion. Never serialize SDK response objects,
  credentials or environment variables.
- Write the log as a deterministic sidecar beside `meta.json`; keep
  `Observation`, `Step` and `EpisodeTrace` provider-agnostic.
- Preserve prompt hashes and current usage accounting.
- Add the missing subprocess isolation test proving
  `import agentic_payments_env` loads neither provider SDK.

**Tests**: valid tool call, malformed arguments, text-only and multi-turn logs;
sidecar schema/round-trip; no provider imports from the core in a fresh
process.

**Done when**: raw normalized evidence needed for run review exists without
contaminating traces or core imports, and the full gate passes.

### T7.14 — Reconcile step rewards and complete anti-gaming coverage

**Files**: `src/agentic_payments_env/rewards/episode.py`,
`src/agentic_payments_env/rewards/step.py`,
`tests/test_rewards_episode.py`, `tests/test_rewards_step.py`,
`reports/v1/reward-spec.md`, `docs/12-decisions.md` only for a T7.01 addendum.

**Spec references**: `docs/11-roadmap.md` M4;
`docs/milestones/M4-rewards.md` T4.01–T4.02.

- Implement the required `step_reward(trace, step_index)` and define
  `step_rewards(trace)` in terms of it. Use one documented step-index
  convention and reject invalid indices.
- Reconcile the normative per-step domain with the implementation. Since one
  action occurs per step, each awarded step is `10`; no report may claim
  unreachable `20/30` values. Preserve a list exactly as long as the trace.
- Keep the recorded task-success hard gate in episode reward and test it as
  the anti-gaming constraint.
- Add one farming agent for each shaped term: repeated verification, consent
  requests and timeout-status checks. Each unsolved episode must have episode
  reward `<= 0`, including combined/repeated farming.

**Tests**: individual positive terms, empty trace, invalid index, singular/list
API equality and all farmers. Derive report examples from test fixtures.

**Done when**: code, tests and reward report describe the same API and value
domain, every shaped term has an anti-gaming proof, and the full gate passes.

### T7.15 — Export usable preference and SFT datasets

**Files**: `src/agentic_payments_env/rewards/pairs.py`,
`src/agentic_payments_env/export_sft.py`,
`src/agentic_payments_env/cli.py`,
`src/agentic_payments_env/contracts/training.py`,
`datasets/preferences-v1.1.jsonl`, `datasets/sft-v1.1.jsonl`,
`tests/test_rewards_pairs.py`, `tests/test_export_sft.py`.

**Spec references**: `docs/11-roadmap.md` M4 preference pairs and M5 SFT;
`docs/milestones/M4-rewards.md` T4.03;
`docs/milestones/M5-optimization.md` T5.02.

- Define frozen, versioned contracts for a preference record and SFT record.
  Preference records include task id, seed, chosen/rejected actions or traces,
  both rank keys and provenance; agent-A/agent-B and oracle/scripted pairs are
  supported. Handle ties explicitly or exclude them deterministically.
- Export deterministic JSONL and prove byte-for-byte reconstruction.
- Expand SFT export from one-task oracle-only mode to benchmark/task lists,
  oracle traces and non-oracle traces filtered by `safe_success`.
- Training exports may use v1.1-train and v0; they must never read v1/v1.1
  held-out tasks.

**Tests**: contract validation, ranking provenance, deterministic rebuild,
JSONL parsing, safe filtering and a hard held-out-leakage failure.

**Done when**: M4 produces an actual training-ready preference dataset, M5
owns a safe SFT dataset, and the full gate passes.

### T7.16 — Correct annotation constraints and canonical test fixtures

**Files**: `src/agentic_payments_env/annotations/schema.py`,
`tests/test_annotations.py`, `tests/conftest.py`, `tests/test_world.py`,
`tests/test_contracts.py`, `docs/12-decisions.md` only for a T7.01 addendum.

**Spec references**: `docs/milestones/M2-failure-analysis.md` T2.01;
`docs/09-failure-taxonomy.md`; `docs/10-testing-strategy.md` REQ-TEST-02.

- Require `StepAnnotation.step_index >= 1`; an episode with no steps has an
  empty annotation list, never a step zero annotation.
- Validate codes against the actual taxonomy, not only a permissive regex.
  Document that three- and four-letter prefixes are required by existing
  `FIN`/`AUTH`/`TASK` codes.
- Move canonical positive world/task construction into `tests/conftest.py`.
  Tests may build minimal local invalid objects only when the invalid shape is
  the subject of that test.

**Tests**: invalid step indices and unknown-but-well-shaped codes; every
taxonomy code accepted; static check that positive canonical fixtures are not
duplicated in test modules.

**Done when**: annotations cannot reference impossible steps/codes, test worlds
obey REQ-TEST-02, and the full gate passes.

### T7.17 — Replace declarative REQ coverage with executable traceability

**Files**: `tests/test_req_coverage.py`, `tests/test_source_conventions.py`,
and only the existing `src/agentic_payments_env/**/*.py` and `tests/test_*.py`
files reported by the new checks.

**Spec references**: AGENTS.md §§1, 2 and 4;
`docs/milestones/M0-scaffold.md` T0.17 and exit checklist;
`docs/02-domain-model.md` through `docs/10-testing-strategy.md`.

- Delete the tautological coverage sentinel. Extract every REQ id from docs
  02–10 and require each to appear near its owning implementation and in a
  behavioral/static test that can fail.
- Add one-line purpose docstrings with accurate REQ ids to every public class,
  function and method. Cover contracts, schemas, handlers, agent/grader
  protocols, task builders and generator helpers; do not exempt a whole
  package to make the checker green.
- Ensure REQ-DOM-02 and REQ-DOM-10, currently absent from all code/tests, are
  attached to the implementation and regressions created in earlier tickets.
- Do not rewrite old commits. Make the corrective commit message enumerate the
  requirements whose traceability is restored.

**Tests**: AST-based public-symbol docstring check; docs-to-code and
docs-to-test REQ set equality; explicit failure fixtures proving a detached
comment bank and `assert True` cannot satisfy coverage.

**Done when**: all 102 normative REQ ids have accountable implementation and
test evidence, no public API lacks the required docstring, and the full gate
passes.

### T7.18 — Make documentation and claimed results internally truthful

**Files**: `README.md`, `docs/12-decisions.md`,
`docs/milestones/M0-scaffold.md`, `docs/milestones/M1-baseline-agents.md`,
`docs/milestones/M3-synthetic.md`, `docs/milestones/M4-rewards.md`,
`docs/milestones/M5-optimization.md`, `docs/milestones/M6-report.md`,
`reports/technical-report.md`, `reports/v0/oracle.md`,
`reports/v1/reward-spec.md`, `reports/reproducibility.md`,
`tests/test_technical_report.py`, `tests/test_reproducibility.py`.

**Spec references**: AGENTS.md no-fabricated-results rule; D-14;
`docs/11-roadmap.md` M1–M6; each milestone exit checklist.

- Remove stale statements such as “No LLM agents yet”; distinguish default
  rule graders from the opt-in report judge.
- Replace the claim that oracle numbers come from a committed raw run with the
  accurate D-14 provenance: a committed reviewed report reproducible from the
  documented command.
- Make every Q/D reference resolve. Remove inherited Q-16/Q-17 numbering or
  point to the decisions actually created in T7.01.
- Reopen any historical exit checkbox whose evidence was false, then mark it
  complete only when the corresponding M7 ticket has supplied evidence.
  Resolve the three unchecked T0.01 boxes consistently with the final gate and
  CI record.
- Update report paths/version labels for v1.1 and generated datasets without
  inventing live-model measurements.

**Tests**: reference-integrity scan; no stale capability claims; every numeric
claim has a committed report/dataset source and a deterministic reproducer.

**Done when**: docs describe the code that exists after M7, all status claims
are evidenced, and the full gate passes.

### T7.19 — Provide one-command clean-clone reproducibility

**Files**: `src/agentic_payments_env/reproduce.py`,
`src/agentic_payments_env/cli.py`, `reports/reproducibility.md`,
`tests/test_reproducibility.py`.

**Spec references**: `docs/11-roadmap.md` M6;
`docs/milestones/M6-report.md` T6.02; D-14.

- Add one CLI command that rebuilds, into a caller-provided temporary output
  directory, every repository-owned artifact or table cited by the technical
  report: oracle report, annotation corpus, taxonomy/agreement summaries,
  v1.1 split and difficulty report, reward examples, preference data and SFT
  data.
- In `--check` mode compare regenerated outputs against committed artifacts and
  exit non-zero on any byte or normalized-data discrepancy.
- Never delete or overwrite caller data; require an empty/nonexistent narrow
  output directory. Do not run live providers or require credentials.

**Tests**: end-to-end invocation in `tmp_path`, success against committed
artifacts, deliberate copied-artifact mismatch returns non-zero, and no writes
outside the chosen directory.

**Done when**: one documented command proves every in-repo headline result
from a clean checkout and the full gate passes.

### T7.20 — Final conformance audit and exit review

**Files**: this file, `README.md`, `docs/12-decisions.md`.

**Spec references**: all sections referenced by T7.01–T7.19; AGENTS.md §5.

Run and record all of the following without changing expected outputs to make
them pass:

1. The full four-command gate on Python 3.11 and 3.12.
2. Load, round-trip and reset every committed task JSON in v0, v1,
   v1-train, v1.1 and v1.1-train.
3. Run every oracle; require exact oracle steps, `safe_success=True`,
   `violations=[]`.
4. Rebuild annotation, benchmark, difficulty, reward, preference and SFT
   artifacts and compare them to committed bytes/data.
5. Run the one-command reproducer in a fresh temporary directory.
6. Search `src/` for wall clock, unseeded randomness, money floats/Decimal,
   forbidden network imports outside adapters, hidden-observation leakage and
   new runtime dependencies.
7. Run the AST docstring and REQ traceability checks; all 102 ids must have
   implementation and test evidence.
8. Confirm `git diff --check` and that old v0/v1 frozen bytes were not changed.

If any check fails, leave the exit checklist open and create the next numbered
ticket instead of weakening the checker.

## M7 exit checklist

- [x] Full verification passes on Python 3.11 and 3.12.
- [x] Every committed task JSON validates; v0/v1 historical bytes are unchanged.
- [x] All v0 and generated benchmark oracles are safe and violation-free.
- [x] Fault ordering and exactly-one terminal audit semantics are proven.
- [x] INV-02 and INV-04 reject all audited negative cases.
- [x] Serialized contracts reject incompatible, incomplete or inconsistent data.
- [x] At least 1,000 generated tasks back the versioned v1.1 freeze/training split.
- [x] Difficulty, reward, preference and SFT artifacts rebuild deterministically.
- [x] CLI evaluates v0, v1 and v1.1 end to end.
- [x] All 102 REQ ids have nearby implementation and executable test evidence.
- [x] Every public class/function/method has its required purpose + REQ docstring.
- [x] Documentation references and result provenance are internally consistent.
- [x] One clean-checkout command reproduces every repository-owned headline artifact.

## T7.20 audit record (2026-09-09)

1. Gate on Python 3.11.16 and 3.12.14: `ruff format --check`, `ruff check`,
   `mypy src`, `pytest -q` all clean.
2. Task JSON: freeze/loader tests round-trip v0, v1, v1-train, v1.1, v1.1-train.
3. Oracle matrix: `test_oracle_matrix_every_task` — exact steps, safe_success,
   violations `[]`.
4. `apenv reproduce --out /tmp/apenv-repro --check` byte-matches committed artifacts.
5. `git diff --check` clean; no M7 commit modified `benchmarks/v0/` or
   `benchmarks/v1/` frozen JSON.
6. `src/` scan: no wall clock, unseeded RNG, or network in core; Decimal only
   in centavos rejection validator; hidden leak tests pass.
7. `tests/test_req_coverage.py` and `tests/test_source_conventions.py` green
   for all 102 REQ ids.

### T7.21 — Close post-audit safety and artifact gaps

**Files**: `src/agentic_payments_env/world.py`,
`src/agentic_payments_env/tools/authorize.py`,
`src/agentic_payments_env/tools/misc.py`,
`src/agentic_payments_env/tools/transfer.py`,
`src/agentic_payments_env/contracts/grading.py`,
`src/agentic_payments_env/contracts/training.py`,
`src/agentic_payments_env/rewards/pairs.py`,
`src/agentic_payments_env/reproduce.py`, `tests/test_invariants.py`,
`tests/test_world.py`, `tests/test_tools_transfer.py`, `tests/test_contracts.py`,
`tests/test_report.py`, `tests/test_rewards_pairs.py`,
`tests/test_reproducibility.py`, `datasets/preferences-v1.1.jsonl`,
`reports/v1/reward-spec.md`, and this file.

**Spec references**: `docs/02-domain-model.md` INV-04;
`docs/03-contracts.md` section 8; `docs/08-graders-and-metrics.md`
REQ-GRD-03--06; `docs/11-roadmap.md` M4--M6; T7.05, T7.06, T7.15 and
T7.19 above.

- Record runtime entity creation at the mutation site and reject missing
  creation metadata, so a missing or later audit event cannot satisfy INV-04.
- Require `GraderResult.passed` to match the normative threshold for every
  applicable dimension. Require `EpisodeResult.violations` to equal the
  de-duplicated union of all dimensional violations.
- Store chosen and rejected action traces in every preference record and
  support explicit agent-A/agent-B pairs as well as the default
  oracle/scripted pairs.
- Generate the reward specification and executable reward examples from code;
  compare the regenerated file in `apenv reproduce --check` rather than
  copying it from the checkout.

**Tests**: direct unaudited-entity and late-event probes; hidden dimensional
catastrophe and non-normative `passed` probes; preference action-pair and
explicit-agent-pair coverage; reward artifact tamper/check coverage.

**Done when**: all four independent review findings are covered by failing
regressions before the fixes, the generated datasets/reports are refreshed,
and the full Python 3.11 verification gate passes.
