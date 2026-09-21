---
id: 20260918-001-port-m7-conformance
title: Port M7 spec-conformance tickets onto main
status: done
harness: claude-code
owner: claude/m7-port
created_at: 2026-09-17T22:58:00Z
updated_at: 2026-09-21T12:00:00Z
claimed_at: 2026-09-17T22:58:00Z
scope: Port docs/milestones/M7-spec-conformance.md T7.01-T7.21 onto current main without inventing live-model results; land already-complete 008/009 docs; merge verified work into main
expected_files:
  - docs/milestones/M7-spec-conformance.md
  - docs/12-decisions.md
  - AGENTS.md
  - src/agentic_payments_env/**
  - tests/**
depends_on: []
---

# Objective

Close the empty coordination backlog by executing the remaining defined
milestone work: post-M6 spec conformance (M7) against current `main`, using
`composer25@7ab9285` as the completed reference implementation.

## Acceptance criteria

- Coordination backlog and in-progress remain free of other owners for this scope.
- Completed uncommitted tasks 008 and 009 are on `main`.
- Each M7 ticket's Done-when conditions hold on the integration branch, then
  on `main`.
- Full verification gate passes on the merged result.
- No paid live-model runs, pushes, or fabricated measurements.

## Current state

Claimed after finding `tasks/backlog/` empty. Independent 008/009 diffs are
already in the main working tree. M7 exists only on `composer25` /
`claude/agentic-payments-spec-cknl3v`. Tickets T7.01-T7.09 are sequential and
share contracts/runtime files; later tickets may be parallelized after those
land if file scopes do not overlap.

## Ownership transfer (2026-09-21)

Cursor's claim was abandoned: worktree `cursor/m7-conformance` stayed at
`b7e0708` with no commits, and the claim file was deleted uncommitted 19 s
after it was committed, without a handoff. The owner asked Claude Code to
implement M7; work continues on branch `claude/m7-port` (worktree `../ape-m7`).
Approach: cherry-pick `composer25` T7 commits one ticket at a time, resolving
against main's code, and regenerate derived artifacts (v1.1, datasets,
reports) from main's code rather than copying composer25 bytes.

## Conflicts and blockers

Do not merge `composer25` wholesale: it is a parallel M0-M6 history from
`e27f756`. Port T7 commits / behavior onto current main instead.

Composer 5 is not in the available sub-agent model list; execution uses
Composer 2.5 Fast (`composer-2.5-fast`).

## Outcome

All 21 M7 tickets ported onto `claude/m7-port`, one commit per ticket
(T7.07's two composer commits squashed; T7.20 split into plan + audit record).
Conflicts were resolved against main's code, preserving main's LLM
single-tool-turn protocol (D-15/D-16). Notable adaptations:

- Decisions renumbered: composer D-15..D-23 -> main D-17..D-25; main's Q-list
  kept, Q-06 promoted to D-17, Q-16/Q-17 marked resolved (T7.12/T7.14).
- Main's `aware_datetime_validator(*fields)` factory kept; now enforces UTC.
- T7.10 keeps main's long nickname injection wording as the first template.
- T7.13 turn log also records protocol-rejected turns (`protocol_error`,
  no parsed action) and coexists with `_episode_meta`.
- T7.17 anchors REQ-ENV-12 on `SimulatedUser`, the sole `task.hidden` holder.
- v1.1 freeze, difficulty report, reward spec and datasets regenerated from
  main's code (datasets/reward spec byte-identical to composer25; 68 v1.1
  adversarial files differ only by nickname wording). v0/v1 bytes unchanged.

Follow-ups (not done): gate now takes ~4–8 min because tests rebuild v1.1
datasets; `reproduce.py` module docstring cites REQ-ENV-14, which is loosely
related; some canonical helpers remain in `tests/test_contracts.py` as in
composer25. No live-model runs, pushes or paid calls.

## Verification

See `docs/milestones/M7-spec-conformance.md` "T7.20 audit record (main)":
full gate clean on Python 3.11.16 and 3.12.14 (mypy 83 files, 1282 tests);
`apenv reproduce --check` exit 0; static scans clean; `git diff --check` clean.
