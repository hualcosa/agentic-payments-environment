# Approved plan: pytest import path

Task: `20260917-002-pytest-import-path`. Owner approved implementation on 2026-09-17.
Open Claude sessions are explicitly not a blocker; leave them untouched. No commits or pushes authorized.

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
