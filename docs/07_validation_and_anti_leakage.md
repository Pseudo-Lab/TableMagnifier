# Validation and Anti-Leakage Plan

## Automated validation

Every task should pass these checks before it is admitted:

1. **Determinism**: same seed creates byte-identical task metadata and visually equivalent render.
2. **Answer consistency**: reference answer is recomputed and matches stored answer.
3. **No raw leakage**: agent observation does not contain table values or answer.
4. **Action bound**: max actions is present and reasonable.
5. **Random-agent sanity**: random agent should almost never solve non-tutorial tasks.
6. **Renderer coverage**: relevant evidence is visible somewhere through valid actions.
7. **Trace replay**: saved traces replay deterministically.

## Split leakage controls

- Public demo templates should not be a representative sample of the private templates.
- Keep private generator seeds secret.
- Keep private template names and rule families hidden.
- Release only a minimal public set for interface demonstration.
- Do not use private tasks for prompt tuning.
- Store private answer keys outside the agent package.

## Commonsense shortcut controls

- Use arbitrary symbolic tokens.
- Avoid real entity names in private tasks.
- Use task-local legends and example blocks.
- Vary table schema across seeds.
- Randomize visual encodings.
- Require evidence from multiple table regions.

## Brute force controls

- Cap max actions.
- Penalize inefficient action counts quadratically.
- Include large tables where exhaustive scanning is action-expensive.
- Track repeated viewports and loops.
- Include tasks where answer space is large enough that guessing is unlikely.

## Visual-only controls

- Agent-facing JSON must not include OCR text.
- Do not send cropped cell text as metadata.
- If an enlarged selected-cell view is implemented, it must be an image crop, not text.
- Logs can contain internal text only in protected evaluator files, not in agent messages.
