# Approved plan: reliable single-tool LLM turns

Owner approved the plan and requested task files for execution using Grok 4.6
in Cursor. Codex is preparing documentation, not implementing these tasks.
Decision: [ADR-0001](../decisions/ADR-0001-single-tool-turn.md).
Preparation task: `20260917-003-prepare-llm-tool-tasks`.

## Goal and evidence
Question: does every accepted model tool call correspond to exactly one executed
Action and, if another model request follows, exactly one correctly correlated
result? An offline reproduction advertised c1 and c2 but returned only c1's result.
Metrics: no partial batch execution, no orphan/duplicate result in subsequent
requests, correct AGENT_ERROR classification, replayable executed actions.
Evidence: offline regressions, captured provider payloads, runner/CLI artifacts
and unchanged oracle report. This is harness validity, not model-performance research.

## Frozen behavior
- At most one tool call per turn; zero calls retains existing text-to-DECLINED behavior.
- More than one call: fail the whole turn before creating any Action. Never pick
  the first, queue the rest, invent tool results or retry the model to repair it.
- A single call needs a non-whitespace string ID, preserved exactly. Invalid IDs
  fail before execution. Unknown tool names and malformed arguments retain existing
  handling; do not redesign these policies or enable strict schemas in this slice.
- Add LLMAgentProtocolError in agents/llm.py (no re-export required), with stable
  message prefixes LLM_PROTOCOL_MULTIPLE_TOOL_CALLS and LLM_PROTOCOL_INVALID_TOOL_CALL_ID.
  Existing runner catches it and records AGENT_ERROR/error; no new failure-taxonomy
  code, termination enum or environment contract. Error messages contain only safe
  reason/count/type metadata, not raw prompts, credentials or complete arguments.
- Preserve reported Usage before validation. Rejected turns must not be appended
  as accepted assistant tool calls or leave a pending ID. Execution failure is
  terminal through the existing runner; manual recovery requires reset.
- Each accepted nonterminal action yields one observation under its original ID
  on the next request, including ToolError observations. Terminal finish/budget
  termination does not require a fabricated follow-up model request/result.
- Reset removes prior conversation, pending correlation and usage. Forced finish
  remains local and must not trigger another model request.
- With tools, OpenAI-compatible requests use parallel_tool_calls=False; Anthropic
  uses tool_choice={"type":"auto","disable_parallel_tool_use":true}. Without tools,
  omit these tool controls. Keep the agent guard independently of provider compliance.
- Unsupported provider parameters fail visibly under existing error handling;
  no silent fallback or changed retry policy. Do not migrate APIs/SDKs or prompts.

## Task graph and ownership

```text
003 preparation (done before execution)
       ├── 004 agent + agent tests + normative decision note
       └── 005 provider adapters + adapter tests
                       ↓ both integrated
              006 end-to-end verification + shared closeout
```

004 and 005 have disjoint implementation files and depend only on 003, not on each
other. Default for one Cursor executor: 004 → 005 → 006 in this checkout. Optional
parallel execution requires isolated writer worktrees, explicit ownership and an
integration owner; never have concurrent writers sharing this checkout. Each task
is bounded, self-contained, independently executable and verifiable within its scope.

Current base: dae3b9598570d80d0e8a1f86aa8cb962e25b2d55, branch codex/sync-workspace.
There are important uncommitted harness/context files and the pytest pythonpath fix.
Do not reset, clean, discard, or branch from bare HEAD and assume those files came
along. Default is serial work here. Before opting into worktrees, preserve/materialize
all necessary uncommitted context/configuration in each worker and document its base;
obtain explicit permission for commits, including a shared claim commit when required.
No commits, pushes or paid requests are authorized by these task files.

Tasks own only their declared source/test/doc files plus their own lifecycle record.
004/005 record local progress in their task, not shared context/plan/other task files;
006 owns combined context/handoff. Do not mark a worker done while its accepted code
exists only in an auxiliary checkout: integrate first, then record evidence. Check
actual claims before writing; do not block solely on an open Claude process.

## Verification and boundaries
Write negative regressions before/with fixes; use test-local recording models and
HTTP-free SDK stubs. Never infer provider conformance from FakeChatModel parsing alone.
No real keys, network, new dependencies, provider API migration, run-budget framework,
latency implementation, v1 CLI expansion, experiment or training work in this slice.
Keep core imports SDK-free and TaskHidden away from agent inputs (REQ-CON-10).
Run the full AGENTS.md gate per task; 006 additionally runs offline oracle and replay.
All final evidence must refer to the integrated checkout, not merely worker results.

## Sources verified during planning
- https://developers.openai.com/api/docs/guides/function-calling — parallel_tool_calls=False.
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/parallel-tool-use — auto + disable_parallel_tool_use.
Spec references: docs/milestones/M1-baseline-agents.md T1.01–T1.03;
docs/03-contracts.md §9; docs/04-tools-and-actions.md REQ-TOOL-08;
docs/06-environment-runtime.md runner/replay; docs/10-testing-strategy.md;
docs/12-decisions.md. Existing spec remains normative; 004 records the clarification.
