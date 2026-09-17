# Approved plan: synchronize implementation and rebuild shared workspace

Task: `20260917-001-sync-workspace`. Approved by owner on 2026-09-17.

## Objective
Use published remote main as implementation base, regenerate generic coordination
and CodeGraph, preserve approved strategic context, then validate the offline baseline.

## Execution
1. Confirm ownership; preserve local modifications, untracked files and local runs
   in an external SHA-256-verified backup before updating Git.
2. Claim the task using canonical fields; fetch origin, fast-forward main only,
   and use `codex/sync-workspace` for local integration. Never reset hard.
3. Dry-run shared initialization with `--no-commit`; reconcile conflicting
   adapters deliberately without force. Regenerate templates, replace generic
   project placeholders with verified facts, keep the strategic context canonical.
4. Rebuild CodeGraph using `codegraph index`; verify real implementation symbols.
5. Validate shared workspace, run uv sync --all-extras, Ruff format check, Ruff
   lint, strict mypy and pytest. Run v0 oracle seed 0 in a fresh ignored run
   directory and compare with the committed oracle report.
6. Record revision, commands, result tails and evidence. Complete only on success;
   otherwise record blockers and bounded backlog tasks. Leave a continuation handoff.

## Boundaries
No API, runtime, dependency or experiment changes. No paid calls, provisioning,
publication, commits or pushes. Restore and validate only. Cloud-only artifacts
are not assumed recovered through Git. Never weaken tests to achieve a pass.

## Initializer reconciliation
The root dry-run found conflicts in `.gitignore`, `AGENTS.md` and `CLAUDE.md`.
The initializer ran without Git/commits in an external staging directory. Its
canonical coordination templates matched the existing generic scaffold exactly
and were refreshed; root adapters were retained deliberately with the approved
strategic/coordination additions, not replaced by generic instructions. The
project context was rewritten with source-verified state. This is not a claim
that a customized root is byte-identical to the initializer's generic scaffold.
