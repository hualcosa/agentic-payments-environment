"""Command-line interface. REQ-ENV-17, 06 §10."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from agentic_payments_env.agents.presets import NAMES, build
from agentic_payments_env.benchmark.loader import export_tasks
from agentic_payments_env.benchmark.runner import _drive, run_benchmark
from agentic_payments_env.benchmark.v0 import all_tasks, load_task
from agentic_payments_env.contracts.grading import EpisodeResult
from agentic_payments_env.contracts.tasks import TaskSpec
from agentic_payments_env.contracts.trace import EpisodeTrace
from agentic_payments_env.graders import grade_episode
from agentic_payments_env.replay import replay


def _tasks_for(benchmark: str) -> list[TaskSpec]:
    if benchmark != "v0":
        raise SystemExit(f"unknown benchmark {benchmark!r}")
    return all_tasks()


def _cmd_list_tasks(args: argparse.Namespace) -> int:
    for task in _tasks_for(args.benchmark):
        print(f"{task.task_id}\t{task.family.value}\t{task.title}")
    return 0


def _cmd_show_task(args: argparse.Namespace) -> int:
    task = load_task(args.task_id)
    payload: dict[str, object] = {
        "task_id": task.task_id,
        "family": task.family.value,
        "title": task.title,
        "public": task.public.model_dump(mode="json"),
        "world": {
            "start_time": task.world.start_time.isoformat(),
            "principal_customer_id": task.world.principal_customer_id,
            "principal_account_id": task.world.principal_account_id,
            "n_accounts": len(task.world.accounts),
            "n_beneficiaries": len(task.world.beneficiaries),
            "n_directory": len(task.world.pix_directory),
        },
    }
    if args.hidden:
        payload["hidden"] = task.hidden.model_dump(mode="json")
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def _write_episode(
    out: Path, task_id: str, seed: int, trace: EpisodeTrace, result: EpisodeResult
) -> None:
    slug = task_id.replace("/", "_")
    folder = out / slug
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"seed-{seed}.trace.json").write_text(
        json.dumps(trace.model_dump(mode="json"), indent=2, sort_keys=True, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    (folder / f"seed-{seed}.result.json").write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )


def _cmd_run(args: argparse.Namespace) -> int:
    task = load_task(args.task)
    agent = build(args.agent, task)
    env, trace = _drive(task, agent, args.seed, strict=True)
    result = grade_episode(task, trace, env.state)
    if args.out:
        _write_episode(Path(args.out), task.task_id, args.seed, trace, result)
    print(
        json.dumps(
            {
                "task_id": result.task_id,
                "agent": result.agent_name,
                "termination": result.termination.value,
                "declared": None
                if result.declared_outcome is None
                else result.declared_outcome.value,
                "task_success": result.task_success,
                "safe_success": result.safe_success,
                "catastrophic_codes": result.catastrophic_codes,
                "steps_used": result.steps_used,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def _cmd_bench(args: argparse.Namespace) -> int:
    seeds = [int(part) for part in str(args.seeds).split(",") if part != ""]
    out = Path(args.out)
    report = run_benchmark(
        _tasks_for(args.benchmark),
        lambda task: build(args.agent, task),
        seeds,
        out_dir=out,
        benchmark_id=args.benchmark,
    )
    print(
        json.dumps(
            {
                "agent": report.agent_name,
                "episodes": len(report.episodes),
                "safe_success_rate": next(
                    item.safe_success_rate for item in report.summaries if item.family is None
                ),
            },
            indent=2,
        )
    )
    return 0


def _cmd_replay(args: argparse.Namespace) -> int:
    path = Path(args.trace)
    trace = EpisodeTrace.model_validate(json.loads(path.read_text(encoding="utf-8")))
    task = load_task(trace.task_id)
    result = replay(task, trace)
    print(json.dumps(result.model_dump(mode="json"), indent=2))
    return 0 if result.matches else 1


def _cmd_export(args: argparse.Namespace) -> int:
    export_tasks(args.benchmark, Path(args.out))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse tree for the six 06 §10 commands."""
    parser = argparse.ArgumentParser(prog="apenv")
    sub = parser.add_subparsers(dest="command", required=True)

    list_p = sub.add_parser("list-tasks")
    list_p.add_argument("--benchmark", default="v0")
    list_p.set_defaults(func=_cmd_list_tasks)

    show = sub.add_parser("show-task")
    show.add_argument("task_id")
    show.add_argument("--hidden", action="store_true")
    show.set_defaults(func=_cmd_show_task)

    run = sub.add_parser("run")
    run.add_argument("--task", required=True)
    run.add_argument("--agent", required=True, choices=list(NAMES))
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--out")
    run.set_defaults(func=_cmd_run)

    bench = sub.add_parser("bench")
    bench.add_argument("--benchmark", default="v0")
    bench.add_argument("--agent", required=True, choices=list(NAMES))
    bench.add_argument("--seeds", default="0")
    bench.add_argument("--out", required=True)
    bench.set_defaults(func=_cmd_bench)

    rep = sub.add_parser("replay")
    rep.add_argument("trace")
    rep.set_defaults(func=_cmd_replay)

    exp = sub.add_parser("export-tasks")
    exp.add_argument("--benchmark", default="v0")
    exp.add_argument("--out", required=True)
    exp.set_defaults(func=_cmd_export)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. 06 §10."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
