# Family Implementation Checklist

## Before Coding

- Identify the target family id, Korean label, answer form, primary/support operators, and level range.
- Decide required sheets/pages and why each is decisive.
- Define at least one shortcut probe: query-only, sheet skip, note skip, text-only, initial viewport only, or wrong cue interpretation.
- Confirm docs already cover the cue/operator/answer form, or plan the doc update.

## Generator Module

- Put family code in `src/table_env_bench/data/families/<family_id>.py`.
- Use shared helpers from `families/shared.py` before adding helpers.
- Use `resolve_template_seed()` so `seed` selects templates consistently.
- Use `episode()` and `build_episode_metadata()` paths through shared helpers where possible.
- Do not hard-code hidden answer hints into visible text.

## Manifest Checks

- `TemplateManifest.family` matches `FAMILY`.
- `TemplateManifest.level` matches the requested level.
- `required_sheet_ids`, `required_page_refs`, `required_navigation`, and `required_evidence` describe the real solving path.
- `expected_reasoning_steps` matches the level guidance.
- `shortcut_probes` targets the tempting wrong solution.

## Tests

- Registry exposes the family and seed capacity.
- Each level generates a renderable `EpisodeSpec`.
- Workbook sheet/page progression matches the intended difficulty.
- Important metadata appears in `spec.metadata`.
- If a visual bug is found manually, add or tighten an automated gate.

## Verification Commands

```bash
uv run pytest tests/test_pilot_families.py
uv run python -m table_env_bench.scripts.audit_readability --smoke --seed-samples 0
```

For release-ready family work:

```bash
uv run python -m table_env_bench.scripts.audit_readability
cd frontend && npm run visual:readability
cd frontend && npm run visual:workbench
```
