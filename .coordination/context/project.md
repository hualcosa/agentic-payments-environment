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
- Local integration branch: `codex/sync-workspace`; reviewed implementation is committed
  through `7d88183` locally. No push has been performed.
- The revision includes environment, benchmark v0/v1, graders, adapters,
  generators, reward/export tooling and reports. Milestone labels describe
  implemented infrastructure, not proof of completed live experiments.
- Live-model benchmark/intervention results remain **not yet measured** in
  the checked-in reports. Git does not recover ignored Cloud-only run files.
- Completed tasks `20260917-001` through `20260917-007` are recorded in
  `tasks/done/`. The latest slice implemented and verified the offline LLM
  single-tool-turn protocol in the agent, both provider adapters and integration.
- No active research experiment is assumed. Live-model behavior remains unmeasured.
- `docs/11-roadmap.md` now separates implemented, offline-validated,
  live-measured and scientifically-supported evidence. The next defined gate is
  R1, a reviewed live-model baseline; defining it does not authorize paid calls.

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

## M7 spec conformance (2026-09-21)
Task `20260918-001-port-m7-conformance` ported M7 (T7.01–T7.21) from
`composer25` onto main, one commit per ticket, with derived artifacts
regenerated from main's code. Adds strict contracts (schema versions, strict
centavos, UTC-only datetimes, fixture structure, grading consistency), exact
INV-02/INV-04, fault ordering, v1.1 freeze (200 held-out / 802 train from 1002
validated tasks), CLI for v0/v1/v1.1, LLM turn sidecars, preference/SFT
datasets, REQ traceability and `apenv reproduce --check`. Audit: gate clean on
Python 3.11/3.12 (1282 tests); reproducer exit 0. Offline evidence only; live
models remain not yet measured. Next gate is still R1 (live baseline), which
needs explicit authorization.

## Latest validation (2026-09-17)
Acceptance review 007 verified tasks 004–006 and fixed two gaps: safe protocol
reasons now persist in existing episode metadata, and a rejected agent requires
reset before another model request. Integration compares complete observation
bodies and audit state, not only correlation IDs. Public contracts are unchanged.

Full gate rerun on committed code `7d88183`: uv sync, Ruff format/lint, mypy
(80 source files), and 469 pytest tests passed. Shared validator and diff checks
passed. Oracle evidence at `runs/llm-protocol-review-20260917T113919Z` contains
31 episodes, safe success 1.0, zero catastrophics; report byte-identical to
`reports/v0/oracle.md`, with all 31 traces replayed during review. This is offline
scripted evidence only, not a live-model experiment. Remote CI has not run.

Local commits: `bc5102e` workspace, `e821417` pytest imports, `a974a32` agent,
`650ec91` adapters, `7d88183` integration/diagnostics. Review closure is recorded
separately. Preexisting `.serena/` configuration remains untracked and untouched.
No paid calls, provisioning, publication or push performed. No implementation
follow-up remains for this protocol slice; further experiments require approval.
