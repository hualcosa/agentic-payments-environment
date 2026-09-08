# Agentic Payments Environment

A reproducible research environment for measuring and improving the behavior of
AI agents that operate financial workflows.

> **Status: specification phase.** The design documents under `docs/` are the
> source of truth. No implementation exists yet. Milestone 0 (M0) is the first
> executable scaffold and is fully specified in `docs/milestones/M0-scaffold.md`.

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

## Repository map

```
docs/                      the specification (start at docs/00-index.md)
docs/milestones/           ticket-level execution plans per milestone
src/agentic_payments_env/  the package (created in M0)
benchmarks/                frozen benchmark task files (created in M0)
tests/                     invariant, replay and grader-validation tests (M0)
AGENTS.md                  rules for AI coding agents working in this repo
```

## For contributors and coding agents

Read `AGENTS.md` first, then `docs/00-index.md`. Work proceeds ticket by ticket
from the active milestone file. Do not invent scope that the spec does not
contain; record open questions in `docs/12-decisions.md`.

## License

Apache 2.0. See `LICENSE`.
