# Project Brief: Table-AGI

## One-sentence goal

Create a benchmark environment where an agent solves table QA from image observations through discrete actions, and is evaluated by both answer correctness and human-normalized action efficiency.

## Research hypothesis

Current multimodal agents can sometimes answer static table-image questions, but they are inefficient and brittle when the task requires active visual evidence gathering, local rule inference, and planning under an action budget.

## Expected paper contribution

Table-AGI should be framed as an **interactive visual table reasoning benchmark**. It combines:

- table-image understanding from WildTableBench-style tasks,
- turn-based environment design from ARC-AGI-3,
- human action baselines,
- synthetic/private rule generation to reduce commonsense shortcuts,
- structured diagnostics by skill type, table location, action type, and reasoning depth.

## Core definitions

- **Environment**: one table family or sheet scenario containing multiple levels/tasks.
- **Level / task**: one question over one table image, with a reference answer and metadata.
- **Observation**: image-only table view plus safe metadata such as action count and valid action names.
- **Action**: one discrete command submitted to the environment. This includes movement, zoom, selection, and answer submission.
- **Trace**: ordered list of observations and actions from reset to terminal state.
- **Correctness**: whether the submitted answer matches the reference answer under task-specific normalization.
- **Action efficiency**: a normalized score comparing the agent action count to a human baseline action count.

## MVP scope

The MVP should not attempt real-world web data collection first. Start with generated Excel-like tables because this enables:

- private deterministic seeds,
- exact reference answers,
- controlled visual styles,
- scalable task templates,
- reproducible human and AI evaluation.

The MVP should support 5 task families:

1. Cell lookup and localization.
2. Semantic row/column lookup.
3. Conditional aggregation.
4. Task-local rule discovery from examples inside the sheet.
5. Color/format-based reasoning.

## Paper-facing claim to preserve

The benchmark is not measuring whether an LLM knows a fact. It is measuring whether an agent can acquire a task-local table skill efficiently from first exposure.
