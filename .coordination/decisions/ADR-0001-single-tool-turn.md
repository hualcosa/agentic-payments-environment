---
id: ADR-0001
title: At most one tool call per LLM turn
status: accepted
decided_at: 2026-09-17T11:19:17Z
task_id: 20260917-003-prepare-llm-tool-tasks
supersedes:
superseded_by:
---

# Context
Environment.step accepts one Action. Current LLMAgent advertises every call in a
model response but executes only the first, leaving an orphan call in the transcript.
Owner explicitly selected one call per turn instead of a sequential queue.

# Decision
Request serial tool use in both adapters and independently reject unexpected batches
in LLMAgent before any action. Require a valid correlation ID for an accepted call.
Record the returned usage and surface a stable protocol exception via existing
AGENT_ERROR termination. Preserve all prior executed actions and their audit history.
See ../plans/2026-09-17-llm-tool-protocol.md for the complete approved contract.
Task 004 appends the matching clarification to normative docs/12-decisions.md.

# Consequences
No partial batch or fabricated result; no environment API/schema changes. An
incompatible endpoint can fail explicitly. Offline tests establish integration
behavior, not live model correctness. Failed protocol turns remain observable.

# Alternatives considered
- Sequential queue: rejected by owner; requires additional state and dependency rules.
- Execute first and ignore remainder: rejected; inconsistent transcript and hidden work loss.
- Provider flags alone: insufficient; retain independent validation at the agent boundary.
