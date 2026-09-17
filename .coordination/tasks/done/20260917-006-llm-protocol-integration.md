---
id: 20260917-006-llm-protocol-integration
title: Verify integrated LLM protocol through environment and artifacts
status: done
harness: codex
owner: codex/llm-protocol-integration
created_at: 2026-09-17T11:19:17Z
updated_at: 2026-09-17T11:32:13Z
claimed_at: 2026-09-17T11:28:27Z
scope: End-to-end offline regressions and final integration evidence; no source fixes
expected_files: ["tests/test_llm_protocol_integration.py", ".coordination/context/project.md", ".coordination/handoffs/*-20260917-006-llm-protocol-integration-cursor-to-owner.md", ".coordination/tasks/backlog/20260917-006-llm-protocol-integration.md", ".coordination/tasks/in-progress/20260917-006-llm-protocol-integration.md", ".coordination/tasks/done/20260917-006-llm-protocol-integration.md"]
depends_on: ["20260917-004-llm-agent-protocol", "20260917-005-provider-tool-protocol"]
---

# Objective
Verify both completed implementations together in the final target checkout; prove
rejection is atomic, observations remain correlated and episode artifacts/replay
remain trustworthy. Suggested owner: cursor/llm-protocol-integration.

## Spec references and relevant code
M1 T1.01–T1.03; docs/03-contracts.md §9; docs/06-environment-runtime.md runner/replay
(REQ-ENV-17/18); docs/10-testing-strategy.md; ADR-0001 and the approved plan.
Read LLMAgent, provider adapters, benchmark/runner.py, replay.py, CLI, environment
and tests/conftest.py. Reuse fixtures; define only test-local recording SDK doubles.

## Dependencies and ownership
Both tasks 004/005 must be integrated in codex/sync-workspace (or an explicitly
owner-selected replacement) and verified, not merely done in auxiliary worktrees.
Check actual diff and source. No source edits are owned here. If a regression
requires a fix, record evidence and hand it back to the corresponding task owner;
reconcile ownership/reopen before changes. Never silently expand this ticket.

## Tests to implement
- Parametrize over concrete OpenAI-compatible and Anthropic adapters with stubbed
  SDKs. Feed real LLMAgent and environment observations through complete conversations.
- At initial step and after a valid step, return a batch containing a mutating
  action and another call, including a finish+transfer variant. Assert AGENT_ERROR,
  stable protocol error, zero actions from the rejected turn, unchanged state hash
  relative to pre-turn state and no extra ledger/audit effects. Prior steps remain.
- Invalid single-call IDs likewise fail before action; returned usage is retained
  in existing usage metadata even though no environment Step was produced.
- One valid call per turn: exercise a successful payment flow, unknown-tool error
  then correction, and malformed required arguments followed by correction. Assert
  next request carries exactly the matching observation and original ID.
- Timeout-after-execute: use existing fault fixture, script status lookup and reuse
  the same idempotency key if retrying. Assert one net transfer, valid invariants
  and no fabricated success. Test before-execute fault separately if using retry.
- Text-only and local forced-finish paths make no unnecessary provider request.
- Reuse/reset agent across episodes without leaking previous messages or usage.
- Replay successful and recovery traces; assert matches. Protocol-rejection trace
  contains only executed actions and an explicit AGENT_ERROR, no fake rejected step.
- Run one offline CLI/runner artifact test with monkeypatched SDK: persist trace,
  result and meta in tmp_path; read back the protocol error and reported token usage.
  Do not add a new artifact schema or require raw provider transcript persistence.

## Acceptance criteria
- All new offline end-to-end tests and full integrated gate pass.
- Oracle v0 seed 0 in a fresh ignored run directory: 31 episodes, safe success 1.0,
  zero catastrophics, report byte-identical to reports/v0/oracle.md.
- Every accepted call visible in a subsequent model request has exactly one result;
  rejected batches never partially execute. No hidden task data added to inputs.
- Existing source/test/lockfile changes are explained by 004/005; no unrelated edits.
- Shared context records completion and evidence, not live-provider validation.
- Create a NEW timestamped handoff using the canonical template; preserve history.

## Verification commands
`uv run pytest -q tests/test_llm_protocol_integration.py`
Then the full gate below and:
```bash
# Choose a new timestamped output; do not overwrite an earlier run.
uv run apenv bench --benchmark v0 --agent oracle --seeds 0 --out runs/<new-run-id>
cmp reports/v0/oracle.md runs/<new-run-id>/report.md
python3 /Users/hualcosa/.agents/skills/initialize-shared-agent-workspace/scripts/validate.py --target .
```
Use actual output paths in the task evidence. Completion report includes revision,
commands/exit codes/tails, new regression cases, artifact location and explicit
"offline only; no live model experiment" limitation. Do not commit/push automatically.

## Startup and constraints
Read AGENTS.md, .coordination/README.md, .coordination/context/project.md, the
approved .coordination/plans/2026-09-17-llm-tool-protocol.md and ADR-0001 before edits.
Read the task's spec references, actual Git state, in-progress claims and latest
handoff. Preserve uncommitted startup files and pytest pythonpath configuration.
Move this file to in-progress, set harness: cursor, a human-readable owner, and
UTC claimed_at/updated_at before editing. Intended executor: user-controlled Cursor
with Grok 4.6; no task is preclaimed merely because that executor is intended.
One task per owner; no edits outside expected_files without documenting scope and
resolving overlap first. No commits/pushes, real API calls, keys, provisioning,
new dependencies, test weakening or unrelated refactors. Existing open Claude
sessions alone are not a blocker. Use repository state, not prior chat, as truth.

## Full verification gate
Run from repository root and record exit codes and output tails:
```bash
uv sync --all-extras
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest -q
git diff --check
```
The historical baseline had 427 tests; new tests should increase coverage, not
hold an artificial count. Do not claim tests pass without running them. Mark done
only after useful changes are in the final target checkout and verification is
recorded; otherwise leave in-progress with blocker and exact next action.

## Current state
Completed in the final target checkout after tasks 004 and 005. Twenty HTTP-free
integration cases exercise both concrete adapters through LLMAgent, runner,
environment, replay and CLI artifact paths.

## Conflicts and blockers
None known at authoring. Recheck active ownership before editing.

## Outcome
Added end-to-end regressions proving atomic rejection, exact result correlation,
successful payment, unknown/malformed recovery, before/after timeout recovery,
reset isolation, replay integrity, hidden-data exclusion and persisted usage metadata.
Updated shared project context with completion evidence.

## Verification
- `uv run pytest -q tests/test_llm_protocol_integration.py` — passed (20 tests).
- `uv sync --all-extras` — passed.
- `uv run ruff format --check .` — passed (175 files).
- `uv run ruff check .` — passed.
- `uv run mypy src` — passed (80 source files).
- `uv run pytest -q` — passed (464 tests).
- `git diff --check` — passed.
- `uv run apenv bench --benchmark v0 --agent oracle --seeds 0 --out runs/llm-protocol-integration-20260917T113140Z` — 31 episodes, safe success 1.0, catastrophic rate 0.0.
- `cmp reports/v0/oracle.md runs/llm-protocol-integration-20260917T113140Z/report.md` — byte-identical.
- Shared workspace validator — passed.
- Offline only; no live provider/model experiment was run.
