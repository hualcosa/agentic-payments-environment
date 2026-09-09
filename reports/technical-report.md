# Technical report — Agentic Payments Environment

## Research question

Can we measure, with a deterministic simulated PIX environment and coded
graders, whether tool-using agents complete payment tasks without
catastrophic failures (wrong recipient, unauthorized debit, injection
following, false success)? The primary headline is **safe success rate**,
never a single composite that hides catastrophes.

## Environment

The package `agentic_payments_env` is a seed-labeled, integer-centavos
world: accounts, PIX directory, consents, step-up, policy limits, faults,
and an audit log. Agents see `TaskPublic` and `Observation`s only
(REQ-CON-10). Invalid actions return `ToolError`. Mutations emit
`AuditEvent`s. Replay must match state hashes (REQ-ENV-16).

There is no real bank, no network in the core loop for M0, and no agent
framework in the core package. Optional `[openai]` / `[anthropic]` extras
live under `adapters/`.

## Benchmark

- **v0**: 31 frozen tasks in `benchmarks/v0/` (routine, policy, recovery,
  adversarial). Oracle sanity: [reports/v0/oracle.md](v0/oracle.md).
- **v1**: 200 held-out generated tasks in `benchmarks/v1/` plus
  `benchmarks/v1-train/`, after the T3.06 validity filter (oracle succeeds;
  at least one scripted adversary fails). Difficulty vs live-model fail
  rate: [reports/v1/difficulty.md](v1/difficulty.md) (**not yet measured**).

## Graders and validation

Eight rule graders (task, financial, authorization, policy, safety,
recovery, efficiency, auditability) emit 09 taxonomy codes. Scripted
presets plus the oracle form the M0 grader matrix. M2 added a 124-episode
scripted annotation corpus and a FakeChatModel copy-rule agreement check:
[reports/v0/grader-agreement.md](v0/grader-agreement.md). Live judge
agreement is **not yet measured**. Taxonomy v1 added no new codes:
[reports/v0/taxonomy-v1.md](v0/taxonomy-v1.md).

## Baseline failures

LLM baseline reports
[reports/v0/gpt-4o-mini-v1.md](v0/gpt-4o-mini-v1.md) and
[reports/v0/claude-haiku-4-5-v1.md](v0/claude-haiku-4-5-v1.md) are
**not yet measured** (no API credentials in the producing run). Example
traces for catastrophic codes wait on a reviewed model run:
[reports/v0/examples/README.md](v0/examples/README.md).

Scripted failures on v0 are encoded in the annotation corpus
(`annotations/v0-scripted.jsonl`) and the grader matrix tests.

## Interventions and results

1. Prompt v2: [reports/v1/prompt-v2.md](v1/prompt-v2.md) — **not yet
   measured** on v1 held-out.
2. SFT export: `apenv export-sft` (oracle action JSONL). Fine-tune and
   eval: **not yet measured**.
3. Stretch DPO/GRPO: **not run**.

See [reports/v1/interventions.md](v1/interventions.md).

Rewards (millipoints, catastrophic floor `-1000`):
[reports/v1/reward-spec.md](v1/reward-spec.md).

## Limitations

Synchronous settlement; single currency; English v0 instructions with
optional generated Portuguese; rule graders for most text; no OTP; seed
unused for RNG in v0; live models and live LLM-as-judge unevaluated here;
CLI `run` still loads v0 task ids from the builder registry (Q-16).

## Reproducibility

Pinned lockfile: `uv.lock`. Commands: [reports/reproducibility.md](reproducibility.md).
This report does not contain unpublished benchmark numbers.
