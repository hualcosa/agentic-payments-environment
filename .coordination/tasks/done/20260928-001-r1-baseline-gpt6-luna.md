---
id: 20260928-001-r1-baseline-gpt6-luna
title: Prepare R1 baseline with gpt-6-luna (docs, provider errors, provenance)
status: done
harness: claude-code
owner: claude-code/r1-baseline
created_at: 2026-09-28T17:29:14Z
updated_at: 2026-09-28T17:55:00Z
claimed_at: 2026-09-28T17:29:14Z
scope: >
  Align docs with the owner's R1 model decision (gpt-6-luna baseline plus one
  comparator from another family, still to be chosen); keep provider errors
  out of agent-behavior metrics; add run provenance to meta.json/turns.json.
  No live calls, commits or pushes.
expected_files:
  - docs/11-roadmap.md
  - docs/12-decisions.md
  - README.md
  - reports/technical-report.md
  - reports/v0/gpt-4o-mini-v1.md
  - reports/v0/claude-haiku-4-5-v1.md
  - reports/v0/gpt-6-luna-v1.md
  - .coordination/context/project.md
  - src/agentic_payments_env/adapters/base.py
  - src/agentic_payments_env/adapters/openai_compat.py
  - src/agentic_payments_env/agents/llm.py
  - src/agentic_payments_env/benchmark/runner.py
  - src/agentic_payments_env/cli.py
  - tests/test_adapters_providers.py
  - tests/test_agents_llm.py
  - tests/test_cli.py
  - tests/test_m1_reports.py
depends_on: []
---

# Objective

Make the repository describe and support the R1 experiment the owner will
actually run: `gpt-6-luna` baseline plus one comparator from another model
family (comparator not chosen yet), executed through an OpenAI-compatible
endpoint. Run artifacts stay provider-neutral.

## Acceptance criteria

- Docs no longer name gpt-4o-mini / claude-haiku-4-5 as planned baselines.
- R1 in `docs/11-roadmap.md` names the baseline, points to the open comparator
  question and frames the limit as usage (quota or spend).
- Episodes that end because the model call failed are marked in `meta.json`
  (`provider_error`) and counted, so they are not read as agent behavior.
- `meta.json` records environment revision, benchmark hash and request/retry
  policy; `turns.json` records the served model when the provider reports it.
- No proxy/base URL/local route appears in run artifacts.
- Full gate passes.

## Current state

Implemented, uncommitted. Next: owner chooses the comparator (Q-19), then
authorizes the R1 smoke sample.

## Conflicts and blockers

None. No other task in progress.

## Outcome

- Docs: D-26 and Q-19 in `docs/12-decisions.md`; R1 names the baseline and uses
  "usage limit" wording; README, technical report and project context updated;
  placeholders renamed to `reports/v0/gpt-6-luna-v1.md` and `comparator-v1.md`.
  `tests/test_m1_reports.py` points at the new paths (same assertions).
- `LLMAgent.provider_error` records `PROVIDER_ERROR type=<Exception>` when
  `model.complete` raises; runner/CLI write `episodes[].provider_error` and
  `provider_error_episodes` in `meta.json`.
- OpenAI adapter pins `max_retries=2` and `timeout=120`; `ModelTurn` and
  `NormalizedModelTurn` gain `served_model` (from `response.model`).
- CLI `meta.json` adds `environment_revision`, `tasks_sha256`, `benchmark_id`
  (bench) and `request_policy` (openai). No endpoint is written.
- Follow-up: Anthropic adapter has no `base_url` and no pinned policy (only
  needed if the comparator requires it, Q-19).

## Verification

- `uv run ruff check src tests`, `ruff format --check src tests`: clean.
  Repo-wide `ruff check .` fails only on untracked `.ua/.trash-*/` scratch
  files that predate this task.
- `uv run mypy src`: no issues (83 files).
- Targeted pytest (owner asked not to rerun the full suite): test_cli,
  test_agents_llm, test_adapters_providers, test_m1_reports,
  test_llm_protocol_integration, test_adapters_isolation, test_adapters_base: all pass.
- No live model calls made.
