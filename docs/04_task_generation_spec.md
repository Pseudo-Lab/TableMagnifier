# Task Generation Specification

## Generator interface

Each task generator should expose:

```python
def generate(seed: int, difficulty: int) -> TaskSpec:
    ...
```

The output must include:

- table cells and style metadata for rendering,
- question text,
- reference answer,
- answer type,
- tags and skill family,
- max action budget,
- optional expected minimal route for debugging,
- no public exposure of raw table values through the agent API.

## Initial generator families

### 1. `cell_lookup`

A target cell is referenced by row and column labels. The answer is the cell value. Use this for tutorial levels and renderer validation.

### 2. `semantic_lookup`

A row label and column label define an intersection. Labels should be synthetic tokens, not world-meaningful names.

### 3. `conditional_aggregate`

The agent must locate rows matching one or more conditions and compute sum/count/max/min/difference.

Example:

> In DATA TABLE, among rows where `GROUP` matches the KEY row marked `FOCUS`, count rows whose `TOKEN` equals the token shown in the `ACTIVE` key row.

### 4. `rule_induction_from_examples`

The table contains an EXAMPLES block and a QUERY block. The agent must infer a mapping or arithmetic rule from examples and apply it to query rows.

Example pattern:

- If `A > B` and color is blue, label is `M7`.
- If `A <= B` and color is yellow, label is `R2`.
- The symbols are randomized per seed.

### 5. `color_format_reasoning`

A legend maps colors or font styles to statuses. The agent must combine color with text/numeric conditions.

Example:

> The legend maps amber fill to one synthetic status. Among rows with that fill status and `DELTA > 12`, which row has the largest `B` value?

### 6. `hypothetical_recompute`

The agent identifies rows affected by an edit and recomputes a value.

Example:

> If all rows whose marker equals the FOCUS token are reassigned to bucket `QX`, what is the new total of bucket `QX`?

## Difficulty knobs

- Number of rows and columns.
- Table bigger than viewport.
- Distance from initial viewport to relevant evidence.
- Number of subtables: DATA, KEY, LEGEND, EXAMPLES, QUERY.
- Number of conditions.
- Need for arithmetic vs. direct lookup.
- Color/format reliance.
- Visual noise: fonts, gridlines, background colors, merged headers.

## Avoiding commonsense shortcuts

Use arbitrary codes, synthetic numbers, and task-local legends. Avoid labels like countries, products, diseases, companies, or real dates in private tasks unless the values are randomized and irrelevant to world knowledge.

## Golden answer computation

Every generator must compute the answer programmatically from the internal structured table before rendering. Do not rely on OCR or model judging for the reference answer.

## Example internal task layout

```text
A1: DATA TABLE
A2:F2: ID | GROUP | A | B | TOKEN | NOTE
A3:F42: randomized records
A45:C45: KEY TABLE
A46:C49: MARKER | KEY | VALUE
```

The image exposes this layout visually. The agent must discover and use it through navigation.
