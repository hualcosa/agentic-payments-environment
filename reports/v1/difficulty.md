# Benchmark v1 difficulty vs failure rate

Held-out set: frozen JSON under `benchmarks/v1/` (200 tasks after the
T3.06 validity filter). Training remainder: `benchmarks/v1-train/`.

## Live LLM baseline

**not yet measured**. M1 reports are placeholders; do not invent a
correlation between `difficulty_score` and model `safe_success_rate`.

## Scripted-adversary note

Validity requires the oracle to succeed and at least one of
quitter / liar / naive_retry / obedient / splitter to fail. Difficulty is
the integer score from `generators/difficulty.py` (amount/limit millis,
fault count, injection, Portuguese instruction). A numeric Spearman (or
similar) against live-model fail rate waits on a reviewed `apenv bench`
report.
