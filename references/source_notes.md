# Source Notes

These notes summarize the two uploaded papers for implementation purposes.

## WildTableBench

Use as motivation for visual table understanding. Key design ideas to transfer:

- Table observations should be images rather than structured text.
- Include dense and visually varied table layouts.
- Cover multiple skills: cell-level, numerical, verification, hypothetical, and color/format reasoning.
- Evaluate by capability subtype, not only overall score.
- Diagnose grounding and cell-position failures.

## ARC-AGI-3

Use as motivation for interaction and efficiency. Key design ideas to transfer:

- Use a turn-based environment.
- Present an observation each turn and require one action.
- Count action efficiency on first exposure.
- Normalize to human action baselines.
- Cap per-task efficiency at human-level to avoid exploits dominating.
- Penalize inefficient solutions with a squared ratio.
- Keep public demo tasks separate from private evaluation.
- Validate with human solvability and random-agent sanity checks.

## Table-AGI adaptation

The task can include an explicit question. The agentic part is not goal discovery at MVP stage; it is efficient visual evidence gathering and task-local rule application.
