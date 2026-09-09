"""Episode and benchmark runner. REQ-ENV-17, REQ-ENV-18."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from pathlib import Path

from agentic_payments_env.agents.base import Agent
from agentic_payments_env.benchmark.report import render_markdown, summarize
from agentic_payments_env.contracts.common import TerminationReason
from agentic_payments_env.contracts.grading import BenchmarkReport
from agentic_payments_env.contracts.tasks import TaskSpec
from agentic_payments_env.contracts.trace import EpisodeTrace, Step
from agentic_payments_env.environment import PaymentsEnvironment
from agentic_payments_env.graders import DEFAULT_GRADERS, grade_episode
from agentic_payments_env.graders.base import Grader


def _drive(
    task: TaskSpec, agent: Agent, seed: int = 0, *, strict: bool = True
) -> tuple[PaymentsEnvironment, EpisodeTrace]:
    env = PaymentsEnvironment(task, seed, strict=strict)
    obs = env.reset()
    agent.reset(task.public, obs)
    history: list[Step] = []
    while not env.done:
        try:
            action = agent.act(history, obs)
        except Exception as exc:  # agent bugs are the agent's failure, not the env's
            return env, env.trace(
                agent.name, termination=TerminationReason.AGENT_ERROR, error=str(exc)
            )
        obs, done = env.step(action)
        del done
        history = list(env.steps)
    return env, env.trace(agent.name)


def run_episode(
    task: TaskSpec, agent: Agent, seed: int = 0, *, strict: bool = True
) -> EpisodeTrace:
    """Reset, loop ``agent.act`` until the environment is done. REQ-ENV-18."""
    _env, trace = _drive(task, agent, seed, strict=strict)
    return trace


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def run_benchmark(
    tasks: Sequence[TaskSpec],
    agent_factory: Callable[[TaskSpec], Agent],
    seeds: Sequence[int],
    graders: Sequence[Grader] = DEFAULT_GRADERS,
    out_dir: Path | None = None,
    *,
    benchmark_id: str = "v0",
) -> BenchmarkReport:
    """Run every task-seed pair, grade, and write traces/results. REQ-ENV-17."""
    episodes = []
    agent_name = "unknown"
    for task in tasks:
        for seed in seeds:
            agent = agent_factory(task)
            agent_name = agent.name
            env, trace = _drive(task, agent, seed, strict=True)
            result = grade_episode(task, trace, env.state, graders)
            episodes.append(result)
            if out_dir is not None:
                slug = task.task_id.replace("/", "_")
                folder = out_dir / slug
                _write_json(folder / f"seed-{seed}.trace.json", trace.model_dump(mode="json"))
                _write_json(folder / f"seed-{seed}.result.json", result.model_dump(mode="json"))
    report = BenchmarkReport(
        benchmark_id=benchmark_id,
        agent_name=agent_name,
        seeds=list(seeds),
        episodes=episodes,
        summaries=summarize(episodes),
    )
    if out_dir is not None:
        _write_json(out_dir / "report.json", report.model_dump(mode="json"))
        (out_dir / "report.md").write_text(render_markdown(report), encoding="utf-8")
    return report
