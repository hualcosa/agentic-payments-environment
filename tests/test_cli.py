"""CLI smoke tests. 06 §10."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_payments_env.benchmark.loader import BENCHMARK_IDS, all_tasks_for
from agentic_payments_env.cli import main


@pytest.mark.parametrize("benchmark", BENCHMARK_IDS)
def test_list_tasks_for_each_benchmark(benchmark: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list-tasks", "--benchmark", benchmark]) == 0
    out = capsys.readouterr().out
    sample = all_tasks_for(benchmark)[0]
    assert sample.task_id in out
    assert sample.family.value in out


def test_list_tasks_default_v0(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list-tasks"]) == 0
    out = capsys.readouterr().out
    assert "v0/rt-001" in out
    assert "ROUTINE_TRANSFER" in out


@pytest.mark.parametrize("benchmark", BENCHMARK_IDS)
def test_export_tasks_for_each_benchmark(tmp_path: Path, benchmark: str) -> None:
    out = tmp_path / benchmark
    assert main(["export-tasks", "--benchmark", benchmark, "--out", str(out)]) == 0
    expected = all_tasks_for(benchmark)
    assert len(list(out.glob("*.json"))) == len(expected)


@pytest.mark.parametrize("benchmark", BENCHMARK_IDS)
def test_run_oracle_for_each_benchmark(
    tmp_path: Path, benchmark: str, capsys: pytest.CaptureFixture[str]
) -> None:
    task_id = all_tasks_for(benchmark)[0].task_id
    out = tmp_path / "run"
    assert main(["run", "--task", task_id, "--agent", "oracle", "--out", str(out)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["safe_success"] is True
    slug = task_id.replace("/", "_")
    assert (out / slug / "seed-0.trace.json").is_file()
    assert (out / slug / "seed-0.result.json").is_file()


def test_run_oracle_and_quitter(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "oracle"
    assert main(["run", "--task", "v0/rt-001", "--agent", "oracle", "--out", str(out)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["safe_success"] is True
    assert payload["task_success"] is True
    trace_path = out / "v0_rt-001" / "seed-0.trace.json"
    assert trace_path.is_file()
    assert (out / "v0_rt-001" / "seed-0.result.json").is_file()

    assert main(["run", "--task", "v0/rt-001", "--agent", "quitter"]) == 0
    quit_payload = json.loads(capsys.readouterr().out)
    assert quit_payload["safe_success"] is False
    assert "SAF-06" not in quit_payload["catastrophic_codes"]

    assert main(["replay", str(trace_path)]) == 0
    replay_payload = json.loads(capsys.readouterr().out)
    assert replay_payload["matches"] is True


def test_show_task_without_hidden_hides_ground_truth(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["show-task", "v0/rt-001"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert "hidden" not in payload
    assert "public" in payload


def test_run_llm_fake_writes_meta(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "llm"
    assert (
        main(
            [
                "run",
                "--task",
                "v0/rt-001",
                "--agent",
                "llm",
                "--provider",
                "fake",
                "--model",
                "fake",
                "--prompt",
                "v1",
                "--out",
                str(out),
            ]
        )
        == 0
    )
    capsys.readouterr()
    meta_path = out / "meta.json"
    payload = json.loads(meta_path.read_text(encoding="utf-8"))
    assert payload["prompt_id"] == "v1"
    assert len(payload["prompt_sha256"]) == 64
    assert payload["model_id"] == "fake"
    assert payload["provider"] == "fake"
    steps = payload["episodes"][0]["steps"]
    assert steps
    assert steps[0]["latency_ms"] == 0
    assert "input_tokens" in steps[0]["usage"]


def test_bench_llm_fake_one_task(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "bench"
    assert (
        main(
            [
                "bench",
                "--agent",
                "llm",
                "--provider",
                "fake",
                "--model",
                "fake",
                "--prompt",
                "v1",
                "--task",
                "v0/rt-001",
                "--out",
                str(out),
            ]
        )
        == 0
    )
    capsys.readouterr()
    payload = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert payload["episodes"][0]["task_id"] == "v0/rt-001"
    assert payload["prompt_id"] == "v1"
    assert (out / "report.json").is_file()
    assert (out / "report.md").is_file()


def test_bench_llm_fake_one_task_v11(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    task_id = all_tasks_for("v1.1")[0].task_id
    out = tmp_path / "bench-v11"
    assert (
        main(
            [
                "bench",
                "--benchmark",
                "v1.1",
                "--agent",
                "llm",
                "--provider",
                "fake",
                "--model",
                "fake",
                "--prompt",
                "v1",
                "--task",
                task_id,
                "--out",
                str(out),
            ]
        )
        == 0
    )
    capsys.readouterr()
    slug = task_id.replace("/", "_")
    assert (out / slug / "seed-0.trace.json").is_file()
    assert (out / slug / "seed-0.result.json").is_file()
    assert (out / "report.json").is_file()
    assert (out / "report.md").is_file()
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert meta["episodes"][0]["task_id"] == task_id
