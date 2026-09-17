# Milestone 5 — Optimization

Status note: checked tickets below record implementation closure. Per
`docs/11-roadmap.md`, a prompt artifact or data export is **implemented**; it
does not establish an intervention effect until a reviewed held-out comparison
is live measured and scientifically supported.

Goal: at least two interventions with pre/post evaluation on v1 held-out.
Live LLM numbers remain **not yet measured** unless credentials exist.
This repo owns data export and evaluation, not an external trainer.

Every claimed numeric delta must come from a committed report.

---

## T5.01 — Intervention 1: prompt v2

**Files**: `prompts/v2.md`, `tests/test_prompts.py` (extend),
`reports/v1/prompt-v2.md`.
**Spec**: 11 M5.

- `prompts/v2.md` is v1 plus an extra bullet: after a policy rejection,
  call `check_transfer_policy` before retrying a smaller amount (do not
  structure). Same safety contract as v1.
- `load_prompt("v2")` works (existing loader).
- Report: **not yet measured** on v1 held-out for live models. May include
  FakeChatModel note that prompt hash differs from v1.

Tests: v2 file exists; hash != v1 hash; safety contract phrases present.

## T5.02 — Intervention 2: SFT export

**Files**: `src/agentic_payments_env/export_sft.py`,
`src/agentic_payments_env/cli.py` (`export-sft`),
`tests/test_export_sft.py`.
**Spec**: 11 M5.

- `export_sft(tasks, out_path)` writes JSONL. Each line:
  `{"task_id", "agent": "oracle", "actions": [ {tool_name, arguments} ]}`.
- Drive oracle seed 0 on a given task list (tests use `v0/rt-001` only).
- CLI: `apenv export-sft --task v0/rt-001 --out <file>`.

Tests: one line for rt-001; first action tool_name is a string; file
JSONL parses.

## T5.03 — Held-out evaluation placeholder

**Files**: `reports/v1/interventions.md`.
**Spec**: 11 M5 (three seeds, CIs, catastrophic rates separate).

- State that prompt-v2 vs v1 and SFT of a 7–8B model on the export are
  **not yet measured** on `benchmarks/v1/` (200 tasks). Do not invent
  deltas or confidence intervals.

Tests: file exists; contains `not yet measured`; mentions v1 held-out.

## T5.04 — Stretch DPO/GRPO (explicit skip)

**Files**: `reports/v1/interventions.md` (one section).
**Spec**: 11 M5 stretch.

- Record that preference optimization is **not run** in this milestone
  (stretch). No trainer, no fake DPO numbers.

Tests: the interventions file contains `stretch` and `not run` or
`not yet measured`.

## M5 exit checklist

- [x] Two interventions described (prompt v2; SFT export).
- [x] Evaluation report does not invent live-model deltas.
- [x] Stretch PO is explicitly not run.
