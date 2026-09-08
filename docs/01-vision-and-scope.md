# 01 — Vision and scope

## 1. Research question

> Can an AI agent complete realistic, long-horizon payment tasks while
> remaining financially correct, explicitly authorized, policy-compliant, safe
> under adversarial inputs, capable of recovering from tool and workflow
> failures, and efficient and auditable?

Everything in this repository exists to make that question measurable, and
then to test whether specific interventions (prompting, data, reward design,
post-training) change the answer.

## 2. Positioning

| | TRAIL (separate repo) | Agentic Payments Environment (this repo) |
|---|---|---|
| Purpose | applied product and user experience for agentic payments | research environment, benchmark, graders, failure analysis, behavior optimization |
| Users | end users, product stakeholders | the owner, reviewers, future collaborators |
| Infrastructure | real integrations, deployment | none: pure Python, deterministic sandbox |
| Success | features shipped | measurable, reproducible claims about agent behavior |

The two must stay decoupled. This repo MUST NOT import TRAIL and TRAIL MUST
NOT be required to run anything here. Shared ideas travel as documents, not as
code dependencies.

## 3. Target specialization demonstrated

`Agent environments -> evals/graders -> synthetic data -> reward signals ->
RL/post-training -> agent behavior`

Each milestone in `11-roadmap.md` adds one link of this chain. The repository
is designed so that later links (reward signals, post-training) reuse the
contracts defined in the first link (environment, traces, graders) without
rewriting them.

## 4. The closed experimental loop

```
                 +-------------------------------------------------+
                 |                                                 v
 environment -> tasks & observations -> agent -> traces -> graders -> failure taxonomy
                 ^                                                 |
                 |                                                 v
        optimization / post-training <- reward & feedback <- synthetic / curriculum data
                 |
                 v
          re-evaluation -> technical report
```

Design consequence: every artifact produced on the left of the loop
(`TaskSpec`, `EpisodeTrace`, `GraderResult`) is a versioned, serializable
contract, because artifacts on the right of the loop (reward models, training
sets) consume them months later.

## 5. Scope of the whole project

In scope, across all milestones:

- a deterministic payment sandbox with PIX-like instant transfers;
- a task specification format with a public part and a hidden ground truth;
- a benchmark of task families with frozen, versioned task sets;
- rule-based graders for eight dimensions; later, model-based graders;
- a coded failure taxonomy;
- scripted agents for grader validation; later, LLM baseline agents;
- synthetic task generation and curriculum construction;
- reward signal design derived from graders;
- optimization (prompt optimization, SFT, preference/RL fine-tuning of small
  open models) and rigorous re-evaluation;
- a technical report.

## 6. Non-goals (all milestones)

- Real banking integration, real credentials, real funds, real PII.
- A frontend, a REST API, a database, cloud deployment.
- Multi-currency, FX, card networks, credit, loans, investments.
- Simulating fraud detection models. Risk decisions are deterministic rules.
- Perfect fidelity to Banco Central do Brasil PIX regulation. The sandbox
  borrows concepts (keys, DICT lookup, night limits, MED-style reversals) to
  be realistic, not to be compliant.
- Emulating a specific bank's product.

## 7. Design principles

1. **Metrics before architecture.** Graders and the failure taxonomy are
   defined before the environment is extended. A feature that cannot be
   graded is not built.
2. **Environment independent of model providers and agent frameworks.** The
   core package imports nothing from an LLM vendor. Agents are anything that
   implements the `Agent` protocol.
3. **Deterministic replay.** Given `(TaskSpec, seed, list[Action])` the
   environment produces byte-identical traces. There is no wall clock and no
   unseeded randomness.
4. **Explicit state transitions and audit logs.** Every mutation of the world
   is an audit event; every step records a transition with state hashes.
5. **Hard constraints remain visible.** Catastrophic failures are reported by
   code, never averaged away.
6. **Hidden ground truth is structurally hidden.** The agent sees
   `TaskSpec.public`; graders see `TaskSpec.hidden`.
7. **The environment can permit misbehavior.** Policy rules have enforcement
   modes so that experiments can measure what an agent *would* do, not only
   what a bank backend lets it do.
8. **Minimal dependencies, strong typing, small modules.**
9. **No fabricated results.** Numbers in documents come from committed run
   artifacts.
10. **Every task ships with a golden trajectory.** A benchmark task without a
    passing oracle plan is a bug in the task.

## 8. Glossary

| Term | Meaning |
|---|---|
| Agent | the system under test; consumes `Observation`s and emits `Action`s |
| Simulated user | the scripted principal who issued the instruction, grants consent, approves step-up and answers clarifications |
| World / WorldState | the full hidden state of the sandbox |
| Fixture | the initial `WorldState` description inside a `TaskSpec` |
| Episode | one run of one task with one seed and one agent, from `reset` to termination |
| Step | one `Action` and the resulting `Observation` and `StateTransition` |
| Trace | the ordered list of steps plus metadata; the unit of grading and of training data |
| Tool | a named operation the agent can invoke; the only way to observe or mutate the world |
| Fault | a scripted deviation of a tool from normal behavior (timeout, outage, stale read) |
| Consent | an explicit, scoped, time-limited authorization from the simulated user for one debit |
| Step-up authentication | a stronger authentication level required above an amount threshold |
| Policy rule | a deterministic rule evaluated on a proposed transfer |
| Enforcement mode | HARD (environment rejects), SOFT (executes with warning), SILENT (executes, only audited) |
| Grader | a function from `(TaskSpec, EpisodeTrace, WorldState)` to a `GraderResult` for one dimension |
| Dimension | one of the eight graded aspects of behavior |
| Violation | a coded finding emitted by a grader with a severity |
| Catastrophic | severity level that makes an episode unsafe regardless of task success |
| Safe success | task success with zero catastrophic violations |
| Oracle plan | the scripted list of actions inside a task's hidden section that solves the task |
| Task family | a group of tasks sharing a scenario type and grading emphasis |
| PIX key | an alias (email, phone, CPF, random key) that resolves to a destination account |
| DICT lookup | resolving a PIX key to its holder (name, masked document, bank) |
| Centavos | integer minor units of BRL; the only money representation |
