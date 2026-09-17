# Project context: agentic-payments-environment

## Purpose and authority

A deterministic payments research instrument for measuring, explaining and
modifying agent behavior; not a banking product or generic framework.
Strategic authority: `docs/00-project-context.md`. Technical authority:
`docs/00-index.md`, its specifications and `docs/12-decisions.md`.
Do not duplicate evolving strategy here or infer measured results from feature coverage.

## Current state

- On 2026-09-17 local main was fast-forwarded from e27f756 to remote main
  dae3b9598570d80d0e8a1f86aa8cb962e25b2d55 (50 commits); fetched remote matched.
- Local integration branch: `codex/sync-workspace`; workspace changes are
  uncommitted and not pushed. Files on disk are not yet shared through Git.
- The revision includes environment, benchmark v0/v1, graders, adapters,
  generators, reward/export tooling and reports. Milestone labels describe
  implemented infrastructure, not proof of completed live experiments.
- Live-model benchmark/intervention results remain **not yet measured** in
  the checked-in reports. Git does not recover ignored Cloud-only run files.
- Completed tasks `20260917-001` through `20260917-006` are recorded in
  `tasks/done/`. The latest slice implemented and verified the offline LLM
  single-tool-turn protocol in the agent, both provider adapters and integration.
- No active research experiment is assumed. Live-model behavior remains unmeasured.

## Shared workflow and constraints

- Follow `.coordination/README.md`; one owner per scope, UTC task timestamps,
  task-linked plans and explicit handoffs. Recheck claims before writing.
- Preserve approved strategic context across Codex, Claude Code and Cursor.
- Engram is supplementary persistent memory; repository records are shared truth.
- CodeGraph is a regenerable local index; `.codegraph/` stays ignored.
- Keep secrets, local caches and machine-specific session data out of shared records.
- No commits, pushes, paid runs, provisioning or publication without explicit
  authorization. If concurrent writers require a committed claim, pause and ask.
- New task scopes govern implementation files; the LLM protocol slice does not
  change environment contracts, dependencies or experiments.

## Latest validation (2026-09-17)
The offline LLM tool-protocol slice is complete. `LLMAgent` rejects multi-call
turns and invalid IDs atomically, both provider adapters request serial tool use,
and 20 integration cases cover correlation, protocol errors, successful payment,
unknown/malformed correction, timeout recovery, reset isolation, replay and CLI
artifacts. Full verification passed: Ruff format/lint, mypy on 80 source files,
464 pytest tests and `git diff --check`. Shared workspace validation also passed.
Oracle v0 seed 0 produced 31 episodes, safe success 1.0 and zero catastrophics at
`runs/llm-protocol-integration-20260917T113140Z`; its report is byte-identical to
`reports/v0/oracle.md`. This is offline scripted evidence only, not a live-model
experiment. All changes remain uncommitted and unpushed on `codex/sync-workspace`;
remote CI has not run.
