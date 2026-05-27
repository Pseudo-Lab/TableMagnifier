# Table-AGI Benchmark / Env Implementation Pack

This package is a Codex-facing implementation brief for building an interactive **Table-AGI** benchmark: an agent receives table images, navigates an Excel-like table environment via discrete actions, and solves question-answering tasks with minimum action cost.

The target paper contribution is not another passive table VQA dataset. The target contribution is an **agentic table QA benchmark** where success requires: visual table grounding, rule discovery inside a task, sequential evidence gathering, planning, and human-normalized action efficiency.

## Why this direction

The uploaded papers motivate two design decisions:

1. **Table image QA should remain visual.** WildTableBench shows that real table understanding is difficult because models struggle with structural perception, cell localization, visual formatting, numerical reasoning, hypothetical reasoning, and color-based reasoning. Table-AGI should therefore keep the table as an image observation and avoid leaking raw CSV/HTML/Markdown to the agent.
2. **Agentic intelligence should be measured by efficient interaction.** ARC-AGI-3 measures turn-based agents by the number of actions needed on first exposure, normalized against human action baselines. Table-AGI should similarly score not only correctness, but also how efficiently the agent explores and executes.

## Minimum viable benchmark

Build an initial benchmark where each task is generated from a private seed and rendered as an Excel-style table image. The table is larger than the current viewport. The agent must use actions such as moving the cursor, moving the viewport, zooming, selecting cells, and submitting an answer.

The first implementation should focus on synthetic Excel-style tables. Later versions can add screenshots, scans, photographs, merged cells, skew, blur, compression artifacts, and real-world collected tables.

## Package contents

- `docs/`: design and implementation documents.
- `schemas/`: JSON schemas for tasks, traces, and run summaries.
- `prompts/`: model-agent prompt contracts.
- `src/table_agi_bench/`: reference Python scaffold for environment, rendering, generators, and metrics.
- `scripts/run_smoke_test.py`: a minimal smoke test that generates one task and renders observations.
- `tests/`: small tests Codex can extend.
- `examples/`: sample task manifest.
- `references/source_notes.md`: paper-grounded design notes.

## First Codex objective

Make the scaffold runnable end-to-end:

```bash
pip install -e .
python3 -m table_agi_bench.demo --seeds 1 2 3 --run-dir runs/demo
python3 scripts/run_smoke_test.py
python3 -m pytest tests
```

The demo command should create generated Table-AGI tasks, render agent-facing table observations, run a development-only scripted oracle policy, and write:

- public observation traces under `runs/demo/public_traces/`,
- public aggregate summaries under `runs/demo/summary.json` and `runs/demo/summary.csv`,
- protected evaluator traces under `runs/demo/protected/`.

Public traces and summaries must not contain submitted answers, reference answers, raw table rows, private metadata, hidden rules, or protected trace paths. `scripts/run_smoke_test.py` remains a compatibility wrapper around the same demo runner.

Human-facing browser UI, model leaderboard runs, ablations, paper experiments, and human baseline collection are follow-up phases, not part of the first agent-facing demo MVP.

## Non-negotiable constraints

- The agent observation must not contain raw table values, answers, computed intermediate values, hidden rules, or parsed cell text.
- All task generation must be seedable and reproducible.
- Every interaction must be logged as a trace.
- Invalid actions should count as actions.
- Answer submission should count as an action.
- Evaluation should report both answer accuracy and action-efficiency scores.
- Human baselines must be collected using the same environment and action space as AI agents.
