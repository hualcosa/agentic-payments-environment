# Specification index

This directory is the complete specification for the Agentic Payments
Environment. It is written to be executed by a coding agent working ticket by
ticket, so it is deliberately explicit and repetitive in places.

## Reading order

| # | Document | Owns | Read when |
|---|----------|------|-----------|
| Context | `00-project-context.md` | shared strategic purpose, experimental priorities and evidence expectations (not implementation status) | at session start, before proposing work |
| 01 | `01-vision-and-scope.md` | research question, positioning, non-goals, design principles, glossary | first |
| 02 | `02-domain-model.md` | entities, money, ids, clock, transfer state machine, invariants | before any code |
| 03 | `03-contracts.md` | the typed contracts (normative pydantic models) | before contracts tickets |
| 04 | `04-tools-and-actions.md` | agent-facing tool catalog, arguments, results, error codes, fault semantics | before tools/environment tickets |
| 05 | `05-policies-and-authorization.md` | policy rule catalog, enforcement modes, consent, step-up auth, evaluation order | before policies tickets |
| 06 | `06-environment-runtime.md` | reset / step / finish lifecycle, seed, fault injection, trace recording, replay | before environment tickets |
| 07 | `07-tasks-and-benchmark-v0.md` | task spec schema, simulated user, task families, the frozen v0 task list, oracle plans | before benchmark tickets |
| 08 | `08-graders-and-metrics.md` | the eight dimensions, grader interface, scoring rules, aggregation, report format | before grader tickets |
| 09 | `09-failure-taxonomy.md` | coded failure taxonomy and severity, mapping to graders | alongside 08 |
| 10 | `10-testing-strategy.md` | test layers, invariants, scripted agents as grader validation, CI | before writing tests |
| 11 | `11-roadmap.md` | milestones M0–M6 with exit criteria | for orientation |
| 12 | `12-decisions.md` | decision log and open questions | whenever something is unclear |
| A | `appendix-plan-review.md` | review of the original project brief and what this spec changed | optional |
| M0 | `milestones/M0-scaffold.md` | ticket-by-ticket plan for the first executable milestone | when executing M0 |
| M1 | `milestones/M1-baseline-agents.md` | ticket-level sketch for M1 | after M0 exit criteria are met |

## Conventions used in the spec

- **MUST / MUST NOT / SHOULD / MAY** have their RFC 2119 meanings.
- Requirement ids: `REQ-<AREA>-<nn>`. Areas: `DOM` domain, `CON` contracts,
  `TOOL` tools, `POL` policy, `ENV` environment, `TASK` tasks, `GRD` graders,
  `TAX` taxonomy, `TEST` testing.
- Failure codes: `<AREA>-<nn>` from `09-failure-taxonomy.md`, e.g. `FIN-03`.
- Code blocks marked `# NORMATIVE` are to be transcribed as written (names,
  fields, types). Code blocks marked `# ILLUSTRATIVE` show intent and may be
  adapted.
- Monetary examples are written as `R$1.000,00 = 100000 centavos`.

## One-paragraph summary of the system

A `TaskSpec` describes a world fixture (customers, accounts, beneficiaries, a
PIX key directory, a policy configuration), a natural-language instruction, a
scripted simulated user, a schedule of injected faults, and a hidden ground
truth. `PaymentsEnvironment.reset()` builds a deterministic `WorldState` from
the fixture and returns the first `Observation`. The agent repeatedly submits an
`Action` (a tool call), the environment validates it against policies and
authorization, mutates the world, appends `AuditEvent`s, records a
`StateTransition` into the `EpisodeTrace`, and returns the next `Observation`.
The episode ends when the agent calls `finish` with a declared outcome or the
step budget is exhausted. Eight independent `Grader`s then read the trace, the
final state and the hidden ground truth and produce `GraderResult`s with coded
violations, which are aggregated into an `EpisodeResult` whose
`catastrophic_codes` are always reported individually.
