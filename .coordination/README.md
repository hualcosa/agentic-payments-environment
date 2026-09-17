# Shared coordination protocol

This directory is the canonical communication layer for Codex, Claude Code,
and Cursor. Repository files—not harness-local memory or chat history—are the
shared source of truth.

## Directory map

- `context/project.md`: stable project facts, constraints, and current state.
- `decisions/`: durable architectural and product decisions.
- `plans/`: approved implementation plans.
- `tasks/backlog/`: defined but unclaimed work.
- `tasks/in-progress/`: claimed work and its current owner.
- `tasks/done/`: completed work with its outcome and verification.
- `handoffs/`: point-in-time notes for continuing work in another session or
  harness.
- `templates/`: canonical formats for new coordination records.
- `.scratch/`: optional local-only notes; ignored by Git.

## Startup protocol

Before editing project files, every agent must:

1. Read this file and `context/project.md`.
2. Inspect all files in `tasks/in-progress/` for scope or file overlap.
3. Read any handoff for the task it will continue.
4. Claim an existing backlog task or create a task from `templates/task.md`.
5. Move the task file to `tasks/in-progress/`, set `status: in-progress`, and
   record the harness, owner label, UTC claim time, scope, and expected files.
6. Commit the claim before substantial project edits when multiple harnesses
   may be working concurrently.

Do not use opaque or machine-specific session identifiers as owner labels. A
short human-readable label such as `codex/api-schema` is sufficient.

## Task identifiers and filenames

Use sortable task IDs in the form `YYYYMMDD-NNN-short-name`, for example
`20260909-001-bootstrap-api`. The task filename is `<task-id>.md` and stays the
same while it moves between lifecycle directories.

All timestamps use ISO 8601 in UTC, such as `2026-09-09T15:30:00Z`.

## Working protocol

- Keep each task focused enough for one owner at a time.
- Update the task record when scope, expected files, blockers, or the next
  action changes materially.
- Check active tasks again before expanding scope or touching an undeclared
  file.
- Record durable choices in `decisions/`; do not bury them only in chat,
  commits, or task notes.
- Put approved multi-step implementation designs in `plans/`.
- Never place credentials, tokens, personal data, or secrets in coordination
  records.

## Conflict policy

Two active tasks must not knowingly own the same scope or files. If overlap is
found, the later claimant must pause that portion of work, record the conflict
and exact overlap in its task, and either switch to unrelated work or request
human coordination. Never resolve an ownership conflict by silently
overwriting another agent's changes.

If simultaneous Git changes conflict, preserve both agents' information while
resolving the text conflict, then reconcile task ownership explicitly before
continuing implementation.

## Handoff protocol

Create a handoff from `templates/handoff.md` when work stops unfinished, moves
to another harness, or needs context that is not obvious from the diff. A
handoff records the task, current state, changed files, verification, blockers,
and exact next action.

Name handoffs `YYYYMMDD-HHMM-<task-id>-<from>-to-<to>.md`, using UTC. The next
owner should incorporate the handoff into the task and keep the handoff as a
historical record.

## Completion protocol

Before completing a task:

1. Run verification appropriate to the change and record the commands and
   results.
2. Summarize the outcome and any follow-up work in the task file.
3. Set `status: done`, update the UTC timestamp, and move the file to
   `tasks/done/`.
4. Update `context/project.md` when the project's stable state changed.
5. Create separate backlog tasks for deferred work; do not hide it in prose.
