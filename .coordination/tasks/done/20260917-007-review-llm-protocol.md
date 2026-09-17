---
id: 20260917-007-review-llm-protocol
title: Review LLM protocol acceptance, repair gaps and commit verified work
status: done
harness: codex
owner: codex/llm-protocol-review
created_at: 2026-09-17T11:36:28Z
updated_at: 2026-09-17T11:43:08Z
claimed_at: 2026-09-17T11:36:28Z
scope: Acceptance review of tasks 004-006, safe diagnostic persistence, regression strengthening and authorized commits
expected_files: ["src/agentic_payments_env/agents/llm.py", "src/agentic_payments_env/benchmark/runner.py", "src/agentic_payments_env/cli.py", "tests/test_agents_llm.py", "tests/test_llm_protocol_integration.py", "docs/12-decisions.md", ".coordination/context/project.md", ".coordination/tasks/in-progress/20260917-007-review-llm-protocol.md", ".coordination/tasks/done/20260917-007-review-llm-protocol.md", ".coordination/handoffs/*-20260917-007-review-llm-protocol-codex-to-owner.md", ".coordination/README.md", ".coordination/decisions/README.md", ".coordination/handoffs/README.md", ".coordination/plans/README.md", ".coordination/tasks/backlog/README.md", ".coordination/tasks/done/README.md", ".coordination/tasks/in-progress/README.md", ".coordination/templates/decision.md", ".coordination/templates/handoff.md", ".coordination/templates/task.md", ".cursor/rules/coordination.mdc", ".coordination/plans/2026-09-17-pytest-import-path.md", ".coordination/tasks/done/20260917-003-prepare-llm-tool-tasks.md"]
depends_on: ["20260917-004-llm-agent-protocol", "20260917-005-provider-tool-protocol", "20260917-006-llm-protocol-integration"]
---

# Objective
Review implemented tasks against every acceptance criterion; fix verified gaps and
commit reviewed code only after fresh integrated verification. User authorized
commits and fixes, not push, paid/model calls or unrelated changes.

## Acceptance criteria
- Full acceptance mapping for 004/005/006, including negative probes and artifacts.
- Protocol error reason persists safely with token usage, without trace contract change.
- Integration verifies actual serialized observation bodies and atomic audit/state behavior.
- Full gate, oracle equivalence, shared validator and clean staged diff checks pass.
- Separate coherent commits; preserve unrelated preexisting local configuration.

## Initial review state
Base dae3b95 on codex/sync-workspace; previous implementation uncommitted.
Read-only reviewers examine adapters/integration; sole writer is primary Codex.
Confirmed gap: environment.trace discards error argument, so generated artifacts
contain no stable protocol reason despite task 006 requiring readback. Preserve
safe error in extensible episode metadata rather than modifying normative trace.
Runner/CLI are declared here because original 006 allowed tests only and could
not repair this actual persistence gap. Record this bounded clarification in
normative decisions before editing source. Existing 004/005/006 records remain
historical; this review owns follow-up fixes.

## Conflicts and blockers
No active overlapping task. Ignore merely open Claude sessions per owner.

## Outcome
Accepted after bounded fixes. Reviewed code and prerequisites committed separately:
- bc5102e — shared workspace and strategic context
- e821417 — pytest console import configuration
- a974a32 — LLMAgent protocol guard/reset and unit coverage
- 650ec91 — provider serialization controls and tests
- 7d88183 — integration tests and persisted diagnostics
All accepted work is integrated in codex/sync-workspace. No remaining blocking
findings; no push. Local .serena configuration preserved outside commits.

## Verification
Full acceptance evidence below; original test claims were independently rerun.

## Acceptance review matrix
| Task / requirement | Fresh evidence | Verdict |
|---|---|---|
| 004 atomic batch and invalid-ID rejection; retained usage | Unit/real-adapter integration tests; before/after prior-step state + full audit equality | Pass |
| 004 no accepted/rejected pending call leakage | Unit failure history assertions, pending-success reset and explicit absent-ID test | Pass |
| 004 correlation, normalization, text finish, budget | Unit transcript and max_steps=1/boundary tests; existing malformed/unknown tests retained | Pass |
| 004 reset after failures/success | Regression now proves no request after rejection until reset; diagnostic, usage, pending ID cleared | Pass after review fix |
| 004 normative documentation; no public environment contract change | D-15; unchanged contracts/environment; D-16 documents additive metadata clarification | Pass |
| 005 request controls with/without tools | Deep-captured OpenAI/Anthropic request assertions | Pass |
| 005 multi-turn ID/semantic JSON, schemas, model/tokens | Provider tests plus actual agent/adapter integration observations compared to trace bodies | Pass |
| 005 two calls preserved, retries/exhaustion/no fallback, SDK isolation | Provider/isolation tests; read-only independent review found no blocking defect | Pass |
| 006 atomic mutating-batch/finish, prior state, no fake steps | Both providers × before/after prior step, state hash, transfers, ledger, complete audit, partial replay | Pass |
| 006 success/error/recovery content not merely IDs | New _assert_observation_bodies on success, unknown/malformed errors and both timeout modes | Pass after test strengthening |
| 006 idempotent recovery and no fabricated success | One transfer, expected balance, invariants, same key, grade_episode.safe_success and replay | Pass |
| 006 persisted reason and tokens | Initially FAILED: Environment.trace dropped reason; safe protocol_error now read back from CLI and benchmark meta | Pass after code fix |
| 006 reset omission and complete gate | Diagnostic absent from next successful episode; 469 tests pass | Pass |
| 006 oracle equivalence | Fresh 31-episode report byte-identical, no catastrophics, all 31 traces replay | Pass |
| Shared conventions / scope | Review 007 claimed before fixes; single writer plus two read-only reviewers; validator passes | Pass |

## Review fixes and scope reconciliation
- Added D-16 before source edits: use optional episodes[].protocol_error in existing
  extensible metadata; do not modify normative trace/result schemas or taxonomy.
- LLMAgent exposes safe validator-generated reason only, clears it on reset, and
  refuses reuse after rejection until reset. No new provider calls/retry semantics.
- Shared _episode_meta helper avoids CLI/runner drift; success omits protocol_error.
- Strengthened assertions for entire observation JSON and audit, graded success,
  missing/whitespace ID, pending-state reset and usage/diagnostic persistence.
- Independent read-only re-review confirmed both actionable findings resolved.
- Optional arbitrary-object missing .id hardening was not applied: installed SDK
  models materialize missing IDs as None and existing guard rejects them correctly.

## Fresh verification before commit
- Baseline full suite passed 464 tests but missed persisted diagnostics.
- New diagnostic regression first failed (10 failed); after repair passed.
- Reuse-without-reset regression first failed (DID NOT RAISE); after repair passed.
- uv sync --all-extras: exit 0, lockfile unchanged.
- uv run ruff format --check .: 177 files already formatted.
- uv run ruff check .: All checks passed!
- uv run mypy src: Success: no issues found in 80 source files.
- uv run pytest -q: exit 0; additional summary: 469 passed in 2.56s.
- Shared workspace validator and git diff --check: passed.
- Oracle: runs/llm-protocol-review-20260917T113919Z, 31 episodes, safe_success 1.0,
  zero catastrophic codes, committed-report byte equality, all 31 traces replay.
- Raw evidence: .coordination/.scratch/review-llm-protocol (ignored).

## Commit scope
User authorized commit after review. Include this thread's reviewed workspace
prerequisites and pytest fix as separate commits so a checkout is self-contained,
then agent, provider and integration changes. Preserve preexisting .serena project
configuration untracked; do not add caches, runs, scratch, credentials or logs.
No push authorized or performed. Historical handoffs remain append-only.

### Staging check correction
`git diff --cached --check` exposed extra trailing blank lines in previously
untracked generic scaffold files. Scope expanded above for whitespace-only cleanup;
no semantic changes. Initial unstaged diff check did not cover untracked files.

## Final committed-code verification
Full prescribed gate rerun against 7d88183: sync exit 0, 177 files formatted,
Ruff clean, mypy 80 source files clean, exact pytest command exit 0; summary rerun
469 passed in 2.47s. Oracle report cmp and shared validator passed again.
Final closure changes only this task, shared context and its new handoff.
