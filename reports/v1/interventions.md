# v1 held-out intervention evaluation

Held-out set: 200 frozen tasks in `benchmarks/v1/`. Protocol required by
M5: three seeds, confidence intervals, catastrophic rates shown separately
from task/safe success.

## Prompt v2 (intervention 1)

See `reports/v1/prompt-v2.md`. Live-model pre/post on v1 held-out is
**not yet measured**.

## SFT of a 7-8B model (intervention 2)

Data export: `apenv export-sft`. Training is out of this repository.
Evaluation of a fine-tuned checkpoint on v1 held-out is **not yet
measured**. No invented deltas.
