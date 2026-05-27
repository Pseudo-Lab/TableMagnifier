# Paper Outline Draft

## Title candidates

- Table-AGI: An Interactive Benchmark for Efficient Agentic Table Understanding
- Table-AGI: Human-Normalized Action Efficiency for Visual Table QA Agents
- Beyond Static Table VQA: Measuring Agentic Efficiency on Visual Table Reasoning

## Abstract structure

1. Static table QA benchmarks under-measure active evidence gathering.
2. Introduce Table-AGI, an interactive table-image benchmark.
3. Agents receive image observations and act through a small table-navigation action space.
4. Tasks require visual grounding, task-local rule inference, numerical reasoning, and formatting/color reasoning.
5. Evaluation combines answer accuracy with human-normalized action efficiency.
6. Experiments show strong models can answer some tasks but remain inefficient and error-prone under visual navigation.

## Sections

1. Introduction
2. Related Work
   - Text table QA
   - Visual table QA
   - Interactive / agentic benchmarks
   - Human-normalized efficiency metrics
3. Benchmark Design
   - Table-AGI environment
   - Observation and action spaces
   - Task taxonomy
   - Synthetic private generation
   - Human calibration
4. Metrics
   - Accuracy
   - Action efficiency
   - Human baseline protocol
5. Dataset / Environments
   - Splits
   - Task families
   - Rendering styles
   - Validation
6. Experiments
   - Models and agents
   - Main results
   - Per-family analysis
   - Efficiency analysis
   - Human comparison
7. Diagnostics
   - Error taxonomy
   - Trace analysis
   - Location sensitivity
   - Visual-only ablations
8. Limitations and Ethics
9. Conclusion

## Main tables and figures

- Figure 1: Environment loop: image observation → action → new image → answer.
- Figure 2: Example task with viewport navigation.
- Table 1: Task taxonomy.
- Table 2: Action space.
- Table 3: Metrics.
- Table 4: Main benchmark results.
- Figure 3: Accuracy vs action efficiency scatter.
- Figure 4: Human vs AI action count distribution.
- Figure 5: Failure taxonomy.

## Core ablations

- Full table image vs viewport-only.
- Text table oracle vs image-only.
- With vs without color/format cues.
- Small vs large tables.
- Public templates vs private OOD templates.
- Mean-human vs second-best-human efficiency baseline.
