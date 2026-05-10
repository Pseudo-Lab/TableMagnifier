---
name: tableqa-family-author
description: Create or revise TableMagnifier/table-env-bench Visual TableQA problem families. Use when adding a canonical family, writing episode generators, manifests, docs, or validation for Korean workbook-style table reasoning tasks.
---

# TableQA Family Author

Use this skill when the user asks Codex to make benchmark problems, add a family, or revise family mechanics in this repository.

## Core Contract

- Start from a rubric. Do not implement a new family or data template before the target capability, evidence path, scoring axes, and shortcut probes are written in `rubrics/`.
- Preserve offline-first deterministic generation.
- Keep evidence visual-first; do not expose hidden grid dumps or oracle metadata in observations.
- Keep human-visible benchmark chrome and helper text in Korean.
- Make tables/workbook fragments the primary evidence surface.
- Treat text overlap, clipping, or invalid layout as correctness failures.
- Prefer small adapter-based family modules over branches in loader, renderer, env, or evaluator code.

## Workflow

1. Read `AGENTS.md`, then inspect current family patterns in `src/table_env_bench/data/families/`.
2. Read or create the rubric in `rubrics/`. For the current canonical work, start with `rubrics/k_vis_table_arc_v0.md`.
3. Read the rule docs that match the rubric: start with `docs/episode_rulebook.md`, `docs/visual_cue_inventory.md`, `docs/operator_taxonomy.md`, `docs/answer_form_policy.md`, and `docs/episode_validation_checklist.md`.
4. Draft exactly one family or one template at a time from the rubric:
   - target capability
   - required sheets/pages
   - gold evidence path
   - answer form
   - distractor/shortcut probes
   - level progression
5. Implement one bounded generator change with `FAMILY`, `FAMILY_LABEL`, `list_manifests(level)`, and `build_episode(level, seed, *, template_id=None)`.
6. Register the module with `FamilyAdapter` in `src/table_env_bench/data/families/__init__.py`; do not add separate registry dict entries by hand.
7. Add or update docs/rubrics in the same change when mechanics introduce new cues, operators, answer forms, evidence requirements, or validation policy.
8. Add focused tests for registry, metadata, deterministic generation, level progression, evidence/navigation metadata, and renderability.
9. Run relevant verification. At minimum: `uv run pytest tests/test_pilot_families.py`; for substantial family work also run readability audits.

## Rubric-First Authoring

Every family/template must have a matching rubric section before implementation.

Rubric sections should answer:

- What agent capability is this data intended to measure?
- What visible table/workbook evidence is required?
- Which support sheets/pages are decisive rather than decorative?
- What shortcut should fail?
- What counts as correct answer, correct evidence, efficient behavior, robust solving, and calibrated uncertainty?
- Which level axis changes from L1 to L2 to L3?

When adding data, keep the patch narrow:

- Add one template or one capability slice.
- Update the rubric acceptance checklist if the data introduces a new cue or answer form.
- Encode the same evidence path in `TemplateManifest.required_sheet_ids`, `required_page_refs`, `required_navigation`, and `required_evidence`.
- Add tests that fail if the metadata drifts away from the rubric.

## Adapter Pattern

Each canonical family module should expose this surface:

```python
FAMILY = "new_family_id"
FAMILY_LABEL = "한국어 표시 이름"

TEMPLATES_BY_LEVEL: dict[int, tuple[TemplateManifest, ...]] = {...}


def list_manifests(level: int) -> tuple[TemplateManifest, ...]:
    return TEMPLATES_BY_LEVEL[level]


def build_episode(level: int, seed: int, *, template_id: str | None = None) -> EpisodeSpec:
    manifest, seed_slot = resolve_template_seed(list_manifests(level), seed, template_id=template_id)
    ...
```

Register it once:

```python
FamilyAdapter(
    family=NEW_FAMILY,
    label=NEW_FAMILY_LABEL,
    build_episode=build_new_family_episode,
    list_manifests=list_new_family_manifests,
)
```

## Quality Bar

- Level 1 usually needs 2-3 reasoning steps; Level 2 usually 3-4; Level 3 usually 4-5.
- Multiple sheets/pages must matter for reasoning, not just navigation overhead.
- At least one non-text visual cue should usually be necessary.
- Wrong answers should correspond to plausible shortcut failures.
- Metadata must include required navigation/evidence so red-team and readability gates can probe shortcuts.

For a compact implementation checklist, read `references/family-checklist.md`.
