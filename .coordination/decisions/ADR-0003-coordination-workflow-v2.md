---
id: ADR-0003
title: Adopt the current configure-agent-workflow coordination core
status: accepted
decided_at: 2026-10-02T23:28:34Z
task_id: 20261002-001-update-coordination-workflow
supersedes:
superseded_by:
---

# Context
`.coordination/` and the harness adapters were scaffolded on 2026-09-17 by an
earlier version of the `configure-agent-workflow` skill. The skill has since
added per-scope direct/rigorous execution modes, rigorous procedures, worktree
and local-main integration rules, impact-based verification, and mode/verify
fields in the task and handoff templates.

# Decision
Reconcile this repository with the current scaffold by hand (the initializer
never overwrites existing files): replace the core `.coordination/README.md`,
add `.coordination/rigorous.md`, update the task/handoff templates,
`tasks/done/README.md`, the Cursor coordination rule, the marked coordination
sections of `AGENTS.md` and `CLAUDE.md`, and add `.worktrees/` to the marked
`.gitignore` section. Owner chose direct mode for this migration.

Project rules in `AGENTS.md` (tickets, hard rules, verification gate, commit
format, concise completeness), `docs/00-project-context.md` and existing
authorization gates are unchanged and remain mandatory in either mode.

# Consequences
Each new task or agreed block starts with a direct/rigorous recommendation and
the owner's choice, recorded as `mode` in the task. Legacy tasks without `mode`
(including backlog `20260929-003`) stay readable as-is; a mode is chosen when
they are claimed. Future skill updates do not propagate automatically.

# Alternatives considered
Re-running the initializer: it treats differing files as conflicts and does not
migrate. Keeping the old core: loses mode choice and rigorous procedures the
owner adopted in the skill.
