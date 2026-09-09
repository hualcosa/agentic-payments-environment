# Reproducibility

## Pin

Install from the committed lockfile:

```bash
uv sync --all-extras
```

`uv.lock` is the pin. Runtime extras `[openai]` and `[anthropic]` are
optional and must not be imported by `import agentic_payments_env`.

## One command: oracle headline table (v0)

```bash
uv sync --all-extras && uv run apenv bench --benchmark v0 --agent oracle --seeds 0 --out runs/oracle
```

Compare `runs/oracle/report.md` headline rates to the committed
[reports/v0/oracle.md](v0/oracle.md). Those rates (safe success 1.000 on
seed 0) came from that style of run. `runs/` is gitignored; the reviewed
copy lives under `reports/`.

## Other committed artifacts

- v0 freeze: `uv run apenv export-tasks --benchmark v0 --out /tmp/v0` and
  diff against `benchmarks/v0/` (CI freeze test).
- v1 freeze: `export-tasks --benchmark v1` vs `benchmarks/v1/`.
- SFT JSONL: `uv run apenv export-sft --task v0/rt-001 --out /tmp/sft.jsonl`.
- Tests: `uv run ruff format --check . && uv run ruff check . && uv run mypy src && uv run pytest -q`.

## Not reproduced here

Live LLM benches (`--agent llm`) and live LLM-as-judge agreement need
provider API keys. Those results are **not yet measured**. Do not fill
them in from memory.
