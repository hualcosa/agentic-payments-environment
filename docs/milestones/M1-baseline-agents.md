# Milestone 1 — Baseline agents (sketch)

To be expanded into tickets once M0 exits. Written now so that M0 does not
paint M1 into a corner.

## Goal

Run real LLM agents on benchmark v0 through a provider-agnostic adapter and
publish the first measured results, with catastrophic failures counted per
code.

## Constraints inherited from M0

- The core package remains free of provider SDKs. Adapters live in
  `src/agentic_payments_env/adapters/` behind extras `[openai]` and
  `[anthropic]`; import errors are raised only when an adapter is used.
- Agents receive only `TaskPublic` and `Observation`s (REQ-CON-10).
- Traces must remain replayable: the LLM agent's `Action`s are ordinary
  actions; the model's raw response is stored in `Action.rationale`
  (truncated to 4 000 chars) and in a side file, never in the observation.

## Planned tickets

| id | deliverable |
|---|---|
| T1.01 | `adapters/base.py`: `ChatModel` protocol (`complete(messages, tools) -> ModelTurn`), `ModelTurn(tool_calls, text, usage)`; a `FakeChatModel` that replays scripted turns for tests |
| T1.02 | `adapters/openai_compat.py` (chat completions with tools; works for OpenAI, OpenRouter, vLLM, Ollama) and `adapters/anthropic.py` (Messages API with tools), each with retry on transport errors only |
| T1.03 | `agents/llm.py`: observation→message rendering (one user message per observation; tool results as tool-role messages), `TOOL_SPECS`→tool definitions, tool-call parsing with strict JSON, malformed → `INVALID_ARGUMENT` observation, forced `finish` when `max_steps - 1` is reached |
| T1.04 | `prompts/v1.md`: system prompt with an explicit safety and authorization contract (verify recipient, consent per transfer, never split to evade limits, check status after timeout, report truthfully with ids); prompt hash recorded in `runs/<id>/meta.json` |
| T1.05 | `cli bench --agent llm --model <id> --prompt v1` with per-step cost and latency in `meta.json`; concurrency across tasks with a fixed seed per task |
| T1.06 | Runs: ≥ 2 models × 3 seeds; `reports/v0/<model>-<prompt>.md`; README results table linking to them |
| T1.07 | First failure review: for every catastrophic code observed, one annotated example trace under `reports/v0/examples/` |

## Exit criteria

- Two committed reports with per-family safe-success, task-success and
  catastrophic rates and per-code counts.
- A `FakeChatModel` test proves the LLM agent loop handles: valid tool
  call, malformed JSON, unknown tool, text-only response, forced finish.
- No provider code imported by `import agentic_payments_env`.
