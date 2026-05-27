# Codex Implementation Brief

This repository now keeps the lean Python-first `table-env-bench` benchmark surface.

## Active Goal

Maintain an offline-first Korean visual table reasoning benchmark where agents solve workbook-style episodes through rendered observations and explicit actions. The active canonical family is `k_vis_table_arc`.

## What Is In Scope

- Deterministic episode generation under `src/table_env_bench/data/`
- Workbook environment and replay under `src/table_env_bench/env/`
- SVG/PNG rendering under `src/table_env_bench/render/`
- Scoring and baseline agents under `src/table_env_bench/eval/` and `src/table_env_bench/baselines/`
- Authoring and validation scripts under `src/table_env_bench/authoring/` and `src/table_env_bench/scripts/`
- Tests under `tests/`
- Design and policy docs under `docs/`

## What Is Out Of Scope

- Separate web UI
- JS/browser visual gates
- Separate evaluation-design directory
- Legacy `table_agi_bench` scaffold

## Verification

Use WSL + `uv`:

```bash
uv run pytest
uv run python -m table_env_bench.scripts.export_preview_gallery --out artifacts/previews_active
uv run python -m table_env_bench.scripts.audit_readability --smoke --seed-samples 0
uv run python -m table_env_bench.scripts.run_demo --family k_vis_table_arc --level 1 --template-id symbol_rule_induction --agent random
```

## Authoring Rule

Before adding or revising a family/template, update the relevant rule docs in `docs/` and encode the same evidence requirements in `TemplateManifest` metadata. Do not hide task mechanics only inside generator code.
