# Benchmark v1.1 difficulty vs scripted failure rate

Sample size: **1002** validated generated tasks (before the 200-task held-out split).

## Family distribution

| family | count |
|---|---|
| ADVERSARIAL | 254 |
| FAILURE_RECOVERY | 254 |
| POLICY_CONSTRAINED | 254 |
| ROUTINE_TRANSFER | 240 |

## Scripted-adversary correlation

Spearman rho (`difficulty_score` vs mean failure rate across quitter, liar, naive_retry, obedient, splitter): **0.813**.

positive association: harder tasks tend to break more scripted presets.

## Live LLM baseline

**not yet measured**. Do not infer model correlation from this table.
