"""Command-line interface. REQ-ENV-17, 06 §10."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable, Sequence
from pathlib import Path

from agentic_payments_env.adapters.base import ChatModel, FakeChatModel, ModelTurn
from agentic_payments_env.agents.base import Agent
from agentic_payments_env.agents.llm import LLMAgent
from agentic_payments_env.agents.presets import NAMES, build
from agentic_payments_env.annotations.from_grade import from_episode
from agentic_payments_env.annotations.schema import dumps_jsonl
from agentic_payments_env.benchmark.loader import (
    BENCHMARK_IDS,
    all_tasks_for,
    export_tasks,
    load_task,
)
from agentic_payments_env.benchmark.runner import (
    _drive,
    _episode_turn_log,
    _usage_steps,
    run_benchmark,
)
from agentic_payments_env.contracts.grading import EpisodeResult
from agentic_payments_env.contracts.tasks import TaskSpec
from agentic_payments_env.contracts.trace import EpisodeTrace
from agentic_payments_env.export_sft import export_sft, export_sft_benchmark
from agentic_payments_env.graders import grade_episode
from agentic_payments_env.prompts import load_prompt
from agentic_payments_env.replay import replay
from agentic_payments_env.reproduce import check as reproduce_check
from agentic_payments_env.reproduce import rebuild as reproduce_rebuild
from agentic_payments_env.rewards.pairs import export_preferences

_LLM_PROVIDERS = ("openai", "anthropic", "fake")


def _tasks_for(benchmark: str) -> list[TaskSpec]:
    if benchmark not in BENCHMARK_IDS:
        raise SystemExit(f"unknown benchmark {benchmark!r}")
    return all_tasks_for(benchmark)


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


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _make_chat_model(args: argparse.Namespace) -> ChatModel:
    provider = str(args.provider)
    model_id = str(args.model)
    if provider == "fake":
        return FakeChatModel(
            [ModelTurn(tool_calls=[], text="declined")],
            model_id=model_id,
        )
    if provider == "openai":
        from agentic_payments_env.adapters.openai_compat import OpenAICompatChatModel

        api_key = str(args.api_key or os.environ.get("OPENAI_API_KEY", ""))
        base_url = str(args.base_url) if args.base_url else None
        return OpenAICompatChatModel(model_id, base_url, api_key)
    if provider == "anthropic":
        from agentic_payments_env.adapters.anthropic import AnthropicChatModel

        api_key = str(args.api_key or os.environ.get("ANTHROPIC_API_KEY", ""))
        return AnthropicChatModel(model_id, api_key)
    raise SystemExit(f"unknown provider {provider!r}")


def _agent_factory(
    args: argparse.Namespace,
) -> tuple[Callable[[TaskSpec], Agent], dict[str, object] | None]:
    if args.agent != "llm":
        if args.agent not in NAMES:
            raise SystemExit(f"unknown agent {args.agent!r}")
        return (lambda task: build(args.agent, task), None)
    if not args.model:
        raise SystemExit("--model is required for --agent llm")
    if args.provider not in _LLM_PROVIDERS:
        raise SystemExit(f"unknown provider {args.provider!r}")
    prompt_id = str(args.prompt)
    text, digest = load_prompt(prompt_id)
    meta: dict[str, object] = {
        "prompt_id": prompt_id,
        "prompt_sha256": digest,
        "model_id": str(args.model),
        "provider": str(args.provider),
    }

    def factory(_task: TaskSpec) -> Agent:
        model = _make_chat_model(args)
        return LLMAgent(model, system_prompt=text, prompt_id=prompt_id)

    return factory, meta


def _cmd_run(args: argparse.Namespace) -> int:
    task = load_task(args.task)
    factory, meta = _agent_factory(args)
    agent = factory(task)
    env, trace = _drive(task, agent, args.seed, strict=True)
    result = grade_episode(task, trace, env.state)
    if args.out:
        out = Path(args.out)
        _write_episode(out, task.task_id, args.seed, trace, result)
        if meta is not None:
            payload = dict(meta)
            payload["episodes"] = [
                {
                    "task_id": task.task_id,
                    "seed": args.seed,
                    "steps": _usage_steps(agent, len(trace.steps)),
                }
            ]
            _write_json(out / "meta.json", payload)
        turn_log = _episode_turn_log(agent, task.task_id, args.seed)
        if turn_log is not None:
            _write_json(out / "turns.json", {"schema_version": "0.1", "episodes": [turn_log]})
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
    tasks = _tasks_for(args.benchmark)
    if args.task:
        tasks = [item for item in tasks if item.task_id == args.task]
        if not tasks:
            raise SystemExit(f"unknown task {args.task!r}")
    factory, meta = _agent_factory(args)
    report = run_benchmark(
        tasks,
        factory,
        seeds,
        out_dir=out,
        benchmark_id=args.benchmark,
        meta=meta,
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


def _cmd_annotate_trace(args: argparse.Namespace) -> int:
    trace = EpisodeTrace.model_validate(json.loads(Path(args.trace).read_text(encoding="utf-8")))
    result = EpisodeResult.model_validate(json.loads(Path(args.result).read_text(encoding="utf-8")))
    task = load_task(trace.task_id)
    record = from_episode(task, trace, result)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as handle:
        handle.write(dumps_jsonl([record]))
    return 0


def _cmd_export_sft(args: argparse.Namespace) -> int:
    out = Path(args.out)
    if args.benchmark:
        export_sft_benchmark(out, agents=tuple(args.agents.split(",")), seed=args.seed)
    elif args.task:
        export_sft([str(args.task)], out, seed=args.seed)
    else:
        raise SystemExit("export-sft requires --task or --benchmark")
    return 0


def _cmd_export_preferences(args: argparse.Namespace) -> int:
    export_preferences(Path(args.out))
    return 0


def _cmd_reproduce(args: argparse.Namespace) -> int:
    out = Path(args.out)
    if args.check:
        reproduce_check(out)
    else:
        reproduce_rebuild(out)
    return 0


def _add_llm_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model", default=None, help="required when --agent llm")
    parser.add_argument("--prompt", default="v1")
    parser.add_argument("--provider", default="fake", choices=list(_LLM_PROVIDERS))
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key", default=None)


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse tree for the six 06 §10 commands. REQ-ENV-14."""
    parser = argparse.ArgumentParser(prog="apenv")
    sub = parser.add_subparsers(dest="command", required=True)

    list_p = sub.add_parser("list-tasks")
    list_p.add_argument("--benchmark", default="v0", choices=list(BENCHMARK_IDS))
    list_p.set_defaults(func=_cmd_list_tasks)

    show = sub.add_parser("show-task")
    show.add_argument("task_id")
    show.add_argument("--hidden", action="store_true")
    show.set_defaults(func=_cmd_show_task)

    run = sub.add_parser("run")
    run.add_argument("--task", required=True)
    run.add_argument("--agent", required=True)
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--out")
    _add_llm_flags(run)
    run.set_defaults(func=_cmd_run)

    bench = sub.add_parser("bench")
    bench.add_argument("--benchmark", default="v0", choices=list(BENCHMARK_IDS))
    bench.add_argument("--agent", required=True)
    bench.add_argument("--seeds", default="0")
    bench.add_argument("--out", required=True)
    bench.add_argument("--task", default=None, help="optional single task id")
    _add_llm_flags(bench)
    bench.set_defaults(func=_cmd_bench)

    rep = sub.add_parser("replay")
    rep.add_argument("trace")
    rep.set_defaults(func=_cmd_replay)

    exp = sub.add_parser("export-tasks")
    exp.add_argument("--benchmark", default="v0", choices=list(BENCHMARK_IDS))
    exp.add_argument("--out", required=True)
    exp.set_defaults(func=_cmd_export)

    ann = sub.add_parser("annotate-trace")
    ann.add_argument("--trace", required=True)
    ann.add_argument("--result", required=True)
    ann.add_argument("--out", required=True)
    ann.set_defaults(func=_cmd_annotate_trace)

    sft = sub.add_parser("export-sft")
    sft.add_argument("--task", default=None)
    sft.add_argument("--benchmark", default=None, choices=["training"])
    sft.add_argument("--agents", default="oracle,quitter")
    sft.add_argument("--seed", type=int, default=0)
    sft.add_argument("--out", required=True)
    sft.set_defaults(func=_cmd_export_sft)

    pref = sub.add_parser("export-preferences")
    pref.add_argument("--out", required=True)
    pref.set_defaults(func=_cmd_export_preferences)

    repro = sub.add_parser("reproduce")
    repro.add_argument("--out", required=True, help="empty or nonexistent output directory")
    repro.add_argument(
        "--check",
        action="store_true",
        help="rebuild into --out and compare to committed artifacts",
    )
    repro.set_defaults(func=_cmd_reproduce)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. 06 §10. REQ-ENV-14."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
