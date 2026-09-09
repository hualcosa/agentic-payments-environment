# Taxonomy v1 evidence log

Source: `annotations/v0-scripted.jsonl` (124 episodes; oracle, quitter, liar,
naive_retry on frozen v0, seed 0). Codes are rule-grader labels, not live LLM
traces.

## Rule

A code is added to `docs/09-failure-taxonomy.md` only with ≥ 3 real
occurrences **and** it is not already in 09. This corpus contains **no**
code outside the M0 09 table.

**Taxonomy v1 = 09 as frozen in M0. No codes added.**

## Episode-code counts (occurrences across episodes, unique codes per episode)

| code | episodes |
|---|---|
| AUD-03 | 31 |
| FIN-06 | 29 |
| SAF-06 | 23 |
| FIN-05 | 10 |
| SAF-05 | 10 |
| POL-05 | 8 |
| POL-06 | 8 |
| SAF-02 | 7 |
| AUTH-06 | 6 |
| REC-03 | 6 |
| AUD-01 | 4 |
| REC-01 | 3 |
| AUTH-04 | 2 |
| AUTH-05 | 2 |
| FIN-03 | 2 |
| TASK-02 | 2 |
| REC-02 | 1 |

Codes with ≥ 3 occurrences are already in 09. Codes below the threshold are
also already in 09. No candidate for a new code.
