# Shared coordination protocol

Repository coordination is the shared source of truth across Codex, Claude Code
and Cursor; harness-local memory supplements it. Keep `.coordination/` versionable
except ignored `.scratch/`. Never store secrets, credentials, personal data or
machine-specific session data here. This is policy, not an enforcement engine.

## Startup protocol

Before editing, read this core, current `context/project.md`, active tasks and
relevant decisions/handoffs. Check ownership and Git state; do not overwrite others.
Before each task/agreed block, **briefly recommend direct or rigorous, explain why,
and ask the user to choose**. Without an applicable choice, do not implement.
The choice lasts for that agreed scope; do not ask again for microedits or fixes.
Material changes in scope, risk or concurrency require a new recommendation and
choice before expansion. Existing requirements, verification mandates,
authorizations and gates remain mandatory in either mode.

## Execution modes

High risk—auth, money/financial limits, data, shared contracts or uncertain
impact—calls for an explicit warning and a **rigorous recommendation**, not a
numeric score or mandatory risk agent. The user may still choose direct after
that warning; honor the choice without silently imposing rigorous ceremony.

- **Direct:** executor implements, writes/updates pertinent tests, verifies and
  records actual results/limitations. Independent review is not mandatory. Use
  native harness resources when requested. Do not load rigorous procedures or
  create an artificial task/worktree for a simple safe change.
- **Rigorous:** only after this choice, read [rigorous.md](rigorous.md). Independent
  protected acceptance authorship and an accepted baseline precede implementation;
  independent final-version review follows it. Docs-only uses observable checks
  and review, not artificial application tests.

## Ownership and records

One owner per focused task. Formal tasks are needed for complex, concurrent or
rigorous work; simple direct work can use a lightweight repo-local record when
needed for continuity. Use `templates/task.md`, record mode, scope, expected files,
owner/harness, ISO 8601 UTC timestamps and dependencies; move backlog → in-progress
→ done. IDs are `YYYYMMDD-NNN-short-name`. Legacy tasks without mode remain readable
historical records; never retroactively reinterpret or rewrite their approvals.
Check the ready set, dependencies, gates and ownership before dispatch; parallelize
only independent ready work with non-overlapping ownership. An acceptance baseline
is a predecessor of rigorous implementation, never concurrent with it.

When a PR exists, concentrate what/why/verification there; link rather than repeat
it in repo records. Without a PR, keep enough repo-local state/results/limitations
for continuity. Maintain current context and relevant decisions; record a handoff
when transferring incomplete work. Do not duplicate narratives. Changelog only
for relevant changes, not every PR; no new changelog automation.

## Worktrees and integration

An existing checkout, including local main, is allowed for a single safe writer.
Concurrent writers require separate worktrees/environments; read-only review may
share a checkout. First verify repo root, base revision, branch, current work and
ownership. Never assume local main is current or stash/reset/discard others' work.

Accepted changes in auxiliary branches must integrate into **local main** before
completion, preferably fast-forward, then verify the combined result and record
revision. Inspect both checkouts; stop and ask if main is dirty, diverged, owned by
another task or conflicts. Do not invent commit permission to enable integration.
If no Git baseline exists, isolated snapshot/hash review is bootstrap evidence,
not exact-HEAD approval. Preserve useful work before removing task worktrees.
No automatic commit, remote, push, PR or other publication; explicit authorization
is required under the project's rules.

## Verification

Tests are required where pertinent in both modes; green tests alone do not prove
readiness. During development run focused functionality/regressions, expand by
actual impact (including transitive consumers, contracts, auth, persistence,
dependencies/config). At integration run mandatory acceptance/verify commands,
changed/impacted tests and project safety core. At milestones/pre-demo run the full
applicable suite plus real system/artifact QA. Existing broader mandates stay.
Uncertain impact, stale mapping or empty selection needs broader checks, not an
unsupported omission. Isolate state for parallel tests. Record actual commands,
results, selection reasons and limitations; never narrow required checks to pass.
Docs-only checks links, output/rendering and affected tooling, not fake app tests.

## Conflict policy

Active tasks must not overlap ownership. Later claimants pause overlapping work,
record the conflict, switch to independent work or ask for human coordination.
Recheck before expanding/touching undeclared files. Never remove locks forcibly or
overwrite another writer. Cross-ownership conflicts/destructive actions require a
human decision; preserve both agents' information.

## Handoff protocol

For incomplete transfer, use `templates/handoff.md`: state, mode/scope, changed
files, verification, blockers and exact next action. Use UTC filename
`YYYYMMDD-HHMM-<task-id>-<from>-to-<to>.md`. Keep history; the next owner incorporates
new state into the active record.

## Completion protocol

Record outcomes, verification and follow-ups in the appropriate existing record;
mark formal tasks done and move to `done/`. Update current context for stable
changes and capture relevant decisions. Explicitly distinguish unverified work,
bootstrap review and runtime readiness; bookkeeping cannot approve unreviewed
product changes. Do not leave accepted work stranded in auxiliary branches.
