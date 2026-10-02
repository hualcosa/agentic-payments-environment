---
id: 20261002-001-update-coordination-workflow
title: Update coordination package and harness adapters to current workflow
status: done
mode: direct
harness: claude-code
owner: claude-code/housekeeping
created_at: 2026-10-02T23:28:34Z
updated_at: 2026-10-02T23:28:34Z
claimed_at: 2026-10-02T23:28:34Z
scope: Reconcile .coordination/ core, templates and harness adapters with the current configure-agent-workflow scaffold.
expected_files:
  - .coordination/README.md
  - .coordination/rigorous.md
  - .coordination/templates/task.md
  - .coordination/templates/handoff.md
  - .coordination/tasks/done/README.md
  - .coordination/decisions/ADR-0003-coordination-workflow-v2.md
  - .coordination/context/project.md
  - .cursor/rules/coordination.mdc
  - AGENTS.md
  - CLAUDE.md
  - .gitignore
depends_on: []
acceptance_tests: []
---

# Objective

Bring the repository's coordination protocol and Codex/Claude Code/Cursor
adapters up to the current skill version without touching project-specific
rules. Owner chose direct mode (docs-only, low risk).

## Acceptance criteria

- Workflow files match the current scaffold; only marked sections of
  `AGENTS.md`, `CLAUDE.md` and `.gitignore` change.
- Skill validator passes; relative links in the new core resolve.

## Current state

Done, uncommitted (no commit authorization yet). Decision: ADR-0003.

## Conflicts and blockers

None. No in-progress tasks existed.

## Outcome

Core README replaced, `rigorous.md` added, task/handoff templates and done
README updated, Cursor rule and AGENTS/CLAUDE coordination sections shortened
to the canonical pointer, `.worktrees/` ignored, project context updated.
Legacy tasks untouched. Trailing-blank-line-only differences in other scaffold
READMEs were left as-is.

## Verification

- `python3 <skill>/scripts/validate.py --target .` → "Shared agent workspace is
  valid", exit 0.
- Relative links in `README.md`, `rigorous.md`, `templates/task.md`: none broken.
- `git diff` of `AGENTS.md`, `CLAUDE.md`, `.gitignore`: only marked
  coordination sections changed.
- Docs-only: no application tests run (not impacted).
