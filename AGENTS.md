# Repository Guidelines

`table-env-bench` is an offline-first, deterministic research benchmark for Korean visual table agent reasoning in a workbook-style interface.

The current canonical track is `korean_visual_table_agent_reasoning`: agents inspect rendered Korean table/document environments, navigate sheets/pages/viewports, induce hidden rules, reference support documents, calculate answers, and submit evidence-aware final responses.

## North Star

- Measure interactive table-agent reasoning on top of Korean visual table surfaces.
- Keep workbook/tables as the primary evidence space, not just decorative chrome.
- Use sheets/pages to distribute examples, legends, exception surfaces, and query states.
- Favor tasks that require abstraction, scope resolution, disambiguation, and transfer.
- Keep the benchmark grounded in visible table/workbook evidence. Do not let hidden text dumps, oracle metadata, or backend shortcuts solve the task.

## Working Agreements

- Keep the benchmark offline-first. Core logic must not depend on network access.
- Keep environment state, rendering, data generation, evaluation, and UI concerns separate.
- Preserve deterministic rendering and replayability across seeds.
- Do not expose hidden structured table/grid text in default observations.
- Prefer declarative episode specs and family-specific generators over hard-coded environment branches.
- Keep human-visible benchmark chrome and helper text in Korean unless there is a strong reason not to.
- Favor table-rooted visual primitives: cells, headers, merged headers, row groups, markers, legends, chart/table alignment, notes, and filtered scopes.
- If colors, shapes, or symbols are used, they should usually appear as cell states, row tags, table markers, legend items, or worksheet annotations rather than as free-floating abstract puzzle pieces.
- Treat readability as benchmark integrity, not UI polish. Text overlap, clipping, or invalid layout means the surface is not benchmark-ready.
- Prefer fail-fast layout validation over automatic shrinking or silent geometry fixes. Wrapping is fine; hidden rescue behavior is not.

## What Good Tasks Look Like

- The agent must read a visually rendered table or worksheet fragment and reason over it.
- Multiple sheets/pages matter for a real reasoning reason, not just for extra clicking.
- Headers, merged headers, row groups, legends, notes, or chart/table links change what counts as the relevant evidence.
- At least one non-text visual cue should usually be necessary: merge direction, conditional-format pattern, icon position, indentation depth, border/band structure, or chart glyph alignment.
- Counterexamples or exception sheets narrow the hypothesis space.
- Surface form can vary across table/chart/note views while the underlying rule stays the same.
- Solving should depend more on relational and structural understanding than on OCR of one obvious value.
- The benchmark should cover diverse operators and outputs rather than repeating subset-aggregation mechanics. Selection, mapping, ordering, classification, statement verification, and mini-table choice are all valid answer forms.

## Leveling Guidance

- Level 1 should usually be learnable in 2-3 reasoning steps.
- Level 2 can add one extra cue, one extra band/group, or a weak exception surface and usually lands around 3-4 steps.
- Level 3 can introduce cross-sheet evidence, stronger disambiguation pressure, nested scope, or answer indirection and usually lands around 4-5 steps.
- Do not increase every complexity axis at once. Prefer raising one or two of: perceptual load, scope nesting, operator complexity, answer indirection, navigation burden.
- If a Level 1 task already needs 4-5 steps, it is probably mis-leveled rather than "challenging."

## What To Avoid

- Pure abstract shape puzzles with no table or worksheet semantics.
- "Find one number in appendix, then add it" style tasks as the main benchmark pattern.
- Tasks where business vocabulary does most of the work.
- Single-page lookup problems with no induction or scope reasoning step.
- Debug-only annotations, hidden IDs, cell coordinates, or answer logic leaking into human/agent views.
- Giant rewrites that mix environment, renderer, and family logic together.

## Current Repo Shape

- `src/table_env_bench/env/`: environment API, action parsing, replay logging
- `src/table_env_bench/render/`: layout and SVG renderer
- `src/table_env_bench/data/`: episode specs, loaders, deterministic generators
- `src/table_env_bench/authoring/`: lead-agent pipeline, stage contracts, readability and red-team validation
- `src/table_env_bench/eval/`: correctness and efficiency scoring
- `src/table_env_bench/server/`: FastAPI session server
- `src/table_env_bench/baselines/`: random and heuristic agents
- `frontend/`: React + Vite + TypeScript primary human-facing web UI
- `frontend/playwright/`: surface readability and workbench traversal validation
- `tests/`: deterministic regression coverage
- `docs/`: benchmark-facing documentation and assumptions

## Content Direction

The current active canonical family is:

- `k_vis_table_arc`

The preferred episode structure is now closer to:

- `examples` sheet/page: small table snippets showing completed behavior or inferred rules
- `glossary` / `notes` / `directory` sheet/page: synthetic abbreviations, unit rules, column map, or exception rules
- `query` sheet/page: a new rendered table fragment plus answer choices or final answer prompt
- optional exception/support page: rules out query-only or document-skip shortcuts

Recommended future family themes:

- special symbol rule induction
- merged cell/header scope disambiguation
- synthetic abbreviation document reference
- 50+ column wide-table navigation and calculation
- cross-family composite hidden tests combining symbol, merged header, glossary, and wide table cues

Current family intent:

- `k_vis_table_arc`: episode-based Korean visual table agent benchmark with symbol induction, merged header scope, synthetic abbreviation reference, and wide table navigation templates.

## Episode Rule Docs

Keep the documentation stack for episode rules ahead of implementation. As new canonical families land, the following doc types should exist or be planned explicitly in `docs/` and referenced from `PLANS.md`.

- visual cue inventory
  - non-text cues such as merge direction, icon anchoring, conditional-format patterns, indentation, border semantics, and chart/table alignment
- operator taxonomy
  - select/filter/map/match/order/rank/classify/aggregate/verify style mechanics
- answer-form policy
  - target cell, row/column label, statement choice, mini-table choice, count, short text output
- level progression policy
  - how step count, band count, cue composition, and exception pressure scale by level
- episode validation checklist
  - text-only solvability check, leakage check, distractor quality, deterministic generation checks

When adding or revising a family, update the relevant rule docs first or in the same change. Do not let episode mechanics live only inside generator code.

## Authoring Pipeline

Authoring is now a first-class workflow, not an ad hoc script path.

- Use `src/table_env_bench/authoring/` as the source of truth for family build/validation flow.
- The default stage order is `rulebook -> family_builder -> visual_qa -> viewport_readability -> red_team_solver -> regression_gate`.
- `viewport_readability` is mandatory for family changes. It checks rendered surfaces and workbench traversal, not just metadata.
- `red_team_solver` should explicitly probe family-specific shortcuts such as query-only solving, page skipping, note skipping, or exception skipping when relevant.
- Keep write ownership narrow by stage. Avoid one-off scripts that mix docs, family generation, renderer, and validation in the same patch without reason.

## Readability / Integrity Rules

- Every rendered surface must satisfy zero-overlap requirements.
- Renderer debug payloads must report `invalidLayout == false` and `layoutErrors == []` for benchmark-ready surfaces.
- Table headings, callouts, notes, answer cards, and cell text must fit their boxes without clipping.
- Multi-page families must be checked both statically and by actual workbench traversal.
- If a screenshot looks wrong, add or tighten the gate so the problem fails automatically next time. Do not rely on manual spot checks as the only defense.

## Data Preview Artifacts

- After generating or revising benchmark data, create image artifacts for every rendered problem surface so reviewers can inspect what the agent actually receives.
- The default handoff artifact must be based on `TableEnv(..., mode="agent")` observations, specifically `observation.viewport_image_png_base64`, not a hidden scene dump, oracle metadata, or human-only workbench chrome.
- First export the agent observation gallery from the repo root, for example `uv run python -m table_env_bench.scripts.export_agent_observation_gallery --out artifacts/agent_observations_active --suite canonical_dev`.
- Then capture every agent observation through Playwright: `cd frontend && npm run visual:capture:agent-observations`.
- The Playwright capture reads `artifacts/agent_observations_active/manifest.json` and writes PNG screenshots under `artifacts/playwright/agent_observations_active/`.
- When the handoff needs every canonical benchmark record rather than a single suite, use `uv run python -m table_env_bench.scripts.export_agent_observation_gallery --out artifacts/agent_observations_active --all-benchmark-records`.
- Static renderer previews are still useful for renderer debugging: `uv run python -m table_env_bench.scripts.export_preview_gallery --out artifacts/previews_active` followed by `cd frontend && npm run visual:capture:previews`.
- For targeted datasets, pass the matching `--suite`, `--family`, `--level`, `--template-id`, or `--seed` options to `export_agent_observation_gallery`, and keep `PLAYWRIGHT_REVIEW_DIR` / `PLAYWRIGHT_CAPTURE_DIR` pointed at the corresponding artifact directories.
- Treat these images as the default handoff artifact for new data. Do not rely only on JSON specs, generated metadata, or a local UI session when asking another agent or reviewer to evaluate generated problems.

## Human and Agent Integrity

- Human mode should feel like a clean reasoning console, not a debug harness.
- Dev/debug affordances must remain secondary and collapsible.
- Default observations for agents must stay visual-first and partial.
- Preserve hit testing, replay logs, and deterministic viewport behavior after renderer changes.
- Charts and notes may assist reasoning, but tables/worksheet fragments should remain central to canonical tasks.

## Validation

Use WSL + `uv` when available.

- `uv run pytest`
- `uv run python -m table_env_bench.scripts.export_agent_observation_gallery --out artifacts/agent_observations_active --suite canonical_dev`
- `uv run python -m table_env_bench.scripts.export_agent_observation_gallery --out artifacts/agent_observations_active --all-benchmark-records`
- `cd frontend && npm run visual:capture:agent-observations`
- `uv run python -m table_env_bench.scripts.export_preview_gallery --out artifacts/previews_active`
- `cd frontend && npm run visual:capture:previews`
- `uv run python -m table_env_bench.scripts.run_demo --family k_vis_table_arc --level 1 --template-id symbol_rule_induction --agent random`
- `uv run python -m table_env_bench.scripts.eval_baselines`
- `uv run python -m table_env_bench.scripts.run_authoring_pipeline --family k_vis_table_arc`
- `uv run python -m table_env_bench.scripts.audit_readability`
- `uv run python -m table_env_bench.scripts.run_server --reload`
- `cd frontend && npm install && npm run dev`
- `cd frontend && npm run visual:readability`
- `cd frontend && npm run visual:workbench`
- `cd frontend && npm run visual:readability:public-smoke`
- `cd frontend && npm run visual:readability:public-dev`

Readability notes:

- `uv run python -m table_env_bench.scripts.audit_readability` is the strict release-blocking audit. By default it sweeps all families, all levels, and the full seed capacity.
- `cd frontend && npm run visual:readability` should stay aligned with that strict audit.
- Use smoke downgrades only when iterating locally, for example `uv run python -m table_env_bench.scripts.audit_readability --smoke --seed-samples 0`.
