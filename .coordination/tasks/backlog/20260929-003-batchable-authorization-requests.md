---
id: 20260929-003-batchable-authorization-requests
title: Decide whether authorization requests may join read-only batches
status: backlog
harness: unassigned
owner: unassigned
created_at: 2026-09-29T18:20:12Z
updated_at: 2026-09-29T18:20:12Z
claimed_at:
scope: Owner decision on D-27 scope for request_consent / request_step_up_auth in batches.
expected_files: []
depends_on: [20260929-001-read-only-tool-batches]
---

# Objective

In the prompt v1.1 seed-0 run, 5 episodes (fr-006, rt-001, rt-003, rt-004,
rt-006) ended with `LLM_PROTOCOL_MULTIPLE_TOOL_CALLS` because the model
batched `check_transfer_policy` with `request_consent` or
`request_step_up_auth` (or two consent requests). These tools create
authorization records but move no money. Decide whether D-27 should treat them
as batchable, keeping money-moving and irreversible tools
(`create_transfer`, `reverse_transfer`, `add_beneficiary`, `finish`)
exclusive. Measure the rejection rate across seeds 1–2 before deciding.

## Acceptance criteria

- Decision recorded (D-xx); if changed, protocol tests updated and R1 reruns
  use one fixed protocol version.

## Current state

Not started. Evidence: reports/r1/journal.md Entry 3.

## Conflicts and blockers

Changing D-27 mid-R1 invalidates comparison with earlier R1 runs.

## Outcome

## Verification
