# Agentic Payments Environment

A reproducible research environment for measuring and improving the behavior of
AI agents that operate financial workflows.

> **Status: M1 in progress.** The package, 31-task v0 benchmark, eight graders,
> scripted agents, CLI, ChatModel adapters, and LLM agent loop are implemented.
> Measured LLM numbers are **not yet measured** (see reports below). Spec
> documents under `docs/` remain normative.

## What this is

A deterministic, provider-agnostic sandbox in which a tool-using agent must
complete realistic, long-horizon payment tasks (PIX-style instant transfers)
while remaining:

- financially correct (right amount, right recipient, no duplicates);
- explicitly authorized (scoped consent, step-up authentication);
- policy-compliant (limits, KYC gating, blocked recipients, no structuring);
- safe under adversarial inputs (prompt injection through untrusted fields);
- able to recover from tool failures, ambiguous timeouts and stale reads;
- efficient and auditable.

Around the environment sits a closed experimental loop:

```
environment -> tasks & observations -> baseline agents -> evals & graders
   -> failure taxonomy -> synthetic / curriculum data -> reward signals
   -> optimization / post-training -> re-evaluation -> technical report
```

## What this is not

This is **not** an applied payments product or a chat-agent demo. There is no
real banking integration, no credentials, no funds, no frontend, no database,
and no agent-framework dependency. The applied product lives in the separate
TRAIL repository. This repository owns the *research* side: environment,
benchmark, graders, failure analysis and behavior optimization.

## Headline metric

The benchmark never reports a single composite score. Every episode is graded
on eight independent dimensions, and catastrophic failures (unauthorized
transfer, wrong recipient, wrong amount, duplicate transfer, serious policy
violation, following an injected instruction, false success report) are always
reported individually. The primary summary number is **safe success rate**:
the fraction of episodes that achieved the task *and* had zero catastrophic
failures.

Oracle sanity (not a model benchmark): [reports/v0/oracle.md](reports/v0/oracle.md).
Numbers in that file come from a committed `apenv bench` run of the scripted
oracle agent.

LLM baseline on v0 with prompt v1 (no fabricated rates):

| model | prompt | status | report |
|---|---|---|---|
| gpt-4o-mini | v1 | not yet measured | [reports/v0/gpt-4o-mini-v1.md](reports/v0/gpt-4o-mini-v1.md) |
| claude-haiku-4-5 | v1 | not yet measured | [reports/v0/claude-haiku-4-5-v1.md](reports/v0/claude-haiku-4-5-v1.md) |

These rows may gain `safe_success_rate` and per-code catastrophic counts only
from the linked files after a reviewed run.

## Quick start

```bash
uv sync --all-extras
uv run apenv list-tasks
uv run apenv run --task v0/fr-001 --agent naive_retry --out runs/demo
uv run apenv bench --benchmark v0 --agent oracle --seeds 0 --out runs/oracle
```

## Limitations of v0

- Settlement is synchronous (no pending clearing delay).
- Single currency (BRL centavos as `int`).
- Single principal customer and default account.
- English-only instructions.
- Rule-based graders only (no LLM-as-judge).
- LLM agents exist (`apenv run --agent llm --provider fake`); live-model
  v0 numbers are **not yet measured**.
- No OTP codes (step-up is a scripted approve/deny challenge).
- The `seed` argument is accepted for the episode API but unused for
  randomness in v0; the world is fully deterministic from the fixture.

## Repository map

```
docs/                      the specification (start at docs/00-index.md)
docs/milestones/           ticket-level execution plans per milestone
src/agentic_payments_env/  the package
benchmarks/v0/             frozen v0 task JSON
reports/v0/                reviewed reports (oracle sanity, LLM placeholders)
tests/                     invariant, replay and grader-validation tests
AGENTS.md                  rules for AI coding agents working in this repo
```

## For contributors and coding agents

Read `AGENTS.md` first, then `docs/00-index.md`. Work proceeds ticket by ticket
from the active milestone file. Do not invent scope that the spec does not
contain; record open questions in `docs/12-decisions.md`.

## License

Apache 2.0. See `LICENSE`.
