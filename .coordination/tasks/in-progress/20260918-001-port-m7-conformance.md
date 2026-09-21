---
id: 20260918-001-port-m7-conformance
title: Port M7 spec-conformance tickets onto main
status: in-progress
harness: claude-code
owner: claude/m7-port
created_at: 2026-09-17T22:58:00Z
updated_at: 2026-09-21T00:00:00Z
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

## Verification
