# Action and Observation Design

## Why the action space should be small

The benchmark should measure reasoning and evidence gathering, not UI complexity. Keep controls simple and stable.

## MVP action set

| Action | Arguments | Counts? | Effect |
|---|---|---:|---|
| `move_cursor` | direction, steps | yes | Moves selected cell within table bounds |
| `move_viewport` | direction, steps | yes | Scrolls the visible table window |
| `zoom` | `in` or `out` | yes | Changes visible density and font scale |
| `select` | none | yes | Marks the current cell; initially no text is returned |
| `answer` | value | yes | Submits final answer and terminates |
| `noop` | none | yes | Does nothing; useful for protocol tests |

## Optional v2 actions

Add these only after the MVP is stable:

- `jump_to_header`: jump to a visible row/column header selected on image.
- `crop_region`: request a crop around selected cell or viewport quadrant.
- `toggle_formula_bar`: show selected cell enlarged visually, without raw text.
- `add_note`: agent-visible scratch marker on a selected cell.
- `undo`: revert one environment action, still counted.

## Observation image modes

### Full table image

Useful for small tables and early levels. It risks making navigation irrelevant.

### Viewport image

Recommended default. The table can be larger than the image. The agent must scroll and plan.

### Dual image

For advanced models, provide a small mini-map plus a detailed viewport. This resembles spreadsheet navigation without leaking cell text.

## Cursor and headers

The image should include row and column headers like a spreadsheet. This allows humans and agents to communicate positions naturally. Header text is structural and acceptable, as long as it does not encode answer values.

## Feedback policy

Do not provide semantic feedback such as "warmer" or "the selected row is relevant." Feedback should be limited to environment mechanics:

- action accepted,
- invalid action,
- terminal state,
- max actions exceeded.

## Image renderer requirements

- Render gridlines.
- Render column letters and row numbers.
- Render selected cell border.
- Support cell background and foreground colors.
- Support larger-than-viewport sheets.
- Support configurable font size and cell sizes.
- Save deterministic images for reproducibility.
