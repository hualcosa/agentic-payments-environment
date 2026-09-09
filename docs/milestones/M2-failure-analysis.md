# Milestone 2 — Failure analysis

Goal: a step-level annotated trace corpus, an LLM-as-judge grader for
report text, a recorded rule-vs-LLM agreement study, and a taxonomy v1
evidence log. New taxonomy codes require ≥ 3 real occurrences.

Execute tickets **in order**. Commit after each ticket (AGENTS.md §6).
Do not edit frozen `benchmarks/v0/` in place; v0.1 would be a new
directory if task ambiguities appear.

M1 LLM baseline reports are **not yet measured**. Until a reviewed model
run exists, the corpus is built from oracle and scripted-agent traces
(grader-derived labels). That still yields ≥ 100 episodes and a
deterministic agreement check against FakeChatModel.

---

## T2.01 — Annotation schema and JSONL IO

**Files**: `src/agentic_payments_env/annotations/__init__.py`,
`src/agentic_payments_env/annotations/schema.py`,
`tests/test_annotations.py`.
**Spec**: 11 M2, 09 (codes), 03 FrozenModel conventions.

- `StepAnnotation` FrozenModel: `step_index: int` (1-based, matching
  `Step.step_index`), `codes: list[str]`, `note: str = ""`.
- `EpisodeAnnotation` FrozenModel: `schema_version: str = SCHEMA_VERSION`,
  `task_id: str`, `seed: int`, `agent_name: str`,
  `annotator: str` (free string; use `rule-graders`, `human`, or `llm-judge`),
  `episode_codes: list[str]`, `steps: list[StepAnnotation] = []`,
  `note: str = ""`.
- Every code in `codes` / `episode_codes` MUST match `^[A-Z]{3}-[0-9]{2}$`
  or the list may be empty.
- `dumps_jsonl(records) -> str` and `loads_jsonl(text) -> list[EpisodeAnnotation]`
  (one JSON object per line, UTF-8, `model_dump(mode="json")`).
- `write_jsonl(path, records)` / `read_jsonl(path)`.

Tests: round-trip two records; reject `FIN-1` as a code; empty codes allowed.

## T2.02 — Bootstrap annotations from graded traces

**Files**: `src/agentic_payments_env/annotations/from_grade.py`,
`src/agentic_payments_env/cli.py` (`annotate-trace` subcommand),
`tests/test_annotations_from_grade.py`.
**Spec**: 11 M2, 08 graders, 09.

- `from_episode(task, trace, result) -> EpisodeAnnotation` with
  `annotator="rule-graders"`, `episode_codes` = unique violation codes from
  `result.violations` (stable sort), and one `StepAnnotation` on the last
  step containing those codes (or step_index=0 with empty steps if the
  trace has no steps).
- CLI: `apenv annotate-trace --trace <path> --result <path> --out <file.jsonl>`
  appends one `EpisodeAnnotation` line. `--result` is the
  `seed-*.result.json` written next to the trace (required). Do not
  re-drive an agent (would need hidden presets).

Tests: oracle rt-001 annotation has empty episode_codes; quitter or liar
produces at least one code; jsonl append.

## T2.03 — Annotated corpus ≥ 100 episodes

**Files**: `src/agentic_payments_env/annotations/corpus.py`,
`annotations/v0-scripted.jsonl`, `tests/test_annotations_corpus.py`.
**Spec**: 11 M2 exit (≥ 100 annotated episodes).

- Build annotations by running a fixed list of presets over all v0 tasks,
  seed 0, `from_episode` after `grade_episode`.
- Commit `annotations/v0-scripted.jsonl` with **≥ 100** lines.
- `build_scripted_corpus() -> list[EpisodeAnnotation]` used by a test that
  also checks the committed file has the same line count as a fresh build
  (or hash equality).

Presets: at least `oracle`, `quitter`, `liar`, `naive_retry` (31×4 = 124).
No network. No LLM.

## T2.04 — LLM-as-judge grader (report text)

**Files**: `src/agentic_payments_env/graders/llm_judge.py`,
`tests/test_graders_llm_judge.py`.
**Spec**: 11 M2, 08 AUD, 09 AUD-01, SAF-02.

- `ReportTruthJudge(model: ChatModel)` implements `Grader` with
  `dimension=AUDITABILITY` (or a dedicated check that only adds
  `JUDGE-AUD-01` style codes — **do not invent 09 codes**).
  Emit existing `AUD-01` when the judge says the COMPLETED report omitted
  transfer ids, else no violation. FakeChatModel in tests.
- Parse the model text as JSON `{"omits_transfer_ids": bool, "note": str}`.
  Malformed → no violation (restrictive for false positives).
- Must not read `TaskSpec.hidden` besides what rule graders already get —
  the judge sees the finish `report` string and the list of agent transfer
  ids from the trace/audit, not expected_outcome.

Tests: FakeChatModel flags omit → AUD-01; malformed JSON → no crash, no
AUD-01; does not appear in `DEFAULT_GRADERS` (opt-in).

## T2.05 — Rule vs judge agreement report

**Files**: `src/agentic_payments_env/annotations/agreement.py`,
`reports/v0/grader-agreement.md`, `tests/test_annotations_agreement.py`.
**Spec**: 11 M2 exit (agreement reported).

- On the committed corpus, compare rule `AUD-01` in `episode_codes` to a
  FakeChatModel judge scripted to copy the rule (perfect agreement) **or**
  document that live-model agreement is **not yet measured**.
- Commit `reports/v0/grader-agreement.md` stating the protocol and either
  numeric agreement from the fake-judge sanity check or "not yet measured"
  for live models. No fabricated live-model kappa.

Tests: file exists; contains `not yet measured` and/or an
`agreement_rate` of the fake sanity check in `[0, 1]`.

## T2.06 — Taxonomy v1 evidence log

**Files**: `reports/v0/taxonomy-v1.md`.
**Spec**: 11 M2, 09 (codes added only with ≥ 3 real occurrences).

- Count `episode_codes` in the committed corpus.
- New codes MUST NOT be added to `docs/09-failure-taxonomy.md` unless a
  code appears ≥ 3 times **and** is not already in 09. If none qualify,
  the report says taxonomy v1 = 09 as frozen in M0, no additions.

Tests: file exists; states whether any code was added (expected: none).

## T2.07 — Benchmark v0.1 decision

**Files**: `benchmarks/README.md` (short note) or
`reports/v0/v0.1-decision.md`.
**Spec**: 11 M2 (keep old files; never edit v0 in place).

- If no task ambiguity was found in the corpus notes, commit a decision
  file: **no v0.1 freeze**; v0 remains the evaluated set.
- Do not modify `benchmarks/v0/*.json`.

Tests: `benchmarks/v0` still matches export (existing freeze test);
decision file exists.

## M2 exit checklist

- [ ] ≥ 100 annotated episodes committed.
- [ ] Rule-vs-LLM grader agreement reported (live or explicitly
      "not yet measured" plus fake-judge sanity).
- [ ] Taxonomy changes recorded with evidence (including "none").
