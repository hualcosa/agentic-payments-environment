---
id: 20260917-008-concise-communication
title: Align concise evidence-rich communication across harnesses
status: done
harness: codex
owner: codex/concise-communication
created_at: 2026-09-17T17:17:18Z
updated_at: 2026-09-17T17:18:09Z
claimed_at: 2026-09-17T17:17:18Z
scope: Add one canonical concise-completeness policy and thin Claude/Cursor adapters
expected_files: ["AGENTS.md", "CLAUDE.md", ".cursor/rules/project-context.mdc", ".coordination/tasks/in-progress/20260917-008-concise-communication.md", ".coordination/tasks/done/20260917-008-concise-communication.md"]
depends_on: []
---

# Objective

Balance precision, evidence and verification with maximally compressed,
high-signal communication across Codex, Claude Code and Cursor.

## Acceptance criteria

- `AGENTS.md` defines the canonical communication policy.
- Claude Code and Cursor explicitly inherit the same policy without duplicating it.
- The policy preserves conclusions, material evidence, risks and verification while removing repetition and process narration.

## Current state

Completed with no overlapping task.

## Conflicts and blockers

None.

## Outcome

Added a canonical concise-completeness policy to `AGENTS.md`. Claude Code and
Cursor explicitly inherit it through their thin project adapters, avoiding
three independently evolving copies.

## Verification

- `git diff --check` — passed.
- Inspected all three rendered policy locations — canonical text and adapters present.
