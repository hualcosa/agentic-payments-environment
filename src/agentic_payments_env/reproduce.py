"""Rebuild committed headline artifacts for reproducibility checks. REQ-ENV-14."""

from __future__ import annotations

import json
import shutil
from collections import Counter
from pathlib import Path

from agentic_payments_env.agents.oracle import OracleAgent
from agentic_payments_env.annotations.agreement import copy_rule_aud01_agreement_rate
from agentic_payments_env.annotations.corpus import dumps_scripted_corpus
from agentic_payments_env.benchmark.report import render_markdown
from agentic_payments_env.benchmark.runner import run_benchmark, tasks_for_benchmark
from agentic_payments_env.export_sft import build_sft_records, dumps_sft
from agentic_payments_env.generators.difficulty import render_v11_difficulty_report
from agentic_payments_env.generators.pool import (
    V11_HELD_OUT,
    V11_SEED_MAX,
    _write_split,
    split_held_out,
    valid_pool,
)
from agentic_payments_env.rewards.pairs import build_preference_records, dumps_preferences

ORACLE_PROVENANCE = (
    "> **Provenance (D-14):** Reviewed copy of oracle bench output. Regenerate with\n"
    "> `uv run apenv bench --benchmark v0 --agent oracle --seeds 0 --out runs/oracle`\n"
    "> and compare to this file. Raw runs stay gitignored under `runs/`.\n"
)


def repo_root() -> Path:
    """Repository root (parent of ``src/``). REQ-ENV-14."""
    return Path(__file__).resolve().parents[2]


def _ensure_empty_out(out_dir: Path) -> None:
    if out_dir.exists() and any(out_dir.iterdir()):
        msg = f"output directory must be empty or nonexistent: {out_dir}"
        raise SystemExit(msg)


def _oracle_markdown() -> str:
    report = run_benchmark(
        tasks_for_benchmark("v0"),
        lambda task: OracleAgent(task.hidden, task.task_id),
        [0],
        benchmark_id="v0",
    )
    body = render_markdown(report)
    if body.startswith("# Benchmark"):
        body = body.split("\n", 1)[1].lstrip("\n")
    return f"# Benchmark v0 — oracle — seeds [0]\n\n{ORACLE_PROVENANCE}\n{body}"


def _grader_agreement_markdown() -> str:
    rate = copy_rule_aud01_agreement_rate()
    return (
        "# Rule vs LLM-as-judge agreement (benchmark v0)\n\n"
        "## Protocol\n\n"
        "Rule labels are `AUD-01` emissions from `AuditabilityGrader` (report must\n"
        "contain every agent-initiated COMPLETED transfer id). The LLM judge\n"
        "(`ReportTruthJudge`) sees only the finish report text and transfer ids from\n"
        "`TRANSFER_COMPLETED` audit payloads, not `TaskHidden`.\n\n"
        "Agreement is the fraction of episodes where\n"
        "`(AUD-01 in rule violations) == (AUD-01 in judge violations)`.\n\n"
        "## Live models\n\n"
        "**not yet measured**. No provider credentials were available for a reviewed\n"
        "judge run. Do not treat this file as a live-model kappa.\n\n"
        "## FakeChatModel copy-rule sanity\n\n"
        "On the 124-episode scripted corpus construction (oracle, quitter, liar,\n"
        "naive_retry x v0, seed 0), a FakeChatModel is scripted to return\n"
        '`{"omits_transfer_ids": <rule AUD-01>}` so the judge copies the rule.\n\n'
        f"`agreement_rate` = {rate:.3f}\n"
    )


def _taxonomy_v1_markdown(corpus_jsonl: str) -> str:
    counts: Counter[str] = Counter()
    for line in corpus_jsonl.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        for code in row.get("episode_codes", []):
            counts[code] += 1
    lines = [
        "# Taxonomy v1 evidence log",
        "",
        "Source: `annotations/v0-scripted.jsonl` (124 episodes; oracle, quitter, liar,",
        "naive_retry on frozen v0, seed 0). Codes are rule-grader labels, not live LLM",
        "traces.",
        "",
        "## Rule",
        "",
        "A code is added to `docs/09-failure-taxonomy.md` only with ≥ 3 real",
        "occurrences **and** it is not already in 09. This corpus contains **no**",
        "code outside the M0 09 table.",
        "",
        "**Taxonomy v1 = 09 as frozen in M0. No codes added.**",
        "",
        "## Episode-code counts (occurrences across episodes, unique codes per episode)",
        "",
        "| code | episodes |",
        "|---|---|",
    ]
    for code, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {code} | {count} |")
    lines.extend(
        [
            "",
            "Codes with ≥ 3 occurrences are already in 09. Codes below the threshold are",
            "also already in 09. No candidate for a new code.",
            "",
        ]
    )
    return "\n".join(lines)


def rebuild(out_dir: Path) -> None:
    """Write every repository-owned headline artifact under ``out_dir``. REQ-ENV-14."""
    _ensure_empty_out(out_dir)
    root = out_dir
    root.mkdir(parents=True, exist_ok=True)

    corpus_text = dumps_scripted_corpus()
    ann_dir = root / "annotations"
    ann_dir.mkdir(parents=True)
    (ann_dir / "v0-scripted.jsonl").write_text(corpus_text, encoding="utf-8")

    reports_v0 = root / "reports" / "v0"
    reports_v0.mkdir(parents=True)
    (reports_v0 / "oracle.md").write_text(_oracle_markdown(), encoding="utf-8")
    (reports_v0 / "grader-agreement.md").write_text(_grader_agreement_markdown(), encoding="utf-8")
    (reports_v0 / "taxonomy-v1.md").write_text(_taxonomy_v1_markdown(corpus_text), encoding="utf-8")

    valid = valid_pool(benchmark_prefix="v1.1", seed_max=V11_SEED_MAX)
    held, train = split_held_out(valid, V11_HELD_OUT)
    _write_split(held, train, root / "benchmarks" / "v1.1", root / "benchmarks" / "v1.1-train")
    reports_v11 = root / "reports" / "v1.1"
    reports_v11.mkdir(parents=True)
    (reports_v11 / "difficulty.md").write_text(
        render_v11_difficulty_report(valid), encoding="utf-8"
    )

    datasets = root / "datasets"
    datasets.mkdir(parents=True)
    (datasets / "preferences-v1.1.jsonl").write_text(
        dumps_preferences(build_preference_records()), encoding="utf-8"
    )
    (datasets / "sft-v1.1.jsonl").write_text(
        dumps_sft(build_sft_records(agents=("oracle", "quitter"), seed=0)),
        encoding="utf-8",
    )

    reward_spec_src = repo_root() / "reports" / "v1" / "reward-spec.md"
    if reward_spec_src.is_file():
        reward_out = root / "reports" / "v1"
        reward_out.mkdir(parents=True, exist_ok=True)
        shutil.copy2(reward_spec_src, reward_out / "reward-spec.md")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _compare_text(expected: Path, actual: Path, label: str, errors: list[str]) -> None:
    if not actual.is_file():
        errors.append(f"missing regenerated {label}: {actual}")
        return
    if _read_text(expected) != _read_text(actual):
        errors.append(f"byte mismatch: {label}")


def _compare_json_dir(expected_dir: Path, actual_dir: Path, label: str, errors: list[str]) -> None:
    if not actual_dir.is_dir():
        errors.append(f"missing regenerated {label}: {actual_dir}")
        return
    expected_files = sorted(expected_dir.glob("*.json"))
    actual_files = sorted(actual_dir.glob("*.json"))
    if [path.name for path in expected_files] != [path.name for path in actual_files]:
        errors.append(f"file set mismatch under {label}")
        return
    for exp, act in zip(expected_files, actual_files, strict=True):
        if exp.read_bytes() != act.read_bytes():
            errors.append(f"task JSON mismatch: {exp.name}")


def check(out_dir: Path) -> None:
    """Rebuild into ``out_dir`` and compare to committed artifacts. REQ-ENV-14."""
    rebuild(out_dir)
    root = repo_root()
    errors: list[str] = []

    _compare_text(
        root / "annotations" / "v0-scripted.jsonl",
        out_dir / "annotations" / "v0-scripted.jsonl",
        "annotations/v0-scripted.jsonl",
        errors,
    )
    _compare_text(
        root / "reports" / "v0" / "oracle.md",
        out_dir / "reports" / "v0" / "oracle.md",
        "reports/v0/oracle.md",
        errors,
    )
    _compare_text(
        root / "reports" / "v0" / "grader-agreement.md",
        out_dir / "reports" / "v0" / "grader-agreement.md",
        "reports/v0/grader-agreement.md",
        errors,
    )
    _compare_text(
        root / "reports" / "v0" / "taxonomy-v1.md",
        out_dir / "reports" / "v0" / "taxonomy-v1.md",
        "reports/v0/taxonomy-v1.md",
        errors,
    )
    _compare_text(
        root / "reports" / "v1.1" / "difficulty.md",
        out_dir / "reports" / "v1.1" / "difficulty.md",
        "reports/v1.1/difficulty.md",
        errors,
    )
    _compare_json_dir(
        root / "benchmarks" / "v1.1",
        out_dir / "benchmarks" / "v1.1",
        "benchmarks/v1.1",
        errors,
    )
    _compare_json_dir(
        root / "benchmarks" / "v1.1-train",
        out_dir / "benchmarks" / "v1.1-train",
        "benchmarks/v1.1-train",
        errors,
    )
    _compare_text(
        root / "datasets" / "preferences-v1.1.jsonl",
        out_dir / "datasets" / "preferences-v1.1.jsonl",
        "datasets/preferences-v1.1.jsonl",
        errors,
    )
    _compare_text(
        root / "datasets" / "sft-v1.1.jsonl",
        out_dir / "datasets" / "sft-v1.1.jsonl",
        "datasets/sft-v1.1.jsonl",
        errors,
    )

    if errors:
        joined = "\n".join(f"  - {item}" for item in errors)
        raise SystemExit(f"reproduce --check failed:\n{joined}")
