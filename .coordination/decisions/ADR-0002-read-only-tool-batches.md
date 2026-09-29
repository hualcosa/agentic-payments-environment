---
id: ADR-0002
title: Read-only tool calls may be batched; state changes stay alone
status: accepted
decided_at: 2026-09-29T13:43:31Z
task_id: 20260929-001-read-only-tool-batches
supersedes: ADR-0001
superseded_by:
---

# Context
The first R1 smoke (2026-09-29, gpt-6-luna) ended all four episodes on the
first turns because the model batched 2–3 read-only lookups
(`get_customer_profile`, `list_beneficiaries`, `get_account_balance`).
ADR-0001 rejected every multi-call turn, which measured format compliance, not
payment safety. What the environment must measure is that a state-changing
action is decided after observing what it depends on.

# Decision
LLMAgent accepts a multi-call turn only when every call names a read-only tool
(`READ_ONLY_TOOLS` in `agents/llm.py`) and every id is a unique non-blank
string. Accepted batches are queued and executed as consecutive environment
steps in model order, each answered by its own correlated tool result; no
model request happens until the queue is drained. A batch containing any
state-changing, user-interaction (`ask_user`), `finish` or unknown tool is
rejected atomically as before (`LLM_PROTOCOL_MULTIPLE_TOOL_CALLS`). Adapters
stop forcing serial tool use; provider defaults apply. Each queued call costs one
step against `max_steps` and gets zero token usage in `meta.json` (usage stays
on the step whose completion produced the batch).

# Consequences
Natural parallel lookups are no longer protocol failures. Environment API,
trace/result schemas and graders are unchanged: batching is invisible below the
agent boundary except as consecutive steps. Runs before this ADR are not
comparable on protocol-error counts.

# Alternatives considered
- Keep ADR-0001 and force `parallel_tool_calls=False`: measures format
  compliance and depends on every endpoint honoring the flag.
- Allow any batch: a transfer could be decided before its prerequisite reads
  are observed, hiding exactly the authorization failures under study.
- Prompt instruction "one tool per turn": creates prompt v2 and confounds R1.
