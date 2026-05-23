# Doc-Driven Family Synthesis Checklist

Use this checklist when the user provides a document such as `docs/family/abc_generator.md` and asks for it to become a usable family/template generator.

## Source Document Analysis

- Identify whether the document is a scaffold, a concrete Template Spec Card, or a mixed design note.
- Extract the template/family intent, answer form, primary/support operators, capability axes, required evidence, sheets/pages, hidden program shape, seed variables, variation axes, shortcut traps, distractors, validation rules, and forbidden visible metadata.
- Mark evidence-vs-inference explicitly. Do not invent a new benchmark mechanic when the document only specifies implementation scaffolding.
- Convert TypeScript-style examples to this repo's Python `EpisodeSpec` / `TemplateManifest` pattern.

## Minimum Filled Spec

Before coding, make sure these fields are explicit either in the source doc, rubric, or working note:

- `family_id`, `template_id`, Korean label, and supported levels.
- target capability and why each support sheet/page is decisive.
- answer form and accepted display formats.
- gold evidence path mapped to sheet IDs and page refs.
- hidden program and deterministic seed variables.
- at least three variation axes that preserve the same reasoning contract.
- shortcut traps and matching distractor derivations.
- forbidden visible metadata strings.
- validation and audit expectations.

## Repo-Native Implementation Mapping

- Put repo code in `src/table_env_bench/data/families/<family_id>.py` or extend the existing canonical module when the request is one template inside `k_vis_table_arc`.
- Use `TemplateManifest` rather than a parallel manifest type.
- Use `resolve_template_seed()` so `seed` selects templates consistently.
- Build workbook surfaces with `families/shared.py` helpers before adding new helpers.
- Keep hidden program, distractor labels, candidate labels, rationale, and debug text out of visible `WorkbookSpec` elements and answer cards.
- Encode required navigation and evidence in both manifest metadata and generated episode metadata where possible.
- Add tests that fail if required evidence/navigation drifts from the spec.

## Completion Evidence

Report changed files, the extracted Template Spec Card or manifest summary, variation axes, shortcut traps, validation rules, and verification results.

If only the skill/workflow was upgraded and no family was generated, report that no benchmark data was changed and that tests were limited to documentation/skill review.
