# Reference Notes from Uploaded Papers

## WildTableBench design implications

WildTableBench motivates Table-AGI's image-first approach. Its benchmark uses naturally occurring table images, including screenshots, scans, and photographs, and emphasizes structural perception, dense layouts, irregular spans, decorative formatting, skewed orientations, and visual reasoning. It organizes questions into five categories and 17 subtypes, including cell-level understanding, numerical reasoning, verification, hypothetical reasoning, and color-based reasoning.

Implications for Table-AGI:

- Keep table observations visual.
- Evaluate more than direct lookup.
- Include color/format reasoning.
- Include hypothetical recomputation.
- Diagnose location/grounding failures.

## ARC-AGI-3 design implications

ARC-AGI-3 motivates Table-AGI's interactive and efficiency-centered design. It uses turn-based environments, action counts, human baselines, and a relative human action efficiency score. It emphasizes exploration, modeling, goal-setting, and planning/execution.

Implications for Table-AGI:

- Use a turn-based API.
- Count environment actions only.
- Compare to human action baselines.
- Penalize brute force.
- Keep public examples separate from private evaluation.
- Validate tasks by human solvability and random-agent failure.

## Adaptations for Table-AGI

Unlike ARC-AGI-3, Table-AGI can state the question explicitly because the scientific target is table QA rather than autonomous goal discovery. The agentic component comes from how evidence must be found and used. Later variants can hide the goal and ask the agent to infer the required operation from in-table cues, but the MVP should prioritize a robust interactive QA environment.

Unlike WildTableBench, Table-AGI should log action traces and score efficiency. Static answer accuracy alone is insufficient.
