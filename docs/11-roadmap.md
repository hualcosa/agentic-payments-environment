# 11 — Roadmap

Milestones map one-to-one onto links of the closed loop. Each has an exit
criterion that is a test, an artifact, or a measurement — never "feels
done". Later milestones are sketched at lower resolution on purpose; their
ticket files are written when the previous milestone exits.

## Status model: delivery is not evidence

The milestone sequence describes capabilities the project needs. Progress on
those capabilities and evidence about agent behavior are tracked separately.
Use the following cumulative evidence levels; never infer a higher level from a
checked ticket or the existence of a report file:

1. **Implemented** — the required code, schema, dataset, report structure, or
   command exists. This proves delivery only.
2. **Offline validated** — deterministic tests, scripted agents, fake models,
   oracle runs, replay, or invariant checks validate mechanics without making a
   claim about live model behavior.
3. **Live measured** — a reviewed run used named real model versions under a
   predeclared protocol and preserved its traces, configuration, usage, metrics,
   and limitations.
4. **Scientifically supported** — matched comparisons, held-out evaluation,
   uncertainty, controls or ablations, and regression analysis support the
   stated conclusion. A null or negative result may satisfy this level.

Milestone ticket checklists record implementation closure at the evidence level
their text explicitly names. A placeholder saying **not yet measured** is an
honest artifact, but it does not satisfy a live-measurement exit criterion.

### Current evidence snapshot (2026-09-17)

| Milestone | Highest demonstrated evidence | Missing evidence before the research claim |
|---|---|---|
| M0 Scaffold | **Offline validated** | No live-model claim belongs to M0; oracle, replay, invariants, grader matrix, and frozen v0 validate the instrument mechanics. |
| M1 Baseline agents | **Offline validated** | Adapters and the single-tool-turn protocol are tested offline; the required real-model baseline is not yet measured. |
| M2 Failure analysis | **Offline validated** | Annotation and judge machinery plus a scripted corpus exist; real-model failure annotations and live judge agreement are not yet measured. |
| M3 Synthetic data and curriculum | **Offline validated** | Generators, validity filtering, and frozen v1 exist; difficulty correlation against real-model failure remains unmeasured. |
| M4 Reward signals | **Offline validated** | Reward, preference, and scripted anti-gaming mechanics exist; usefulness and misspecification against live behavior are unmeasured. |
| M5 Optimization | **Implemented** | Prompt v2 and SFT export exist; no reviewed live pre/post comparison, fine-tuned checkpoint evaluation, or preference optimization has run. |
| M6 Report | **Implemented** | The report and reproducibility instructions summarize committed artifacts, but headline live-model findings remain unavailable. |

This snapshot is point-in-time state, not a permanent weakening of the milestone
exit criteria below. Update it only from reviewed evidence artifacts.

| Milestone | Loop link | Headline deliverable | Exit criterion |
|---|---|---|---|
| M0 Scaffold | environment, tasks, graders (rule-based) | working package, benchmark v0 (31 tasks), 8 graders, scripted agents, CI green | grader matrix passes; oracle passes every task; replay is byte-identical; `reports/v0/oracle.md` committed |
| M1 Baseline agents | baseline agent | provider-agnostic LLM agent adapter, prompt v1, first real numbers | ≥ 2 models × 3 seeds on v0 with `reports/v0/<model>.md` committed; per-code catastrophic counts published |
| M2 Failure analysis | failure taxonomy | annotated trace corpus, taxonomy v1, model-based graders for text (report truthfulness), grader agreement study | ≥ 100 annotated episodes; rule-vs-LLM grader agreement reported; taxonomy changes recorded with evidence |
| M3 Synthetic data and curriculum | synthetic / curriculum data | parametric task generators per family, difficulty knobs, validity filter (oracle must pass), benchmark v1 | 1 000+ generated tasks validated; difficulty correlates with baseline failure rate; v1 frozen |
| M4 Reward signals | reward & feedback | episode- and step-level reward from graders, preference pairs from traces, reward-hacking audit | reward spec document; preference dataset; demonstrated reward-hacking case caught by a hard constraint |
| M5 Optimization | optimization / post-training | at least two interventions (prompt/tool design; SFT or preference fine-tuning of a small open model) with pre/post evaluation on held-out tasks | statistically reported improvement or null result on v1 held-out, with catastrophic rates shown separately |
| M6 Report | re-evaluation → technical report | technical report, reproducibility package | report committed; a fresh clone reproduces headline numbers from committed configs |

## Next research gate — R1 reviewed live baseline

**Question:** On frozen benchmark v0, where do selected real LLM agents fail,
and which failures are agent behavior rather than environment, task, adapter, or
grader defects?

**Authorization boundary:** live provider calls may incur cost and MUST NOT run
until the owner approves the named models, model versions, maximum spend, and
execution command. Defining this gate is not authorization to execute it.

**Protocol:**

1. Lock the environment revision, benchmark v0 hash, prompt v1 hash, adapter
   configuration, model versions, seeds, retry policy, and spend ceiling before
   interpreting results.
2. Run a small cost-capped smoke sample across all four task families. Its only
   purpose is to detect protocol, artifact, task, and grader defects; it does not
   produce a behavioral conclusion.
3. If the smoke sample is valid, run at least two model families over all 31 v0
   tasks with three declared seeds per model, as required by M1. If the approved
   cost ceiling cannot support that design, record the shortfall and keep R1
   open rather than weakening the claim.
4. Review catastrophic episodes and a stratified sample of non-catastrophic
   successes and failures before publishing aggregate interpretations.

**Metrics:** task success, safe success, catastrophic count and rate by code,
over-refusal/decline rate, efficiency, recovery performance, token usage, and
failure distribution by task family. Report variation across seeds and never
fold catastrophic failures into one averaged score.

**Evidence artifacts:** immutable run configuration and metadata, complete
traces, raw and aggregated grader outputs, usage/cost record, reviewed failure
annotations, generated report, and a short experiment record containing the
hypothesis, setup, result, surprise, limitations, and next hypothesis.

**Exit criterion:** R1 exits only when the full declared comparison is complete,
artifacts are reviewable and reproducible, sampled traces have been manually
checked for validity, and the report distinguishes measured facts from
interpretation. Passing offline tests or completing the smoke sample alone does
not exit R1.

**Result-dependent next step:**

- If task, environment, adapter, or grader defects materially affect results,
  repair measurement validity and rerun R1 before optimizing the agent.
- If real failures form repeated, reviewable clusters, use those traces to scope
  M2 taxonomy/annotation work and select the smallest targeted intervention.
- If v0 shows a ceiling effect, use M3 difficulty evidence to define a harder
  held-out slice before drawing conclusions.
- Choose prompt/tool changes, targeted data, SFT, or preference optimization
  only after the observed failure mechanism justifies them. Do not schedule RL
  merely to complete a roadmap label.

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
