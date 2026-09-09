# Milestone 6 — Technical report

Goal: a technical report plus a reproducibility note so a fresh clone can
rebuild tables that this repo actually owns (oracle sanity, grader matrix,
v1 freeze, rewards). Live LLM tables stay **not yet measured**.

---

## T6.01 — Technical report

**Files**: `reports/technical-report.md`, `tests/test_technical_report.py`.
**Spec**: 11 M6.

Sections (all required): research question; environment; benchmark;
graders and validation; baseline failures; interventions and results;
limitations; reproducibility.

Cite only committed paths under `reports/` and `benchmarks/`. No invented
model scores. Point at `reports/v0/oracle.md`, `reports/v0/grader-agreement.md`,
`reports/v1/reward-spec.md`, `reports/v1/interventions.md`.

Tests: file exists; each section heading appears.

## T6.02 — Reproducibility package

**Files**: `reports/reproducibility.md`, `tests/test_reproducibility.py`.
**Spec**: 11 M6.

- Pin is `uv.lock` (already committed).
- One command to regenerate the oracle headline table from committed
  configs:

  `uv sync --all-extras && uv run apenv bench --benchmark v0 --agent oracle --seeds 0 --out runs/oracle`

  Then compare `runs/oracle/report.md` headline rates to
  `reports/v0/oracle.md` (manual or documented). Tests only check the
  document lists this command and `uv.lock`.
- State that live LLM benches need provider extras and keys and are
  **not yet measured**.

## M6 exit checklist

- [ ] Report committed.
- [ ] Reproducibility command documented.
