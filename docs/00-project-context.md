# Shared project context — Frontier Engineering

Updated: 2026-09-17. Owner-approved context synchronization for all harnesses.

## Purpose and authority

This document owns the project's strategic motivation and prioritization lens.
It distills the owner's ChatGPT export
`codex_context_rotina_frontier_track_2026-09-17.md`, supplied on 2026-09-17.
It is self-contained: no harness needs access to the original Downloads file.
Personal schedules and unrelated projects are intentionally not copied here.

Read this alongside `AGENTS.md`, `01-vision-and-scope.md` and the relevant
technical specification. It reinforces the existing research purpose; it does
not rewrite contracts, invariants, approved tickets or milestone exit criteria.
The conceptual progression below is not a statement of implementation status.
If a proposed strategic change conflicts with a technical requirement, surface
the conflict and obtain a decision rather than silently changing the spec.

## Why this project exists

The owner is building toward frontier agent research / research engineering
over an approximately 12–24 month horizon from September 2026. Existing
strength in Agentic AI, architecture, production systems and reliability is
the starting advantage, not the final destination of this project.

The capability to develop is: **measure, explain and modify model/agent
behavior through reproducible experiments**.

The payments environment is a potential flagship research project, or central
infrastructure for that flagship. Payments supply a concrete domain in which
authorization, correctness, uncertainty, recovery and safety can be measured.
The goal is not another enterprise banking application or a generic framework.
Keep this repository independent of TRAIL and real banking integrations as
specified in `01-vision-and-scope.md`.

Success is not "implemented an environment". It is "used the environment to
discover something verifiable about agent behavior, applied an intervention,
and measured its effects, limitations and regressions". Negative results are
useful evidence when the experiment is valid; improvement must not be assumed.

## The unit of progress: a closed experimental loop

Environment and task distribution → baseline → evals/graders → failure
taxonomy → targeted cases/data → feedback/reward → intervention → held-out
re-evaluation → technical write-up → next hypothesis.

Prefer small, complete loops over a large architecture without results. Not
every loop needs every stage. The capability progression is:

1. Reproducible environments and reliable evals/graders.
2. Failure analysis and systematic hard-case/synthetic/curriculum generation.
3. Feedback/reward design, including misspecification and gaming analysis.
4. Meaningful optimization and eventually justified post-training work.
5. Re-evaluation of generalization, robustness, variance and regressions.

An initial intervention may be a prompt/policy change, search, rejection
sampling or supervised learning. RL/post-training is a growing capability
target, not a required first step or a checkbox. Over time, avoid limiting the
flagship to prompting and orchestration alone. The environment supplies
transitions and observations; a learning/optimization process changes the
agent. Do not conflate evaluation with training.

## How to choose work

Prioritize, in order:

1. Remove a blocker for a current, explicitly identified experiment.
2. Improve measurement/eval validity and reliability.
3. Close an experimental loop.
4. Produce evidence that can be reviewed and reproduced.
5. Extend capability into targeted data, feedback/reward and optimization.
6. Improve ergonomics/reliability needed for the above.
7. Add framework sophistication only when experimentally justified.

For a proposed feature or refactor, explain: which question it unlocks, what
metric measures the effect, what artifact provides evidence, and why this is
the smallest useful change. If no experiment is active, first inspect current
code and run artifacts; propose a bounded experiment rather than inventing
status or automatically implementing this progression.

Avoid disconnected demos, feature/LOC-based progress, generic abstractions
without a hypothesis, infrastructure for its own sake, and RL solely to claim
RL experience. Papers and reproductions should unblock a concrete question.

## Evidence standard

- Define hypothesis, task distribution, baseline, intervention, metrics and
  success criteria before interpreting results.
- Validate graders and distinguish agent failures from environment, task,
  context and grading defects. Passing software tests alone is not scientific
  validation.
- Separate development/training cases from held-out evaluation. Use matched
  comparisons, repeat runs where needed, and report variance/uncertainty.
- Measure safe task completion together with catastrophic errors, over-refusal,
  efficiency and regressions. Reward increases alone do not prove improvement.
- Record model/version, prompts/policies, configuration, seeds where applicable,
  environment revision, task set, grader version, traces and metrics. A seeded
  environment does not imply deterministic model inference.
- Inspect reward hacking, distribution shifts and limits of generalization.
  Use ablations/controls before making causal claims.
- Keep measured facts, hypotheses, interpretations and plans distinct. Never
  fabricate results; follow the repository's artifact/report requirements.

A useful experiment record contains: hypothesis, setup, metric, result,
surprise, limitations and next experiment.

## Desired outputs and scope boundaries

Accumulate depth in one flagship rather than proliferating projects. Desired
outputs over time are a flagship repository, a benchmark/eval release, 2–4
technical memos and, if evidence warrants it, a paper or technical report.
These are aspirations, not completed deliverables or automatic work orders.

Public writing and technical outreach should be downstream of real results:
experiment → reproducible artifact → technical memo → concise public insight.
The strategic value is capability, evidence, research judgment and informed
technical feedback, not publishing frequency or software sophistication.

Keep this context project-scoped. Do not alter other projects, personal
routines or global harness settings because the source export mentions them.
Do not spend, provision, publish, commit or push without explicit authorization.

## Keeping harnesses aligned

- Codex reads the repository `AGENTS.md`, which requires this document.
- Claude Code imports `AGENTS.md` and this document through `CLAUDE.md`.
- Cursor's always-applied project rule points to the same two sources.
- Engram stores the durable strategic summary and significant decisions;
  repository files keep the context usable when MCP is unavailable.

Update this canonical document rather than copying evolving strategy into
three independent rule sets. Keep adapters thin and reconcile substantive
changes with Engram. Check the actual checkout before reporting project status;
the existence of this context is not evidence that a milestone is complete.
