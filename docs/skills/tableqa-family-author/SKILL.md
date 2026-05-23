---
name: tableqa-family-author
description: Create or revise TableMagnifier/table-env-bench Visual TableQA problem families. Use when adding a canonical family, writing episode generators, manifests, docs, or validation for Korean workbook-style table reasoning tasks.
---

# TableQA Family Author

Use this skill when the user asks Codex to make benchmark problems, add a family, revise family mechanics, or turn a family/template design document into an executable generator in this repository.

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
2. If the user provides or points to a design/scaffold document, read it first. For the current doc-driven scaffold, use `docs/family/abc_generator.md` as the contract for Template Spec Cards, variation axes, hidden programs, shortcut traps, metadata, and validation.
3. Read or create the rubric in `rubrics/`. For the current canonical work, start with `rubrics/k_vis_table_arc_v0.md`.
4. Read the rule docs that match the rubric: start with `docs/episode_rulebook.md`, `docs/visual_cue_inventory.md`, `docs/operator_taxonomy.md`, `docs/answer_form_policy.md`, and `docs/episode_validation_checklist.md`.
5. Draft exactly one family or one template at a time from the rubric and any Template Spec Card:
   - target capability
   - required sheets/pages
   - gold evidence path
   - answer form
   - distractor/shortcut probes
   - level progression
6. Implement one bounded generator change with `FAMILY`, `FAMILY_LABEL`, `list_manifests(level)`, and `build_episode(level, seed, *, template_id=None)`.
7. Register the module with `FamilyAdapter` in `src/table_env_bench/data/families/__init__.py`; do not add separate registry dict entries by hand.
8. Add or update docs/rubrics in the same change when mechanics introduce new cues, operators, answer forms, evidence requirements, or validation policy.
9. Add focused tests for registry, metadata, deterministic generation, level progression, evidence/navigation metadata, and renderability.
10. Run relevant verification. At minimum: `uv run pytest tests/test_pilot_families.py`; for substantial family work also run readability audits.

## Doc-Driven Family Synthesis

When the input is a scaffold/spec document like `docs/family/abc_generator.md`, treat the document as an authoring contract, not as code to copy literally.

Use this translation:

- `Template Idea` becomes the template intent and `TemplateManifest.latent_rule`.
- `Template Spec Card` becomes the source of truth for `template_id`, label, answer form, operators, capability axes, required evidence, shortcut probes, level progression, and seed variables.
- `manifest` maps to this repo's Python `TemplateManifest`, including `required_sheet_ids`, `required_page_refs`, `required_navigation`, `required_evidence`, `expected_reasoning_steps`, and `shortcut_probes`.
- `sampleParams(seed_slot, level)` maps to deterministic parameter sampling inside `build_episode()` or a small private helper. Use `random.Random(...)` or existing shared helpers; do not depend on network, wall clock, or global randomness.
- `buildWorkbook(params)` maps to `WorkbookSpec` construction through shared helpers such as `sheet()`, `page()`, `table_from_cells()`, `text_block()`, `cell()`, `rect()`, and query choice helpers.
- `solve(params)` maps to the hidden answer calculation and `AnswerSpec`.
- `buildChoices(...)` maps to visible choice cards and accepted answer IDs. Choice text may show only option IDs and display values.
- `buildMetadata(...)` maps to `episode()` / `build_episode_metadata()` metadata plus explicit fields for decisive variables, visible-unused variables, gold evidence path, hidden program shape, and distractor derivations when the family supports them.
- `validate(...)` maps to tests, readability audits, and any family-local validation helpers. Do not rely on manual screenshot review as the only gate.

Before implementing, fill any missing Template Spec Card fields in a short working note or rubric section. If a field is underspecified, infer conservatively from the rule docs and current family patterns; ask only if the answer would materially change the family contract.

For this workflow, also read `references/doc-driven-family.md`.

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
