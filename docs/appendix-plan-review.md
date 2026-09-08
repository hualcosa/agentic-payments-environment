# Appendix — Review of the original project brief

The original brief (drafted with another model) asked for an M0 scaffold
directly. This spec was written instead of executing that brief, because the
executor will be a less capable model that needs decisions made up front.
This appendix records what the brief got right, what it missed, and what
changed.

## Kept as-is

- Research framing and separation from the TRAIL product repo.
- The closed experimental loop and the "metrics before architecture"
  principle.
- Eight evaluation dimensions with catastrophic failures never hidden by a
  composite.
- Deterministic replay, explicit transitions and audit logs, minimal
  dependencies, strong typing, Apache 2.0, `src/` layout, Python 3.11+.
- No premature infrastructure; no fabricated results.

## Gaps found and how the spec closes them

| # | Gap in the brief | Consequence if left open | Where closed |
|---|---|---|---|
| 1 | No agent-facing tool catalog or action space | executor invents tools ad hoc; graders cannot be written | 04 |
| 2 | No terminal action with an explicit outcome | refusal-correct tasks and false-success claims cannot be graded | 04 §3.15, D-08 |
| 3 | No idempotency-key model | the central payment-recovery mechanic (ambiguous timeout → duplicate) does not exist | 04 §3.9, 05 §5, 09 FIN-03/REC-01 |
| 4 | Money representation unspecified | floats | 02 §1, D-02 |
| 5 | No PIX key resolution (DICT) | "wrong recipient" has no realistic cause | 02 §4.4, 04 §3.4, adv-004 |
| 6 | Authentication, authorization and consent conflated | failures cannot be attributed; AUTH-02 impossible | 05 §1, §4 |
| 7 | No enforcement modes | agent can never misbehave; benchmark measures the backend | 05 §2, D-06 |
| 8 | No simulated user | consent, step-up and clarification have no counterparty | 06 §7, 07 §4 |
| 9 | No simulated clock | daily/night limits, expiry, staleness have no substrate | 02 §3, D-03 |
| 10 | No adversarial channels or family | safety dimension has no data | 02 §8, 07 §3.4, D-12 |
| 11 | No grader validation strategy | graders trusted on intuition | 10 §4–5, REQ-GRD-12 |
| 12 | No golden trajectory per task | environment bugs and task ambiguity go unnoticed; no SFT seed data | 07 §5–6, REQ-TASK-04 |
| 13 | Hidden ground truth not structurally separated | executor leaks it into the prompt | 03 §6, 06 §5, leak test |
| 14 | Taxonomy without codes | graders emit free text; no stable metrics across milestones | 09 |
| 15 | Benchmark freezing rules absent | tasks silently change between runs | 07 §1 REQ-TASK-02 |
| 16 | Efficiency undefined | arbitrary step penalties | 08 §3.7 |
| 17 | "Refunds or reversals" unspecified | conservation and pairing rules missing | 02 §5 REQ-DOM-18 |
| 18 | Roadmap beyond M0 absent | later milestones would reinvent contracts | 11 |
| 19 | No rules for the executing agent | inconsistent style, forbidden deps, silent guesses | AGENTS.md |

## Changes to the brief's file list

The brief's flat `contracts.py`, `environment.py`, `policies.py`,
`graders.py` became small packages (`contracts/`, `graders/`, `tools/`,
`agents/`, `benchmark/`) because each grew past a comfortable single-file
size once specified. `docs/architecture.md`, `docs/benchmark-v0.md`,
`docs/failure-taxonomy.md`, `docs/roadmap.md` map to 06, 07, 09, 11.
`examples/task.example.json` is superseded by the exported, frozen
`benchmarks/v0/*.json` files. `AGENTS.md`, `LICENSE`, CI, README are kept.

## Things deliberately not added

- LangGraph or any orchestration framework, a database, a frontend, cloud
  deployment (all excluded by the brief and by 01 §6).
- LLM-based graders in M0 (M2).
- Portuguese instructions in v0 (M3 augmentation).
- Asynchronous settlement (contracts reserve `PENDING` for it).
