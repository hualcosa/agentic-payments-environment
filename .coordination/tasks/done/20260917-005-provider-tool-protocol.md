---
id: 20260917-005-provider-tool-protocol
title: Request single-tool turns and validate provider payloads
status: done
harness: codex
owner: codex/provider-tool-protocol
created_at: 2026-09-17T11:19:17Z
updated_at: 2026-09-17T11:28:12Z
claimed_at: 2026-09-17T11:26:59Z
scope: Two provider adapters and provider tests; no LLMAgent or shared contract changes
expected_files: ["src/agentic_payments_env/adapters/openai_compat.py", "src/agentic_payments_env/adapters/anthropic.py", "tests/test_adapters_providers.py", ".coordination/tasks/backlog/20260917-005-provider-tool-protocol.md", ".coordination/tasks/in-progress/20260917-005-provider-tool-protocol.md", ".coordination/tasks/done/20260917-005-provider-tool-protocol.md"]
depends_on: ["20260917-003-prepare-llm-tool-tasks"]
---

# Objective
Ask both providers for at most one tool call and prove outbound multi-turn payloads
preserve tool-call/result correlation using HTTP-free SDK stubs.
Suggested owner: cursor/provider-tool-protocol.

## Spec references and relevant code
M1 T1.01–T1.02; REQ-CON-10; docs/12-decisions.md D-01; ADR-0001 and approved plan.
Read adapters/base.py and existing provider stubs/tests. Public ChatModel.complete,
ChatMessage, ModelTurn and Usage stay unchanged. This task does not rely on task 004:
construct canonical ChatMessage sequences directly for its adapter tests.

## Implementation
1. With nonempty tools, add parallel_tool_calls=False to OpenAI-compatible kwargs;
   add tool_choice={"type":"auto","disable_parallel_tool_use":True} to Anthropic.
   Omit these controls for empty tools; do not force a tool for textual responses.
2. Preserve model selection, schemas, max_tokens, usage parsing and retry policy.
   Do not suppress/retry unsupported-parameter errors as an automatic fallback.
3. Extend existing fake SDKs to capture deep copies of request payloads. Exercise
   assistant tool call, tool result (including error observation JSON), subsequent
   call and textual finish through each concrete adapter.
4. Assert OpenAI function arguments are serialized JSON objects exactly once;
   Anthropic uses tool_use/input and user tool_result blocks with matching IDs.
   Keep system message handling and tool schema transport intact.
5. Preserve all returned calls in ModelTurn even when a stub violates the requested
   count; do not truncate at adapter layer. Task 004 owns rejection. Missing IDs
   should reach the boundary in the existing dict contract, not be silently invented.

## Acceptance criteria
- Correct provider-specific control sent with tools; absent without tools.
- Complete outbound transcript retains the same ID and semantic argument/result
  JSON content for successive calls; no dropped/duplicated results.
- Text-only response and token Usage mapping remain correct.
- Stub returning two calls maps both, allowing agent-level rejection.
- Transport failure retry success and exhaustion are tested under existing policy;
  nontransport/unsupported-parameter errors propagate without fallback.
- No real HTTP, keys, dependency change or SDK import leakage into core.

## Targeted verification
`uv run pytest -q tests/test_adapters_providers.py tests/test_adapters_isolation.py`
Then the full gate below. This task must pass independently of task 004.

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
Completed in the final target checkout. Both adapters request serial tool use only
when tools are present and preserve complete provider responses for agent validation.

## Conflicts and blockers
None known at authoring. Recheck active ownership before editing.

## Outcome
Implemented provider-specific serial-tool controls and deep-capture regressions for
multi-turn correlation, empty tool lists, multi-call boundary behavior, usage mapping,
and transport/nontransport failure policy.

## Verification
- `uv run pytest -q tests/test_adapters_providers.py tests/test_adapters_isolation.py` — passed (15 tests).
- `uv sync --all-extras` — passed.
- `uv run ruff format --check .` — passed (174 files).
- `uv run ruff check .` — passed.
- `uv run mypy src` — passed (80 source files).
- `uv run pytest -q` — passed (444 tests).
- `git diff --check` — passed.
- Offline HTTP-free stubs only; no live provider request was run.
