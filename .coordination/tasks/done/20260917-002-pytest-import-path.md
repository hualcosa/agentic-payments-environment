---
id: 20260917-002-pytest-import-path
title: Make the required pytest console entrypoint import local test helpers
status: done
harness: codex
owner: codex/pytest-import-path
created_at: 2026-09-17T09:42:16Z
updated_at: 2026-09-17T09:56:32Z
claimed_at: 2026-09-17T09:55:20Z
scope: Diagnose and minimally repair test import-path configuration; no runtime behavior changes
expected_files: ["pyproject.toml", ".coordination/tasks/{backlog,in-progress,done}/20260917-002-pytest-import-path.md"]
depends_on: []
---

# Objective
Unblock validation of 20260917-001-sync-workspace without weakening tests.

## Acceptance criteria
- Exact `uv run pytest -q` succeeds without shell PYTHONPATH overrides.
- Module and console invocations collect the same tests (current module run: 427).
- All four AGENTS.md verification gates pass; no new dependency or runtime change.

## Current state
Completed on base dae3b95, Python 3.11.16; diagnostics below describe the pre-fix state.
`tests/conftest.py:15` imports `tests.test_world`; tests is a namespace directory.
Console invocation exits 4 (No module named tests); module invocation passes.
Revalidated the proposed minimal pytest pythonpath configuration using a temporary
CLI override, with no tracked config or dependency changes.
Declare any alternate file scope before editing; follow docs/12-decisions.md for
spec conflicts. Rerun the exact commands, do not substitute the diagnostic command.

## Conflicts and blockers
No runtime ownership overlap. Parent task owns coordination, not pyproject.toml.

## Outcome
Completed: added only `pythonpath = ["."]` in pytest configuration. Exact official
entrypoint now passes with no overrides. No tests, runtime code, dependencies,
lockfile or CI changes. No commits/pushes. Parent owner may resume closeout.

## Verification
Historical diagnosis from parent task: module run 427 passed; console run exit 4.

## Execution plan — approved

### Goal and evidence
This is measurement-infrastructure repair, not an active agent experiment.
Question: can the prescribed console entrypoint collect and execute the exact
same suite as the successful module entrypoint? Metrics: exit code 0 and identical
427 test node IDs at current base. Evidence: gate logs and node-ID comparison.
Smallest useful change: one pytest configuration entry; no runtime/API change.

### Ownership and prerequisites
1. Read AGENTS.md, shared protocol/context, parent task and latest handoff; verify
   branch codex/sync-workspace and base dae3b95, inspect current diff and active claims.
2. After implementation approval, parent owner explicitly excludes this task's
   lifecycle file from its broad coordination scope and pauses parent writes.
   Claim/move this task to in-progress, owner codex/pytest-import-path, UTC timestamps.
   No other writer may own pyproject.toml. If concurrent harnesses require a committed
   claim, obtain explicit commit authorization rather than silently committing.
3. Publish this approved sequence to plans/ through the parent coordination owner
   before child claim; keep proposed content here until approval. Add that plan's
   concrete filename to the parent's expected files. Do not start a second fix ticket.

### Implementation
Add `pythonpath = ["."]` under `[tool.pytest.ini_options]` in pyproject.toml.
Retain testpaths, addopts, all existing test code and CI commands. No tests/__init__.py,
conftest sys.path hacks, dependencies, lockfile or runtime changes are needed.
If the verified one-line change fails on the execution state, stop and document
new evidence rather than broadening scope or weakening tests.

### Verification and acceptance
- Before editing, reproduce `uv run pytest -q` exit 4 on the unchanged base.
- After editing run `uv sync --all-extras`, `uv run ruff format --check .`,
  `uv run ruff check .`, `uv run mypy src`, and **`uv run pytest -q` without overrides**.
- Compare node IDs from `uv run pytest --collect-only -o addopts='' -q` and
  `uv run python -m pytest --collect-only -o addopts='' -q`; require identical sets
  and 427 cases on this base. Do not compare elapsed-time footer text.
- Rerun offline oracle v0 seed 0 in a fresh run directory; require 31 episodes,
  safe success 1.0, zero catastrophic failures and report equality with committed
  reports/v0/oracle.md. Do not overwrite prior runs.
- Verify only the declared pytest configuration and coordination metadata changed;
  preserve all preexisting owner changes. `git diff --check` must pass.
- Record exact commands, revision, environment and result tails in this task;
  no remote CI success claim unless separately executed and observed.

### Closeout (serial ownership transfer)
Complete/move this child task to done only after its checks pass. Parent owner then
resumes, updates context, reruns shared-workspace validation and closes the parent
when all original acceptance criteria are met. Create a new timestamped handoff;
do not rewrite historical handoffs. If anything fails, leave the affected task
in-progress with the exact blocker. Leave all changes uncommitted unless authorized.

### Defaults and exclusions
Single writer, current checkout, current dependencies; no paid/model runs,
experiments, new APIs, provisioning, publication, commit or push. Experimental
planning is a subsequent owner decision, not bundled into this repair.

## Fresh planning verification
- Exact required command still fails: `ModuleNotFoundError: No module named 'tests'`.
- Temporary `uv run pytest -q -o pythonpath=.` exits 0 (configuration not written).
- Console-with-override and module invocation collect 427 identical explicit node IDs.
- Runtime source, tests, pyproject.toml and uv.lock remain unmodified.
- Diagnostic logs: `.coordination/.scratch/sync-workspace/replan-*.log` (local only).

Approved plan: `../../plans/2026-09-17-pytest-import-path.md`.
User explicitly instructed ignoring open Claude sessions and focusing on this fix.

## Final verification
- Baseline exact `uv run pytest -q`: exit 4, missing tests module reproduced before edit.
- `uv sync --all-extras`: exit 0, lockfile unchanged.
- `uv run ruff format --check .`: `166 files already formatted`.
- `uv run ruff check .`: `All checks passed!`.
- `uv run mypy src`: `Success: no issues found in 80 source files`.
- Exact `uv run pytest -q`: exit 0, all progress rows through [100%].
- Additional summary invocation `uv run pytest -o addopts='' -q`: `427 passed in 0.84s`.
- Console and module collect-only commands (without pythonpath overrides):
  identical 427 explicit node IDs.
- Offline oracle v0 seed 0, new output runs/pytest-fix-20260917: 31 episodes,
  safe_success_rate 1.0; report byte-identical to committed oracle report,
  including zero catastrophic failures.
- `git diff --exit-code -- src tests uv.lock` and `git diff --check`: clean.
- Raw local logs: .coordination/.scratch/sync-workspace/fix-*.log.
- Local results only; remote CI not run.
