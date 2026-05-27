# Codex Implementation Plan

## Phase 0: Make scaffold run

- Verify `pip install -e .` works.
- Verify `scripts/run_smoke_test.py` renders images and produces a terminal result.
- Verify tests pass.
- Fix type hints, dataclasses, and import paths.

## Phase 1: Stable environment

- Complete `TableAGIEnv.reset` and `TableAGIEnv.step`.
- Add trace logging with image hashes.
- Add invalid-action handling.
- Add max-action termination.
- Ensure answer action counts.
- Ensure observation payload has no raw table values.

## Phase 2: Strong renderer

- Improve text clipping.
- Add better spreadsheet aesthetics.
- Add selectable viewport size.
- Add deterministic style randomization.
- Add cell color/font support.

## Phase 3: Task generators

Implement at least five generators:

1. `cell_lookup`
2. `semantic_lookup`
3. `conditional_aggregate`
4. `rule_induction_from_examples`
5. `color_format_reasoning`

Each generator must produce a reference answer and tags.

## Phase 4: Evaluator

- Implement batch runner.
- Implement metrics summary.
- Implement answer normalization.
- Implement human baseline CSV loader.
- Export results as JSONL and CSV.

## Phase 5: Human UI

- Build a simple browser UI.
- Use the same env API.
- Log every action.
- Export human action counts and traces.

## Phase 6: Paper experiments

- Evaluate random, raster, and multimodal LLM agents.
- Run ablations: full image vs viewport, with/without zoom, public vs private templates.
- Report per-family accuracy and efficiency.
- Analyze traces for navigation and grounding errors.

## Definition of done for MVP

A new developer should be able to run:

```bash
pip install -e .
python scripts/run_smoke_test.py
python -m pytest tests
```

and see:

- rendered table images,
- a valid environment trace,
- a correct answer check,
- an action efficiency score,
- no raw table leakage in agent-facing observations.
