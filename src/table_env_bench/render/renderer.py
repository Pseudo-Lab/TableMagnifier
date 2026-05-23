"""Deterministic SVG renderer for workbook pages."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from table_env_bench.data.models import (
    ChartElementSpec,
    LegendElementSpec,
    NoteSpec,
    PageElementSpec,
    PageSpec,
    TableCellSpec,
    TableElementSpec,
    TextBlockElementSpec,
    WorkbookSpec,
)
from table_env_bench.render.layout import Rect
from table_env_bench.theme import RADII, TOKENS, rgba


@dataclass(frozen=True)
class RenderConfig:
    viewport_width: int = 1280
    viewport_height: int = 900
    page_margin: int = 44
    header_height: int = 84
    font_family: str = TOKENS.font_sans


TABLE_TEXT_STYLES = {
    "header": {"text": TOKENS.on_surface, "font_size": 13, "weight": 760, "line_gap": 4},
    "index": {"text": TOKENS.on_surface_variant, "font_size": 12, "weight": 680, "line_gap": 4},
    "row_label": {"text": TOKENS.on_surface, "font_size": 13, "weight": 650, "line_gap": 5},
    "body": {"text": TOKENS.on_surface, "font_size": 13, "weight": 560, "line_gap": 5},
    "numeric": {"text": TOKENS.on_surface, "font_size": 13, "weight": 640, "family": TOKENS.font_mono, "line_gap": 5},
    "muted": {"text": TOKENS.on_surface_variant, "font_size": 12, "weight": 560, "line_gap": 4},
    "accent": {"text": TOKENS.tertiary, "font_size": 13, "weight": 720, "family": TOKENS.font_mono, "line_gap": 5},
    "highlight": {"text": TOKENS.primary, "font_size": 13, "weight": 760, "family": TOKENS.font_mono, "line_gap": 5},
    "negative": {"text": "#b54708", "font_size": 13, "weight": 720, "family": TOKENS.font_mono, "line_gap": 5},
    "total": {"text": TOKENS.on_surface, "font_size": 13, "weight": 760, "family": TOKENS.font_mono, "line_gap": 5},
    "total_label": {"text": TOKENS.on_surface, "font_size": 13, "weight": 740, "line_gap": 5},
    "note": {"text": TOKENS.on_surface, "font_size": 13, "weight": 640, "line_gap": 5},
}

TEXT_BLOCK_STYLES = {
    "body": {
        "fill": TOKENS.surface_container_lowest,
        "title": TOKENS.on_surface,
        "text": TOKENS.on_surface_variant,
    },
    "note": {
        "fill": TOKENS.note_container,
        "title": TOKENS.on_surface,
        "text": TOKENS.on_surface_variant,
    },
    "callout": {
        "fill": TOKENS.surface_container_low,
        "title": TOKENS.on_surface,
        "text": TOKENS.on_surface_variant,
    },
}


def _wrap_text(text: str, max_chars: int) -> list[str]:
    text = str(text)
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    if not words:
        return [""]
    lines = [words[0]]
    for word in words[1:]:
        candidate = f"{lines[-1]} {word}"
        if len(candidate) <= max_chars:
            lines[-1] = candidate
        else:
            lines.append(word)
    return lines


def _format_tick(value: float) -> str:
    if value >= 1000:
        return f"{int(round(value)):,}"
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _excel_column_label(index: int) -> str:
    label = ""
    current = index + 1
    while current > 0:
        current, remainder = divmod(current - 1, 26)
        label = chr(65 + remainder) + label
    return label


def _svg_rect(
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    fill: str,
    radius: int | float = 0,
    stroke: str | None = None,
    stroke_width: float = 0.0,
    opacity: float | None = None,
    extra: str = "",
) -> str:
    attributes = [
        f'x="{x:.2f}"',
        f'y="{y:.2f}"',
        f'width="{width:.2f}"',
        f'height="{height:.2f}"',
        f'fill="{fill}"',
    ]
    if radius:
        attributes.append(f'rx="{radius}"')
        attributes.append(f'ry="{radius}"')
    if stroke is not None and stroke_width > 0:
        attributes.append(f'stroke="{stroke}"')
        attributes.append(f'stroke-width="{stroke_width:.2f}"')
    if opacity is not None:
        attributes.append(f'opacity="{opacity:.3f}"')
    if extra:
        attributes.append(extra.strip())
    return f"<rect {' '.join(attributes)}/>"


def _svg_text(
    text: str,
    *,
    x: float,
    y: float,
    size: int | float,
    fill: str,
    weight: int = 500,
    anchor: str = "start",
    family: str = TOKENS.font_sans,
    letter_spacing: float | None = None,
    extra: str = "",
) -> str:
    attributes = [
        f'x="{x:.2f}"',
        f'y="{y:.2f}"',
        f'font-size="{size}"',
        f'font-family="{family}"',
        f'font-weight="{weight}"',
        f'fill="{fill}"',
        f'text-anchor="{anchor}"',
    ]
    if letter_spacing is not None:
        attributes.append(f'letter-spacing="{letter_spacing:.2f}"')
    if extra:
        attributes.append(extra.strip())
    return f"<text {' '.join(attributes)}>{escape(text)}</text>"


def _svg_line(
    *,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    stroke: str,
    stroke_width: float = 1.0,
    opacity: float | None = None,
    extra: str = "",
) -> str:
    attributes = [
        f'x1="{x1:.2f}"',
        f'y1="{y1:.2f}"',
        f'x2="{x2:.2f}"',
        f'y2="{y2:.2f}"',
        f'stroke="{stroke}"',
        f'stroke-width="{stroke_width:.2f}"',
    ]
    if opacity is not None:
        attributes.append(f'opacity="{opacity:.3f}"')
    if extra:
        attributes.append(extra.strip())
    return f"<line {' '.join(attributes)}/>"


def _svg_polygon(
    points: list[tuple[float, float]],
    *,
    fill: str,
    stroke: str | None = None,
    stroke_width: float = 0.0,
    opacity: float | None = None,
    extra: str = "",
) -> str:
    attributes = [f'points="{" ".join(f"{x:.2f},{y:.2f}" for x, y in points)}"', f'fill="{fill}"']
    if stroke is not None and stroke_width > 0:
        attributes.append(f'stroke="{stroke}"')
        attributes.append(f'stroke-width="{stroke_width:.2f}"')
    if opacity is not None:
        attributes.append(f'opacity="{opacity:.3f}"')
    if extra:
        attributes.append(extra.strip())
    return f"<polygon {' '.join(attributes)}/>"


class SvgWorkbookRenderer:
    def __init__(self, config: RenderConfig | None = None) -> None:
        self.config = config or RenderConfig()

    def render_page(
        self,
        workbook: WorkbookSpec,
        *,
        sheet_index: int,
        page_index: int,
        viewport: Rect | None = None,
        overlay_note: NoteSpec | None = None,
        debug: bool = False,
    ) -> str:
        sheet = workbook.sheets[sheet_index]
        page = sheet.pages[page_index]
        view_box = viewport or Rect(0.0, 0.0, float(page.width), float(page.height))
        sheet_x = float(self.config.page_margin)
        sheet_y = 26.0
        sheet_width = page.width - (self.config.page_margin * 2)
        sheet_height = page.height - 52.0

        parts = [
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.config.viewport_width}" '
                f'height="{self.config.viewport_height}" viewBox="{view_box.x:.2f} {view_box.y:.2f} '
                f'{view_box.width:.2f} {view_box.height:.2f}">'
            ),
            "<defs>",
            (
                '<filter id="paper-shadow" x="-20%" y="-20%" width="140%" height="140%">'
                '<feDropShadow dx="0" dy="10" stdDeviation="20" flood-color="rgba(25,28,29,0.06)"/>'
                "</filter>"
            ),
            "</defs>",
            _svg_rect(x=0, y=0, width=page.width, height=page.height, fill=TOKENS.surface),
            _svg_rect(x=0, y=0, width=page.width, height=112, fill=rgba(TOKENS.surface_container_low, 0.88)),
            _svg_rect(
                x=sheet_x,
                y=sheet_y,
                width=sheet_width,
                height=sheet_height,
                fill=TOKENS.surface_container_lowest,
                radius=RADII["lg"],
                stroke=rgba(TOKENS.outline_variant, 0.26),
                stroke_width=1.0,
                extra='filter="url(#paper-shadow)"',
            ),
            _svg_rect(
                x=sheet_x,
                y=sheet_y,
                width=sheet_width,
                height=self.config.header_height,
                fill=rgba(TOKENS.surface_container_low, 0.58),
                radius=RADII["lg"],
            ),
        ]

        parts.extend(self._render_header(workbook, sheet.tab_label, sheet_index, page, page_index))
        for element in page.elements:
            parts.extend(self._render_element(element))

        if debug:
            parts.extend(self._render_debug_regions(page))
        if overlay_note is not None:
            parts.extend(self._render_note_overlay(page, overlay_note))

        parts.append("</svg>")
        return "".join(parts)

    def _render_header(
        self,
        workbook: WorkbookSpec,
        sheet_label: str,
        sheet_index: int,
        page: PageSpec,
        page_index: int,
    ) -> list[str]:
        page_count = len(workbook.sheets[sheet_index].pages)
        header_parts = self._render_sheet_tabs(
            workbook,
            active_sheet_index=sheet_index,
            active_page_index=page_index,
            page_width=page.width,
        )
        header_parts.extend(
            [
                _svg_text(page.title, x=76, y=104, size=26, fill=TOKENS.on_surface, weight=740),
                _svg_text(
                    f"{sheet_label} · 페이지 {page_index + 1}/{page_count}",
                    x=76,
                    y=124,
                    size=11,
                    fill=TOKENS.on_surface_variant,
                    weight=620,
                ),
                _svg_line(
                    x1=76,
                    y1=140,
                    x2=page.width - 76,
                    y2=140,
                    stroke=rgba(TOKENS.outline_variant, 0.24),
                    stroke_width=1.0,
                ),
            ]
        )
        return header_parts

    def _render_sheet_tabs(
        self,
        workbook: WorkbookSpec,
        *,
        active_sheet_index: int,
        active_page_index: int,
        page_width: float,
    ) -> list[str]:
        parts: list[str] = []
        x = 76.0
        y = 42.0
        height = 30.0
        parts.append(
            _svg_text(
                f"문서 검토 자료 · {workbook.title}",
                x=x,
                y=32,
                size=12,
                fill=TOKENS.on_surface_variant,
                weight=700,
            )
        )
        for sheet_index, sheet in enumerate(workbook.sheets):
            label = sheet.tab_label
            width = max(86.0, min(148.0, 54.0 + (len(label) * 14.0)))
            active = sheet_index == active_sheet_index
            parts.append(
                _svg_rect(
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    fill=TOKENS.surface_container_lowest if active else rgba(TOKENS.surface_container, 0.62),
                    radius=RADII["md"],
                    stroke=rgba(TOKENS.outline_variant, 0.28 if active else 0.18),
                    stroke_width=1.1 if active else 1.0,
                )
            )
            if active:
                parts.append(
                    _svg_line(
                        x1=x + 12,
                        y1=y + height - 1,
                        x2=x + width - 12,
                        y2=y + height - 1,
                        stroke=rgba(TOKENS.on_surface, 0.92),
                        stroke_width=1.8,
                    )
                )
            parts.append(
                _svg_text(
                    label,
                        x=x + (width / 2),
                    y=y + 20,
                    size=12,
                    fill=TOKENS.on_surface if active else TOKENS.on_surface_variant,
                    weight=700 if active else 620,
                    anchor="middle",
                )
            )
            x += width + 10
        parts.append(
            _svg_text(
                f"{active_page_index + 1}/{len(workbook.sheets[active_sheet_index].pages)}",
                x=page_width - 76,
                y=63,
                size=11,
                fill=TOKENS.on_surface_variant,
                weight=620,
                anchor="end",
            )
        )
        return parts

    def _render_element(self, element: PageElementSpec) -> list[str]:
        if isinstance(element, TableElementSpec):
            return self._render_table(element)
        if isinstance(element, ChartElementSpec):
            return self._render_chart(element)
        if isinstance(element, LegendElementSpec):
            return self._render_legend(element)
        if isinstance(element, TextBlockElementSpec):
            return self._render_text_block(element)
        raise TypeError(f"Unsupported element type: {type(element)!r}")

    def _render_table(self, element: TableElementSpec) -> list[str]:
        rect = Rect.from_spec(element.rect)
        title_y = rect.y - 26
        subtitle = str(element.metadata.get("subtitle", "")).strip()
        excel_chrome = bool(element.metadata.get("excel_chrome", False))
        freeze_columns = int(element.metadata.get("freeze_columns", 0))
        top_chrome_height = 20 if excel_chrome else 0
        grid_top = rect.y + top_chrome_height
        x_positions = [rect.x]
        for width in element.column_widths:
            x_positions.append(x_positions[-1] + width)
        y_positions = [grid_top]
        for height in element.row_heights:
            y_positions.append(y_positions[-1] + height)

        parts: list[str] = []
        parts.append(_svg_text(element.title, x=rect.x, y=title_y, size=18, fill=TOKENS.on_surface, weight=730))
        if subtitle:
            parts.append(_svg_text(subtitle, x=rect.x, y=title_y + 16, size=11, fill=TOKENS.on_surface_variant, weight=560))

        parts.append(
            _svg_rect(
                x=rect.x,
                y=rect.y,
                width=rect.width,
                height=rect.height,
                fill=TOKENS.surface_container_lowest,
                radius=RADII["md"],
                stroke=rgba(TOKENS.outline_variant, 0.18),
                stroke_width=1.1,
            )
        )
        if excel_chrome:
            parts.append(
                _svg_rect(
                    x=rect.x,
                    y=rect.y,
                    width=rect.width,
                    height=top_chrome_height,
                    fill=rgba(TOKENS.surface_container_low, 0.92),
                    radius=RADII["md"],
                )
            )
            for col_index, width in enumerate(element.column_widths):
                letter_x = x_positions[col_index] + (width / 2)
                parts.append(
                    _svg_text(
                        _excel_column_label(col_index),
                        x=letter_x,
                        y=rect.y + 14,
                        size=10,
                        fill=TOKENS.on_surface_variant,
                        weight=620,
                        anchor="middle",
                        family=TOKENS.font_mono,
                        letter_spacing=0.6,
                    )
                )
            parts.append(
                _svg_line(
                    x1=rect.x + 8,
                    y1=grid_top,
                    x2=rect.x + rect.width - 8,
                    y2=grid_top,
                    stroke=rgba(TOKENS.outline_variant, 0.26),
                    stroke_width=1.15,
                )
            )
        if element.n_cols >= 1:
            parts.append(
                _svg_rect(
                    x=rect.x,
                    y=grid_top,
                    width=element.column_widths[0],
                    height=rect.height - top_chrome_height,
                    fill=rgba(TOKENS.surface_container_high, 0.54),
                )
            )

        for row_index, row_height in enumerate(element.row_heights):
            row_y = y_positions[row_index]
            parts.append(
                _svg_rect(
                    x=rect.x,
                    y=row_y,
                    width=rect.width,
                    height=row_height,
                    fill=self._table_row_fill(element, row_index),
                    radius=RADII["md"] if row_index == 0 and not excel_chrome else 0,
                )
            )

        prominent_column_boundaries = {freeze_columns} if freeze_columns > 0 else set()
        for cell in element.cells:
            if cell.row == 0 and cell.col_span > 1:
                boundary = cell.col + cell.col_span
                if boundary < element.n_cols:
                    prominent_column_boundaries.add(boundary)

        for separator_x in x_positions[1:-1]:
            boundary_index = x_positions.index(separator_x)
            is_prominent = boundary_index in prominent_column_boundaries
            parts.append(
                _svg_line(
                    x1=separator_x,
                    y1=rect.y + 10,
                    x2=separator_x,
                    y2=rect.y + rect.height - 10,
                    stroke=rgba(TOKENS.outline_variant, 0.28 if is_prominent else 0.16),
                    stroke_width=1.35 if is_prominent else 1.0,
                )
            )
        for row_index, separator_y in enumerate(y_positions[1:-1], start=1):
            prev_is_header = self._is_header_row(element, row_index - 1)
            next_is_header = self._is_header_row(element, row_index)
            prev_is_total = self._is_total_row(element, row_index - 1)
            next_is_total = self._is_total_row(element, row_index)
            prev_is_group = self._is_group_row(element, row_index - 1)
            next_is_group = self._is_group_row(element, row_index)
            line_opacity = 0.18
            line_width = 1.0
            if prev_is_header or next_is_header:
                line_opacity = 0.30
                line_width = 1.3
            if prev_is_group or next_is_group:
                line_opacity = max(line_opacity, 0.26)
                line_width = max(line_width, 1.15)
            if prev_is_total or next_is_total:
                line_opacity = 0.36
                line_width = 1.55
            parts.append(
                _svg_line(
                    x1=rect.x + 8,
                    y1=separator_y,
                    x2=rect.x + rect.width - 8,
                    y2=separator_y,
                    stroke=rgba(TOKENS.outline_variant, line_opacity),
                    stroke_width=line_width,
                )
            )
        if freeze_columns > 0 and freeze_columns < len(x_positions):
            parts.append(
                _svg_line(
                    x1=x_positions[freeze_columns],
                    y1=rect.y + 10,
                    x2=x_positions[freeze_columns],
                    y2=rect.y + rect.height - 10,
                    stroke=rgba(TOKENS.outline_variant, 0.34),
                    stroke_width=1.45,
                )
            )

        for cell in element.cells:
            cell_rect = Rect(
                x=float(x_positions[cell.col]),
                y=float(y_positions[cell.row]),
                width=float(sum(element.column_widths[cell.col : cell.col + cell.col_span])),
                height=float(sum(element.row_heights[cell.row : cell.row + cell.row_span])),
            )
            parts.extend(self._render_table_cell_backgrounds(element, cell, cell_rect))
            parts.extend(self._render_table_text(cell, cell_rect))
            parts.extend(self._render_table_cell_foregrounds(cell, cell_rect))
        return parts

    def _table_row_cells(self, element: TableElementSpec, row_index: int) -> list[TableCellSpec]:
        return [cell for cell in element.cells if cell.row == row_index]

    def _table_row_styles(self, element: TableElementSpec, row_index: int) -> set[str]:
        return {cell.style for cell in self._table_row_cells(element, row_index)}

    def _table_row_label(self, element: TableElementSpec, row_index: int) -> str:
        for cell in self._table_row_cells(element, row_index):
            if cell.col == 0 and cell.text.strip():
                return cell.text.strip()
        return ""

    def _is_header_row(self, element: TableElementSpec, row_index: int) -> bool:
        row_cells = self._table_row_cells(element, row_index)
        return bool(row_cells) and all(cell.style == "header" for cell in row_cells)

    def _is_total_row(self, element: TableElementSpec, row_index: int) -> bool:
        row_styles = self._table_row_styles(element, row_index)
        if "total" in row_styles or "total_label" in row_styles:
            return True
        row_label = self._table_row_label(element, row_index)
        return row_label.startswith("합계") or row_label.startswith("소계")

    def _is_group_row(self, element: TableElementSpec, row_index: int) -> bool:
        row_styles = self._table_row_styles(element, row_index)
        row_label = self._table_row_label(element, row_index)
        return bool(row_label) and "row_label" in row_styles and "muted" in row_styles and not self._is_total_row(element, row_index)

    def _table_row_fill(self, element: TableElementSpec, row_index: int) -> str:
        if self._is_header_row(element, row_index):
            return TOKENS.surface_container_highest if row_index == 0 else rgba(TOKENS.surface_container_high, 0.88)
        row_styles = self._table_row_styles(element, row_index)
        row_label = self._table_row_label(element, row_index)
        if self._is_total_row(element, row_index):
            if row_label.startswith("합계"):
                return rgba(TOKENS.primary_fixed, 0.82)
            return rgba(TOKENS.surface_container_highest, 0.96)
        if self._is_group_row(element, row_index):
            return rgba(TOKENS.tertiary_fixed, 0.72)
        if "highlight" in row_styles:
            return rgba(TOKENS.primary_fixed, 0.76)
        if "accent" in row_styles:
            return rgba(TOKENS.tertiary_fixed, 0.88)
        if "note" in row_styles:
            return rgba(TOKENS.note_container, 0.95)
        return TOKENS.surface_container_lowest if row_index % 2 == 1 else TOKENS.surface_container_low

    def _render_table_cell_backgrounds(self, element: TableElementSpec, cell: TableCellSpec, rect: Rect) -> list[str]:
        parts: list[str] = []
        if cell.row_span > 1 or cell.col_span > 1:
            stroke_opacity = 0.14
            stroke_width = 1.0
            if cell.style == "header":
                stroke_opacity = 0.24
                stroke_width = 1.2
            elif cell.style in {"total", "total_label"}:
                stroke_opacity = 0.22
                stroke_width = 1.15
            parts.append(
                _svg_rect(
                    x=rect.x + 1,
                    y=rect.y + 1,
                    width=max(rect.width - 2, 0),
                    height=max(rect.height - 2, 0),
                    fill=self._table_cell_fill(element, cell),
                    stroke=rgba(TOKENS.outline_variant, stroke_opacity),
                    stroke_width=stroke_width,
                )
            )

        pattern = cell.metadata.get("pattern")
        if isinstance(pattern, dict):
            parts.extend(self._render_table_cell_pattern(rect, pattern))
        return parts

    def _render_table_cell_foregrounds(self, cell: TableCellSpec, rect: Rect) -> list[str]:
        parts: list[str] = []
        icon = cell.metadata.get("icon")
        if isinstance(icon, dict):
            parts.extend(self._render_table_cell_icon(rect, icon))

        frame = cell.metadata.get("frame")
        if isinstance(frame, dict):
            parts.extend(self._render_table_cell_frame(rect, frame))
        elif frame:
            parts.extend(self._render_table_cell_frame(rect, {}))
        return parts

    def _render_table_cell_pattern(self, rect: Rect, pattern: dict[str, object]) -> list[str]:
        kind = str(pattern.get("kind", ""))
        if kind != "diagonal_stripe":
            return []

        inset = float(pattern.get("inset", 6))
        spacing = max(float(pattern.get("spacing", 12)), 8.0)
        stroke = str(pattern.get("color", rgba(TOKENS.primary, 0.18)))
        stroke_width = float(pattern.get("stroke_width", 2.2))
        opacity = float(pattern.get("opacity", 0.55))
        usable_width = max(rect.width - (inset * 2), 0)
        usable_height = max(rect.height - (inset * 2), 0)
        if usable_width <= 0 or usable_height <= 0:
            return []

        parts = [
            _svg_rect(
                x=rect.x + 1,
                y=rect.y + 1,
                width=max(rect.width - 2, 0),
                height=max(rect.height - 2, 0),
                fill=rgba(TOKENS.primary_fixed, 0.12),
            )
        ]
        start = -usable_height
        end = int(usable_width) + int(usable_height)
        offset = start
        while offset <= end:
            x1 = rect.x + inset + max(offset, 0)
            y1 = rect.y + rect.height - inset - max(offset, 0)
            x2 = rect.x + inset + max(offset - usable_height, 0)
            y2 = rect.y + inset + max(usable_height - offset, 0)
            x1 = min(max(x1, rect.x + inset), rect.x + rect.width - inset)
            y1 = min(max(y1, rect.y + inset), rect.y + rect.height - inset)
            x2 = min(max(x2, rect.x + inset), rect.x + rect.width - inset)
            y2 = min(max(y2, rect.y + inset), rect.y + rect.height - inset)
            parts.append(
                _svg_line(
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    stroke=stroke,
                    stroke_width=stroke_width,
                    opacity=opacity,
                    extra='stroke-linecap="round"',
                )
            )
            offset += int(spacing)
        return parts

    def _render_table_cell_icon(self, rect: Rect, icon: dict[str, object]) -> list[str]:
        kind = str(icon.get("kind", ""))
        if kind != "triangle":
            return []

        anchor = str(icon.get("anchor", "top_right"))
        size = float(icon.get("size", 12))
        inset = float(icon.get("inset", 7))
        fill = str(icon.get("color", TOKENS.primary))

        if anchor == "top_left":
            points = [
                (rect.x + inset, rect.y + inset),
                (rect.x + inset + size, rect.y + inset),
                (rect.x + inset, rect.y + inset + size),
            ]
        elif anchor == "bottom_left":
            points = [
                (rect.x + inset, rect.y + rect.height - inset),
                (rect.x + inset + size, rect.y + rect.height - inset),
                (rect.x + inset, rect.y + rect.height - inset - size),
            ]
        elif anchor == "bottom_right":
            points = [
                (rect.x + rect.width - inset, rect.y + rect.height - inset),
                (rect.x + rect.width - inset - size, rect.y + rect.height - inset),
                (rect.x + rect.width - inset, rect.y + rect.height - inset - size),
            ]
        else:
            points = [
                (rect.x + rect.width - inset, rect.y + inset),
                (rect.x + rect.width - inset - size, rect.y + inset),
                (rect.x + rect.width - inset, rect.y + inset + size),
            ]

        return [_svg_polygon(points, fill=fill, opacity=float(icon.get("opacity", 0.92)))]

    def _render_table_cell_frame(self, rect: Rect, frame: dict[str, object]) -> list[str]:
        inset = float(frame.get("inset", 4))
        color = str(frame.get("color", TOKENS.primary))
        stroke_width = float(frame.get("stroke_width", 2.2))
        return [
            _svg_rect(
                x=rect.x + inset,
                y=rect.y + inset,
                width=max(rect.width - (inset * 2), 0),
                height=max(rect.height - (inset * 2), 0),
                fill="none",
                radius=RADII["sm"],
                stroke=color,
                stroke_width=stroke_width,
            )
        ]

    def _table_cell_fill(self, element: TableElementSpec, cell: TableCellSpec) -> str:
        if cell.style == "header":
            return TOKENS.surface_container_highest if cell.row == 0 else rgba(TOKENS.surface_container_high, 0.92)
        if cell.style in {"total", "total_label"}:
            row_label = self._table_row_label(element, cell.row)
            if row_label.startswith("합계"):
                return rgba(TOKENS.primary_fixed, 0.82)
            return rgba(TOKENS.surface_container_highest, 0.96)
        return self._table_row_fill(element, cell.row)

    def _render_table_text(self, cell: TableCellSpec, rect: Rect) -> list[str]:
        style = TABLE_TEXT_STYLES.get(cell.style, TABLE_TEXT_STYLES["body"])
        text_inset = 18 if cell.style in {"row_label", "total_label", "note"} else 16
        usable_width = max(rect.width - (text_inset * 2), 48)
        max_chars = max(7, int(usable_width / 8.4))
        lines = _wrap_text(cell.text, max_chars=max_chars)
        line_height = int(style["font_size"]) + int(style.get("line_gap", 5))
        block_height = line_height * len(lines)
        baseline = rect.center_y - (block_height / 2) + line_height - 3
        family = str(style.get("family", TOKENS.font_mono if cell.align == "right" and cell.style != "header" else TOKENS.font_sans))

        if cell.align == "left":
            anchor = "start"
            text_x = rect.x + text_inset
        elif cell.align == "right":
            anchor = "end"
            text_x = rect.x + rect.width - text_inset
        else:
            anchor = "middle"
            text_x = rect.center_x

        return [
            _svg_text(
                line,
                x=text_x,
                y=baseline + (index * line_height),
                size=style["font_size"],
                fill=style["text"],
                weight=style["weight"],
                anchor=anchor,
                family=family,
            )
            for index, line in enumerate(lines)
        ]

    def _render_chart(self, element: ChartElementSpec) -> list[str]:
        rect = Rect.from_spec(element.rect)
        subtitle = str(element.metadata.get("subtitle", "")).strip()
        parts = [
            _svg_text(element.title, x=rect.x, y=rect.y - 24, size=17, fill=TOKENS.on_surface, weight=680),
        ]
        if subtitle:
            parts.append(_svg_text(subtitle, x=rect.x, y=rect.y - 6, size=12, fill=TOKENS.on_surface_variant, weight=600))

        parts.append(
            _svg_rect(
                x=rect.x,
                y=rect.y,
                width=rect.width,
                height=rect.height,
                fill=TOKENS.surface_container_lowest,
                radius=RADII["md"],
                stroke=rgba(TOKENS.outline_variant, 0.12),
                stroke_width=1.0,
            )
        )

        plot_left = rect.x + 66
        plot_top = rect.y + 70
        plot_width = rect.width - 104
        plot_height = rect.height - 120
        plot_bottom = plot_top + plot_height

        parts.append(
            _svg_rect(
                x=plot_left,
                y=plot_top,
                width=plot_width,
                height=plot_height,
                fill=TOKENS.plot_fill,
                radius=RADII["sm"],
            )
        )

        max_value = max((max(series.values) for series in element.series), default=1.0)
        max_value = max(max_value, 1.0)

        for tick_index in range(5):
            fraction = tick_index / 4
            tick_value = max_value * (1 - fraction)
            tick_y = plot_top + (plot_height * fraction)
            parts.append(
                _svg_line(
                    x1=plot_left,
                    y1=tick_y,
                    x2=plot_left + plot_width,
                    y2=tick_y,
                    stroke=rgba(TOKENS.chart_grid, 0.95),
                    extra='stroke-dasharray="4 6"',
                )
            )
            parts.append(
                _svg_text(
                    _format_tick(tick_value),
                    x=plot_left - 10,
                    y=tick_y + 4,
                    size=12,
                    fill=TOKENS.on_surface_variant,
                    weight=600,
                    anchor="end",
                )
            )

        parts.extend(
            [
                _svg_line(x1=plot_left, y1=plot_top, x2=plot_left, y2=plot_bottom, stroke=rgba(TOKENS.outline_variant, 0.28)),
                _svg_line(
                    x1=plot_left,
                    y1=plot_bottom,
                    x2=plot_left + plot_width,
                    y2=plot_bottom,
                    stroke=rgba(TOKENS.outline_variant, 0.28),
                ),
            ]
        )

        if element.y_axis_label:
            parts.append(
                _svg_text(
                    element.y_axis_label,
                    x=plot_left,
                    y=rect.y + 48,
                    size=12,
                    fill=TOKENS.on_surface_variant,
                    weight=600,
                )
            )

        if element.chart_type == "bar":
            parts.extend(self._render_bar_chart(element, plot_left, plot_width, plot_height, plot_bottom, max_value))
        elif element.chart_type == "line":
            parts.extend(self._render_line_chart(element, plot_left, plot_width, plot_height, plot_bottom, max_value))
        else:
            raise ValueError(f"Unsupported chart type: {element.chart_type}")
        return parts

    def _render_bar_chart(
        self,
        element: ChartElementSpec,
        plot_left: float,
        plot_width: float,
        plot_height: float,
        plot_bottom: float,
        max_value: float,
    ) -> list[str]:
        category_count = max(len(element.categories), 1)
        series_count = max(len(element.series), 1)
        slot_width = plot_width / category_count
        bar_group_width = slot_width * 0.72
        bar_width = bar_group_width / series_count
        parts: list[str] = []

        for category_index, category in enumerate(element.categories):
            category_center_x = plot_left + (slot_width * category_index) + (slot_width / 2)
            parts.append(
                _svg_text(
                    category,
                    x=category_center_x,
                    y=plot_bottom + 28,
                    size=13,
                    fill=TOKENS.on_surface_variant,
                    weight=600,
                    anchor="middle",
                )
            )
            group_left = category_center_x - (bar_group_width / 2)
            for series_index, series in enumerate(element.series):
                value = series.values[category_index]
                bar_height = (value / max_value) * plot_height
                x = group_left + (series_index * bar_width) + 4
                width = max(bar_width - 8, 14)
                y = plot_bottom - bar_height
                parts.append(
                    _svg_rect(
                        x=x,
                        y=y,
                        width=width,
                        height=bar_height,
                        fill=series.color,
                        radius=4,
                        opacity=0.9,
                    )
                )
        return parts

    def _render_line_chart(
        self,
        element: ChartElementSpec,
        plot_left: float,
        plot_width: float,
        plot_height: float,
        plot_bottom: float,
        max_value: float,
    ) -> list[str]:
        category_count = max(len(element.categories), 1)
        step = plot_width / max(category_count - 1, 1)
        parts: list[str] = []

        for category_index, category in enumerate(element.categories):
            x = plot_left + (step * category_index)
            parts.append(
                _svg_text(
                    category,
                    x=x,
                    y=plot_bottom + 28,
                    size=13,
                    fill=TOKENS.on_surface_variant,
                    weight=600,
                    anchor="middle",
                )
            )

        for series in element.series:
            points: list[tuple[float, float]] = []
            for category_index, value in enumerate(series.values):
                x = plot_left + (step * category_index)
                y = plot_bottom - ((value / max_value) * plot_height)
                points.append((x, y))
            point_string = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
            parts.append(
                f'<polyline fill="none" stroke="{series.color}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" points="{point_string}"/>'
            )
            for x, y in points:
                parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5.5" fill="{series.color}" stroke="#ffffff" stroke-width="1.8"/>')
        return parts

    def _render_legend(self, element: LegendElementSpec) -> list[str]:
        rect = element.rect
        parts = [
            _svg_rect(
                x=rect.x,
                y=rect.y,
                width=rect.width,
                height=rect.height,
                fill=rgba(TOKENS.surface_container_low, 0.9),
                radius=RADII["md"],
            ),
            _svg_text(element.title, x=rect.x + 16, y=rect.y + 24, size=12, fill=TOKENS.on_surface_variant, weight=700, letter_spacing=0.8),
        ]
        for index, item in enumerate(element.items):
            y = rect.y + 48 + (index * 28)
            parts.append(_svg_rect(x=rect.x + 16, y=y - 11, width=16, height=16, fill=item.color, radius=4))
            parts.append(_svg_text(item.label, x=rect.x + 42, y=y + 1, size=14, fill=TOKENS.on_surface, weight=600))
        return parts

    def _render_text_block(self, element: TextBlockElementSpec) -> list[str]:
        rect = element.rect
        subtitle = str(element.metadata.get("subtitle", "")).strip()
        style = TEXT_BLOCK_STYLES.get(element.style, TEXT_BLOCK_STYLES["body"])
        parts = [
            _svg_rect(
                x=rect.x,
                y=rect.y,
                width=rect.width,
                height=rect.height,
                fill=style["fill"],
                radius=RADII["md"],
                stroke=rgba(TOKENS.outline_variant, 0.10),
                stroke_width=1.0,
            )
        ]
        parts.append(_svg_text(element.title, x=rect.x + 18, y=rect.y + 28, size=16, fill=style["title"], weight=680))
        if subtitle:
            parts.append(_svg_text(subtitle, x=rect.x + 18, y=rect.y + 46, size=12, fill=TOKENS.on_surface_variant, weight=600))
        wrapped_lines: list[str] = []
        for line in element.lines:
            wrapped_lines.extend(_wrap_text(line, max(22, int(rect.width / 14))))
        line_start = rect.y + (58 if subtitle else 52)
        for index, line in enumerate(wrapped_lines):
            parts.append(
                _svg_text(
                    line,
                    x=rect.x + 18,
                    y=line_start + (index * 22),
                    size=14,
                    fill=style["text"],
                    weight=500,
                )
            )
        return parts

    def _render_debug_regions(self, page: PageSpec) -> list[str]:
        parts: list[str] = []
        for region in page.regions:
            rect = region.rect
            parts.append(
                _svg_rect(
                    x=rect.x,
                    y=rect.y,
                    width=rect.width,
                    height=rect.height,
                    fill="none",
                    stroke="#cf4f4b",
                    stroke_width=1.8,
                    extra='stroke-dasharray="7 5"',
                )
            )
            parts.append(
                _svg_text(
                    f"{region.role} · {region.label}",
                    x=rect.x + 8,
                    y=rect.y + 18,
                    size=12,
                    fill="#b83b35",
                    weight=700,
                )
            )
        return parts

    def _render_note_overlay(self, page: PageSpec, note: NoteSpec) -> list[str]:
        box = Rect(x=118.0, y=124.0, width=page.width - 236.0, height=page.height - 248.0)
        lines = _wrap_text(note.text, 58)
        parts = [
            _svg_rect(x=0, y=0, width=page.width, height=page.height, fill=rgba(TOKENS.on_surface, 0.18)),
            _svg_rect(
                x=box.x,
                y=box.y,
                width=box.width,
                height=box.height,
                fill=rgba(TOKENS.surface_container_lowest, 0.98),
                radius=RADII["lg"],
                stroke=rgba(TOKENS.outline_variant, 0.12),
                stroke_width=1.0,
                extra='filter="url(#paper-shadow)"',
            ),
            _svg_text(note.id, x=box.x + 28, y=box.y + 34, size=11, fill=TOKENS.on_surface_variant, weight=700, letter_spacing=1.6),
            _svg_text(note.title, x=box.x + 28, y=box.y + 68, size=24, fill=TOKENS.on_surface, weight=760),
        ]
        for index, line in enumerate(lines):
            parts.append(
                _svg_text(
                    line,
                    x=box.x + 28,
                    y=box.y + 110 + (index * 26),
                    size=17,
                    fill=TOKENS.on_surface_variant,
                    weight=500,
                )
            )
        return parts
