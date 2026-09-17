# AGENTS.md — rules for AI coding agents working in this repository

This file is the operating contract for any AI coding agent (Cursor, Claude
Code, Codex, etc.) executing work here. The human owner acts as planner and
reviewer; the coding agent is the executor. Read this file completely before
touching any code.

<!-- shared-agent-workspace:coordination:start -->
## Cross-harness coordination

The repository-wide source of truth for collaboration is
`.coordination/README.md`. Read and follow it before changing project files.

At the start of a work session:

1. Read `.coordination/context/project.md`.
2. Review `.coordination/tasks/in-progress/` and recent handoffs.
3. Claim a backlog task, or create and claim a task, before editing project
   files.

Keep durable context in the repository coordination files. Harness-local
memory is supplementary and must not be treated as shared state.
<!-- shared-agent-workspace:coordination:end -->

## 0. Shared strategic context — read at session start

Read `docs/00-project-context.md` before proposing architecture, features,
experiments, refactors or roadmap changes. It is the shared strategic context
for Codex, Claude Code and Cursor, not a replacement for the technical spec.

This project exists to turn production/agentic engineering experience into
verifiable ability to measure, explain and modify agent behavior. The
environment is a research instrument and potential flagship, not a generic
framework or banking product. Prefer small, complete experimental loops and
reproducible evidence over feature count. RL is a possible intervention, not
a checkbox or a prerequisite for the first useful experiment.

At the start of related work:

1. Read the shared context, then `docs/00-index.md` and the relevant spec/ticket.
2. Inspect Git branch, revision, status and available artifacts. Do not infer
   implementation or milestone completion from old memories or ignored files.
3. If Engram is available, call `mem_current_project`, then `mem_context` or
   `mem_search`. Use Engram for durable decisions, discoveries and handoffs;
   keep shared strategic guidance in the repository as well. If unavailable,
   continue from the repository context and disclose the memory limitation.
4. For proposed work, state the experimental question, metric, evidence
   artifact and smallest useful next step. Do not invent an active experiment.

Save significant decisions/discoveries with `mem_save`, reusing a stable
`topic_key` for an evolving topic; save a session summary before finishing.
Do not start a memory session or invent a session ID; runtime registration
belongs to the harness. Do not use retired memory stores as substitutes.

The strategic direction does not authorize autonomous roadmap execution,
paid runs, provisioning, publication, commits or pushes. Obtain explicit user
authorization for those actions. The commit instructions below specify format
and grouping, not standing permission to commit.

## Communication standard — concise completeness

Default to the shortest response that preserves the information needed for a
correct decision or handoff. Lead with the result or verdict, then include only
material evidence, risks, authorization state, blockers and verification.

- Compress rather than omit: retain decisive facts, necessary qualifiers,
  failure states and uncertainty while removing repetition and routine process
  narration.
- Prefer a small number of high-signal bullets, tables or diagrams over a long
  chronological account. Do not restate the prompt or explain obvious steps.
- Cite the minimum sufficient `file:line` evidence. Summarize verification with
  the command or gate and outcome; include raw output only when requested or
  when diagnosing a failure.
- Distinguish freshly verified facts from historical results in one concise
  phrase. Expand only when the user asks or when safety and correctness require
  the additional detail.

## 1. Where the truth lives

1. `docs/` is the specification. It is normative. If code and spec disagree,
   the spec wins unless a decision in `docs/12-decisions.md` says otherwise.
2. `docs/milestones/<milestone>.md` breaks the active milestone into ordered
   tickets. Work on exactly one ticket at a time, in order, unless the ticket
   says it has no dependencies.
3. Requirement identifiers look like `REQ-ENV-07` or `REQ-GRD-12`. When you
   implement one, reference it in a code comment or docstring near the
   implementation and in the commit message.

## 2. How to execute a ticket

For every ticket:

1. Read the ticket. Then read every spec section the ticket lists under
   "Spec references". Do not start from memory.
2. Create or edit only the files the ticket names. If you believe another
   file must change, stop and record why in `docs/12-decisions.md` under
   "Open questions", then proceed only if the change is trivial and clearly
   implied by the spec.
3. Write the tests listed in the ticket **before or alongside** the code.
   Every ticket has a "Done when" checklist. All boxes must be true.
4. Run the full verification command (section 5) and paste the tail of its
   output into your final message. Never say tests pass without running them.
5. Commit with the message format in section 6.

If a ticket is ambiguous, prefer the interpretation that is (a) more
restrictive for the agent under test, (b) simpler to implement, and (c) more
deterministic. Write the ambiguity and your choice into
`docs/12-decisions.md`.

## 3. Hard rules (never violate)

- **Money is `int` centavos.** Never use `float` or `Decimal` for amounts,
  balances, limits or fees. `100` means R$1.00. See `docs/02-domain-model.md`.
- **No randomness outside the seeded RNG.** No `random.random()`, no
  `uuid4()`, no `time.time()`, no `datetime.now()` inside the package. IDs
  come from `IdGenerator`; time comes from `SimClock`.
- **No network calls** anywhere in `src/` for milestones M0–M2. No HTTP
  clients, no SDKs, no environment-variable credentials.
- **No new runtime dependencies** beyond those listed in
  `docs/12-decisions.md` (currently: `pydantic>=2`). Dev dependencies are
  `pytest`, `ruff`, `mypy`. Ask before adding anything else.
- **Hidden ground truth never reaches the agent.** `TaskSpec.hidden` must not
  appear in any `Observation`. There is a test for this; keep it passing.
- **The environment never crashes on a bad agent action.** Invalid tool
  names, bad arguments and policy violations return a `ToolError`
  observation. Only genuine bugs raise exceptions.
- **State mutations are audited.** Every change to `WorldState` emits an
  `AuditEvent` in the same step. There is an invariant test for this.
- **Catastrophic failures stay visible.** Never fold a catastrophic
  violation into an averaged score. `EpisodeResult.catastrophic_codes` must
  list every one.
- **No fabricated results.** Never write benchmark numbers into docs or the
  README unless they come from a committed run artifact under `runs/` or a
  report the human owner has reviewed. Placeholder text must say
  "not yet measured".
- **No frameworks.** No LangChain, LangGraph, gymnasium, OpenAI Agents SDK
  or similar in the core package. Provider adapters (M1+) live under
  `src/agentic_payments_env/adapters/` behind optional extras.
- **Do not delete or weaken tests** to make CI pass. If a test is wrong,
  explain why in the commit and in `docs/12-decisions.md`.

## 4. Code conventions

- Python 3.11+. `src/` layout. Package name `agentic_payments_env`.
- Type hints on every public function and method. `mypy --strict` on
  `src/` must pass. Use `from __future__ import annotations`.
- Pydantic v2 `BaseModel` for all contracts, with `model_config =
  ConfigDict(frozen=True, extra="forbid")` unless the spec says otherwise.
- Enums are `str, Enum` subclasses with UPPER_SNAKE members whose values equal
  their names (e.g. `COMPLETED = "COMPLETED"`).
- Line length 100. `ruff format` and `ruff check` clean.
- Docstrings on every public class and function: one line stating purpose,
  then the REQ ids it satisfies.
- Tests live in `tests/`, mirror the module name (`tests/test_policies.py`
  for `policies.py`), use plain `pytest` functions, and use fixtures from
  `tests/conftest.py`. No test may depend on execution order.
- Logging: use `logging.getLogger(__name__)`; never `print` in `src/`
  except inside `cli.py`.

## 5. Verification command

Run from the repository root:

```bash
uv sync --all-extras          # or: pip install -e ".[dev]"
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest -q
```

All four must be clean. CI runs the same commands.

## 6. Commit messages

```
<ticket-id>: <imperative summary under 72 chars>

<what changed and why, 1–5 lines>
Satisfies: REQ-XXX-nn, REQ-YYY-mm
```

One ticket per commit where practical. Do not squash unrelated tickets.

## 7. What to do when stuck

- Missing information: check `docs/00-index.md` for the document that owns
  the topic. Each topic has exactly one owning document.
- Conflicting information: newer decision in `docs/12-decisions.md` wins;
  otherwise the more specific document wins over the more general one.
- Still stuck: write the question into `docs/12-decisions.md` under
  "Open questions", implement the most conservative option, and flag it in
  your final message. Do not silently guess.
