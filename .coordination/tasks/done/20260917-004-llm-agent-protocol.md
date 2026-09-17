---
id: 20260917-004-llm-agent-protocol
title: Enforce single-call LLM turns and correlated observations
status: done
harness: codex
owner: codex/llm-agent-protocol
created_at: 2026-09-17T11:19:17Z
updated_at: 2026-09-17T11:26:46Z
claimed_at: 2026-09-17T11:25:22Z
scope: LLMAgent protocol guard and unit regressions; no adapter changes
expected_files: ["src/agentic_payments_env/agents/llm.py", "tests/test_agents_llm.py", "docs/12-decisions.md", ".coordination/tasks/backlog/20260917-004-llm-agent-protocol.md", ".coordination/tasks/in-progress/20260917-004-llm-agent-protocol.md", ".coordination/tasks/done/20260917-004-llm-agent-protocol.md"]
depends_on: ["20260917-003-prepare-llm-tool-tasks"]
---

# Objective
Prevent partial execution of multi-call model responses and prove the agent emits
consistent multi-turn transcripts, without changing public environment contracts.
Suggested owner: cursor/llm-agent-protocol.

## Spec references and relevant code
M1 T1.03, T1.01 contracts; REQ-CON-10, REQ-TOOL-08; docs/12-decisions.md.
Read-only dependencies: adapters/base.py, contracts/actions.py, benchmark/runner.py,
environment.py, tests/conftest.py. LLMAgent.act currently logs Usage, appends all
assistant calls, then _action_from_turn selects index 0. Runner catches exceptions
and terminates AGENT_ERROR; use that path, do not add an environment error code.
All source paths are under src/agentic_payments_env unless shown otherwise.

## Implementation
1. Add failing regressions using a recording fake defined in this test module;
   snapshot messages so later mutations cannot invalidate assertions.
2. Define LLMAgentProtocolError in llm.py, preserving existing signatures. Validate
   count and correlation ID before appending an accepted assistant message or
   returning an Action; record Usage first. Use stable prefixes from the plan.
3. Reject multiple calls atomically and IDs that are missing, non-string, empty
   or whitespace-only. Preserve valid IDs exactly; never synthesize a replacement.
4. Keep zero-tool textual finish, argument normalization, unknown-tool routing,
   max-step forced finish and rationale/report truncation unchanged. Reset clears
   all episode-local state. Do not add queueing, retries or prompt edits.
5. Append the next available D-nn in docs/12-decisions.md, linking ADR-0001 and
   clarifying the previously unspecified multi-call behavior. Do not rewrite old
   decisions or create a requirement identifier. Reference existing applicable
   REQ identifiers in nearby docstrings/tests per AGENTS.md.

## Acceptance criteria
- Multi-call turn raises the specific exception before any Action is returned;
  it is not appended as an accepted call or left pending. Returned Usage retained.
- Missing/invalid single-call IDs produce the stable invalid-ID error.
- Captured two/three-turn messages contain one result per accepted call, correct
  ID and ordered observations; a ToolError observation keeps the same correlation.
- Single-call arguments/name reach Action unchanged except existing normalization.
- Reset after success/failure removes old messages, pending ID and usage.
- Text-only response and forced finish preserve existing outcomes; forced finish
  makes no model request. Include max_steps=1 and boundary after a valid call.
- Empty/malformed argument behavior and unknown-tool handling keep existing tests.
- Normative decision note present; adapter files and public contracts untouched.

## Targeted verification
`uv run pytest -q tests/test_agents_llm.py tests/test_hidden_leak.py`
Then the full gate below. This task must pass independently of task 005.

## Startup and constraints
Read AGENTS.md, .coordination/README.md, .coordination/context/project.md, the
approved .coordination/plans/2026-09-17-llm-tool-protocol.md and ADR-0001 before edits.
Read the task's spec references, actual Git state, in-progress claims and latest
handoff. Preserve uncommitted startup files and pytest pythonpath configuration.
Move this file to in-progress, set harness: cursor, a human-readable owner, and
UTC claimed_at/updated_at before editing. Intended executor: user-controlled Cursor
with Grok 4.6; no task is preclaimed merely because that executor is intended.
One task per owner; no edits outside expected_files without documenting scope and
resolving overlap first. No commits/pushes, real API calls, keys, provisioning,
new dependencies, test weakening or unrelated refactors. Existing open Claude
sessions alone are not a blocker. Use repository state, not prior chat, as truth.

## Full verification gate
Run from repository root and record exit codes and output tails:
```bash
uv sync --all-extras
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest -q
git diff --check
```
The historical baseline had 427 tests; new tests should increase coverage, not
hold an artificial count. Do not claim tests pass without running them. Mark done
only after useful changes are in the final target checkout and verification is
recorded; otherwise leave in-progress with blocker and exact next action.

## Current state
Completed in the final target checkout. LLMAgent now rejects multi-call turns and
invalid correlation IDs before appending an assistant call or returning an Action,
while retaining provider-reported Usage.

## Conflicts and blockers
None known at authoring. Recheck active ownership before editing.

## Outcome
Implemented atomic single-call validation, stable protocol errors, exact ID
correlation, reset isolation, multi-turn transcript regressions and normative D-15.

## Verification
- `uv run pytest -q tests/test_agents_llm.py tests/test_hidden_leak.py` — passed (46 tests).
- `uv sync --all-extras` — passed.
- `uv run ruff format --check .` — passed (174 files).
- `uv run ruff check .` — passed.
- `uv run mypy src` — passed (80 source files).
- `uv run pytest -q` — passed (436 tests).
- `git diff --check` — passed.
- Offline only; no live model experiment or provider request was run.
