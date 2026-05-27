# Benchmark Design

## Design principles

### 1. Image-first, not text-first

The benchmark must give agents table images rather than serialized tables. Raw CSV, Markdown, HTML, OCR text, or cell dictionaries may exist internally for generation and verification, but must not be exposed through the agent API.

### 2. Interactive evidence gathering

A task should often be too large or too dense to solve from a single glance. Agents should have to navigate a viewport, zoom, select regions, or inspect linked sub-tables. This creates a measurable difference between blind brute-force exploration and efficient planning.

### 3. Task-local rules

To reduce commonsense shortcuts, rules should be contained inside the table itself. Examples:

- A key table maps arbitrary marker tokens to target categories.
- A legend maps colors to arbitrary statuses.
- A small example block demonstrates an input-output relation that must be applied to query rows.
- Rows contain random IDs and synthetic labels, so external world knowledge is not useful.

### 4. Deterministic generation, private seeds

All benchmark instances should be produced by code from private seeds. Public examples can use separate templates or seed ranges. Private evaluation should use held-out templates and seed ranges.

### 5. Human solvability

A task should be solvable by untrained humans using the same UI within a bounded session. If humans cannot reliably solve a task, the task should be revised or removed.

## Dataset split proposal

| Split | Purpose | Contents |
|---|---:|---|
| Public demo | Format demonstration and debugging | Easy examples, no leaderboard claims |
| Dev | Agent development and regression testing | Medium examples, public answers allowed |
| Semi-private | API model evaluation | Hidden answers, controlled access |
| Fully private | Paper headline evaluation | Hidden templates, seeds, and answers |

## Task taxonomy

Use WildTableBench's five broad capability areas as a starting point, but convert them into interactive tasks.

| Family | Static table QA analogue | Agentic Table-AGI version |
|---|---|---|
| C1 Cell-level | read a cell or range | navigate to target row/column, select/inspect, answer |
| C2 Numerical | aggregate values | gather relevant rows under filters, compute result |
| C3 Verification | true/false claim | verify by collecting evidence cells, answer boolean |
| C4 Hypothetical | recompute after edit | identify affected rows, apply counterfactual, answer updated value |
| C5 Color/format | use visual encoding | infer color legend and reason over formatted cells |

## Level progression

Each environment should contain multiple levels. Early levels communicate controls and the table layout. Later levels should require combining mechanics learned earlier.

Recommended 5-level environment:

1. Locate and read one visible cell.
2. Navigate to off-screen row/column and retrieve a value.
3. Combine a key table with a data table.
4. Apply a conditional aggregate or ranking.
5. Infer a task-local rule and answer under the rule.

## Anti-shortcut requirements

- Use random synthetic labels such as `VX-391`, `MORU`, `K7P`, not semantic names like "sales", "profit", or "disease" for private tasks.
- Randomize row order and column order.
- Vary fonts, column widths, cell colors, and gridline density.
- Keep public templates visibly different from private templates.
- Do not reuse exact color legends or rule names across splits.
- Store answers and raw tables outside agent-visible payloads.
