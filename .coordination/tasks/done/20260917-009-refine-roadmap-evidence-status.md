---
id: 20260917-009-refine-roadmap-evidence-status
title: Separate capability delivery from research evidence
status: done
harness: codex
owner: codex/roadmap-evidence-status
created_at: 2026-09-17T18:05:37Z
updated_at: 2026-09-17T18:07:27Z
claimed_at: 2026-09-17T18:05:37Z
scope: Refine roadmap status semantics and define the next live-evidence gate
expected_files: ["docs/11-roadmap.md", "docs/milestones/M1-baseline-agents.md", "docs/milestones/M2-failure-analysis.md", "docs/milestones/M3-synthetic.md", "docs/milestones/M4-rewards.md", "docs/milestones/M5-optimization.md", "docs/milestones/M6-report.md", ".coordination/context/project.md", ".coordination/tasks/in-progress/20260917-009-refine-roadmap-evidence-status.md", ".coordination/tasks/done/20260917-009-refine-roadmap-evidence-status.md"]
depends_on: []
---

# Objective

Preserve the M0-M6 capability roadmap while making scientific evidence status
explicit, and define the first bounded live-model research gate without
pretending later hypotheses can be fixed before observing real traces.

## Acceptance criteria

- The roadmap defines `implemented`, `offline validated`, `live measured`, and
  `scientifically supported` without treating them as interchangeable.
- The roadmap truthfully summarizes current evidence for M0-M6.
- The next live-model gate has a question, protocol, metrics, artifacts, exit
  criterion, authorization boundary, and result-dependent branching rules.
- M1-M6 milestone checklists explicitly mean artifact/ticket closure rather
  than proof of live measurement or scientific support.
- Documentation checks pass and no unrelated working-tree changes are modified.

## Current state

Completed after confirming no backlog or in-progress task owned the roadmap
files. Existing communication-policy changes and local tool directories were
unrelated and remained untouched.

## Conflicts and blockers

None.

## Outcome

Added a cumulative four-level evidence model and a truthful M0-M6 snapshot to
the canonical roadmap. Defined R1 as the next reviewed live-model baseline,
including its question, authorization boundary, staged protocol, metrics,
artifacts, exit criterion, and result-dependent branching. Added status notes
to M1-M6 so checked implementation tickets cannot be mistaken for live
measurement or scientific support. Synchronized the stable project context.

## Verification

- `git diff --check` — passed.
- `uv sync --all-extras` — passed.
- Canonical `uv run ruff format --check .` and `uv run ruff check .` — blocked
  only by pre-existing untracked `.ua/.trash-1789666381/tmp/ua-arch-analyze.py`;
  the unrelated file was not modified.
- Tracked Python files: `ruff format --check` — 133 files already formatted;
  `ruff check` — passed.
- `uv run mypy src` — passed, 80 source files.
- `uv run pytest -q` — passed, complete suite.
