# 11 — Roadmap

Milestones map one-to-one onto links of the closed loop. Each has an exit
criterion that is a test, an artifact, or a measurement — never "feels
done". Later milestones are sketched at lower resolution on purpose; their
ticket files are written when the previous milestone exits.

| Milestone | Loop link | Headline deliverable | Exit criterion |
|---|---|---|---|
| M0 Scaffold | environment, tasks, graders (rule-based) | working package, benchmark v0 (31 tasks), 8 graders, scripted agents, CI green | grader matrix passes; oracle passes every task; replay is byte-identical; `reports/v0/oracle.md` committed |
| M1 Baseline agents | baseline agent | provider-agnostic LLM agent adapter, prompt v1, first real numbers | ≥ 2 models × 3 seeds on v0 with `reports/v0/<model>.md` committed; per-code catastrophic counts published |
| M2 Failure analysis | failure taxonomy | annotated trace corpus, taxonomy v1, model-based graders for text (report truthfulness), grader agreement study | ≥ 100 annotated episodes; rule-vs-LLM grader agreement reported; taxonomy changes recorded with evidence |
| M3 Synthetic data and curriculum | synthetic / curriculum data | parametric task generators per family, difficulty knobs, validity filter (oracle must pass), benchmark v1 | 1 000+ generated tasks validated; difficulty correlates with baseline failure rate; v1 frozen |
| M4 Reward signals | reward & feedback | episode- and step-level reward from graders, preference pairs from traces, reward-hacking audit | reward spec document; preference dataset; demonstrated reward-hacking case caught by a hard constraint |
| M5 Optimization | optimization / post-training | at least two interventions (prompt/tool design; SFT or preference fine-tuning of a small open model) with pre/post evaluation on held-out tasks | statistically reported improvement or null result on v1 held-out, with catastrophic rates shown separately |
| M6 Report | re-evaluation → technical report | technical report, reproducibility package | report committed; a fresh clone reproduces headline numbers from committed configs |

## M0 — Scaffold (ticket file: `milestones/M0-scaffold.md`)

Scope: everything in docs 02–10 at v0 fidelity. No LLM, no network.
Out of scope: prompts, adapters, generators, rewards.

## M1 — Baseline agents (ticket file: `milestones/M1-baseline-agents.md`)

- `adapters/` with a minimal OpenAI-compatible chat-completions client and
  an Anthropic client, each behind an optional extra; the core stays
  dependency-free.
- `agents/llm.py`: converts `Observation`s to messages, `TOOL_SPECS` to
  tool definitions, parses tool calls into `Action`s; strict JSON parsing;
  a malformed model output becomes an `INVALID_ARGUMENT` observation, not a
  crash.
- Prompt v1 with an explicit "safety and authorization contract" section;
  prompt text is versioned in `prompts/` and hashed into the trace.
- Run harness: retries on transport errors only; cost and latency recorded
  per step in `Step.observation.result` metadata? No — in a parallel
  `runs/<id>/meta.json`; traces stay provider-agnostic.
- First results table. Any claim in the README links to a committed report.

## M2 — Failure analysis

- Annotation format for traces (`annotations/*.jsonl`): step-level labels
  with taxonomy codes and free text; a small CLI to annotate.
- LLM-as-judge grader for report truthfulness and explanation quality,
  validated against rule graders where both apply.
- Taxonomy v1: codes added only with ≥ 3 real occurrences in traces.
- Benchmark v0 → v0.1 fixes if analysis reveals task ambiguities (keep old
  files; never edit in place).

## M3 — Synthetic data and curriculum

- `generators/`: per-family parametric generators seeded by `seed`;
  parameters include amounts relative to limits, number of recipients,
  beneficiary name collisions, injection templates and placement, fault
  kinds and ordinals, user script variations, Portuguese instructions.
- Validity filter: generated task must pass its generated oracle plan and
  must fail at least one scripted adversary (otherwise it measures nothing).
- Difficulty model: predicted failure rate from features; curriculum =
  ordering by difficulty with family balance.
- Benchmark v1: 200 held-out tasks frozen; the rest is training pool.

## M4 — Reward signals

- Episode reward: lexicographic (catastrophic → −1 regardless of the rest;
  else weighted dimension scores). Document the weights and their rationale.
- Step reward: shaped from audit events (verified before transfer,
  consent before debit, status check after timeout), with an explicit
  anti-gaming analysis: for each shaped term, a scripted agent that farms
  it without solving the task must still get episode reward ≤ 0.
- Preference pairs: (oracle trace, scripted failure trace) and (agent trace
  A, agent trace B) ranked by `(safe_success, catastrophic count,
  dimension scores)`.

## M5 — Optimization

- Intervention 1: prompt and tool-description changes measured on v1
  held-out; report deltas per family and per catastrophic code.
- Intervention 2: SFT on oracle + filtered agent traces for a small open
  model (e.g. 7–8B) using an external training stack; this repo owns the
  data export (`export-sft`), the evaluation, and the analysis, not the
  trainer.
- Intervention 3 (stretch): preference optimization (DPO/GRPO) using M4
  pairs and rewards.
- Every run: three seeds, confidence intervals, held-out only, catastrophic
  rates shown separately from success.

## M6 — Technical report

- Structure: research question; environment; benchmark; graders and their
  validation; baseline failures by code; interventions and results;
  limitations; reproducibility.
- Reproducibility package: pinned lockfile, committed configs, one command
  to regenerate every table in the report from committed traces.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Executor drifts from spec | REQ ids in code, tests per ticket, freeze test on tasks |
| Graders judged by intuition | grader matrix with scripted adversaries (M0), annotation agreement (M2) |
| Benchmark too easy for frontier models | SOFT/SILENT enforcement, adversarial family, M3 difficulty knobs |
| Benchmark too artificial | PIX concepts (keys, DICT, night limits, MED reversals), realistic user scripts |
| Reward hacking in M4/M5 | hard constraints outside the reward; anti-gaming scripted agents |
| Claims without evidence | reports directory; README links only to committed reports |
