# Renderer and Visual Style Guide

## MVP renderer

Use a deterministic Pillow-based renderer for Excel-like tables.

Required visual features:

- row numbers,
- column letters,
- gridlines,
- selected cell border,
- viewport clipping,
- configurable cell width and height,
- text clipping inside cells,
- background colors,
- foreground colors,
- bold headers.

## Style randomization

Add controlled style variation by seed:

- font size,
- row height,
- column width,
- alternating row shading,
- header colors,
- gridline intensity,
- text alignment,
- number formatting,
- hidden or visible row/column headers.

## v2 visual complexity

After the MVP:

- merged cells,
- frozen panes,
- conditional formatting,
- rotated text,
- icons and data bars,
- slight skew or blur,
- compression artifacts,
- screenshot-like border and toolbar,
- scanned/photographed versions.

## Accessibility for human baseline

Visual complexity should not make tasks frustrating for humans. Difficulty should come from reasoning composition and navigation, not from illegible text.

## Image file naming

Use deterministic names:

```text
runs/{run_id}/{task_id}/obs_{turn:04d}.png
```

Every trace event should store the image hash.
