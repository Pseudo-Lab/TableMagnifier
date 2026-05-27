from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from PIL import Image, ImageDraw, ImageFont

from table_agi_bench.core.types import Cell


def _col_name(index: int) -> str:
    """Zero-based index to spreadsheet-style column name."""
    name = ""
    n = index + 1
    while n:
        n, rem = divmod(n - 1, 26)
        name = chr(65 + rem) + name
    return name


def _safe_hex(color: str, fallback: str) -> str:
    if isinstance(color, str) and len(color) == 7 and color.startswith("#"):
        return color
    return fallback


def _load_font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default(size=size) if hasattr(ImageFont.load_default(), "size") else ImageFont.load_default()


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    left, _, right, _ = draw.textbbox((0, 0), text, font=font)
    return right - left


def _clip_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, font: ImageFont.ImageFont) -> str:
    if _text_width(draw, text, font) <= max_width:
        return text
    ellipsis = "…"
    if _text_width(draw, ellipsis, font) > max_width:
        return ""
    clipped = text
    while clipped and _text_width(draw, clipped + ellipsis, font) > max_width:
        clipped = clipped[:-1]
    return clipped + ellipsis if clipped else ellipsis


class TableRenderer:
    """Deterministic Excel-like viewport renderer.

    This renderer is intentionally simple. Codex should improve text clipping,
    fonts, merged cells, and style randomization in later phases.
    """

    def __init__(
        self,
        cell_width: int = 96,
        cell_height: int = 28,
        header_width: int = 44,
        header_height: int = 26,
        font_size: int = 12,
    ) -> None:
        self.cell_width = cell_width
        self.cell_height = cell_height
        self.header_width = header_width
        self.header_height = header_height
        self.font = _load_font(font_size)
        self.bold_font = _load_font(font_size, bold=True)

    def render_viewport(
        self,
        table: Sequence[Sequence[Cell]],
        out_path: str | Path,
        viewport_row: int,
        viewport_col: int,
        viewport_rows: int,
        viewport_cols: int,
        cursor_row: int,
        cursor_col: int,
        zoom: int = 1,
        visual_metadata: dict[str, Any] | None = None,
    ) -> Path:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        cw = max(50, int(self.cell_width * zoom))
        ch = max(20, int(self.cell_height * zoom))
        width = self.header_width + viewport_cols * cw
        page_graph = (visual_metadata or {}).get("page_graph")
        page_tab_height = 28 if page_graph else 0
        height = self.header_height + viewport_rows * ch + page_tab_height
        img = Image.new("RGB", (width, height), "#f6f8fa")
        draw = ImageDraw.Draw(img)

        # Top-left corner and headers.
        draw.rectangle([0, 0, self.header_width, self.header_height], fill="#e5e7eb", outline="#9ca3af")
        for c in range(viewport_cols):
            abs_c = viewport_col + c
            x0 = self.header_width + c * cw
            draw.rectangle([x0, 0, x0 + cw, self.header_height], fill="#e5e7eb", outline="#9ca3af")
            draw.text((x0 + 4, 6), _col_name(abs_c), fill="#111827", font=self.bold_font)

        for r in range(viewport_rows):
            abs_r = viewport_row + r
            y0 = self.header_height + r * ch
            draw.rectangle([0, y0, self.header_width, y0 + ch], fill="#e5e7eb", outline="#9ca3af")
            draw.text((4, y0 + 7), str(abs_r + 1), fill="#111827", font=self.bold_font)

        n_rows = len(table)
        n_cols = max((len(row) for row in table), default=0)
        merge_ranges = (visual_metadata or {}).get("merge_ranges", [])
        cell_media = (visual_metadata or {}).get("cell_media", [])
        merge_covered = self._merge_covered_cells(merge_ranges)
        media_by_cell = {
            (int(item.get("row", -1)), int(item.get("col", -1))): item
            for item in cell_media
            if item.get("type") == "icon"
        }

        for r in range(viewport_rows):
            abs_r = viewport_row + r
            y0 = self.header_height + r * ch
            for c in range(viewport_cols):
                abs_c = viewport_col + c
                x0 = self.header_width + c * cw
                cell = Cell(text="")
                if 0 <= abs_r < n_rows and 0 <= abs_c < len(table[abs_r]):
                    cell = table[abs_r][abs_c]
                bg = _safe_hex(cell.bg, "#ffffff")
                fg = _safe_hex(cell.fg, "#111111")
                draw.rectangle([x0, y0, x0 + cw, y0 + ch], fill=bg, outline="#d1d5db")
                if (abs_r, abs_c) in media_by_cell:
                    self._draw_icon(draw, media_by_cell[(abs_r, abs_c)], x0, y0, cw, ch)

                if (abs_r, abs_c) not in merge_covered:
                    font = self.bold_font if cell.bold else self.font
                    text = _clip_text(draw, cell.text, max(1, cw - 8), font)
                    draw.text((x0 + 4, y0 + 7), text, fill=fg, font=font)

                if abs_r == cursor_row and abs_c == cursor_col:
                    draw.rectangle([x0 + 1, y0 + 1, x0 + cw - 1, y0 + ch - 1], outline="#2563eb", width=3)

        self._draw_merge_ranges(
            draw=draw,
            merge_ranges=merge_ranges,
            viewport_row=viewport_row,
            viewport_col=viewport_col,
            viewport_rows=viewport_rows,
            viewport_cols=viewport_cols,
            cw=cw,
            ch=ch,
        )
        if page_graph:
            self._draw_page_tabs(draw, page_graph, width, height - page_tab_height, page_tab_height)

        # Outer boundary.
        draw.rectangle([0, 0, width - 1, height - 1], outline="#111827")
        img.save(out_path)
        return out_path

    @staticmethod
    def _merge_covered_cells(merge_ranges: Sequence[dict[str, Any]]) -> set[tuple[int, int]]:
        covered: set[tuple[int, int]] = set()
        for item in merge_ranges:
            start_row = int(item.get("start_row", -1))
            start_col = int(item.get("start_col", -1))
            row_span = int(item.get("row_span", 1))
            col_span = int(item.get("col_span", 1))
            for row in range(start_row, start_row + row_span):
                for col in range(start_col, start_col + col_span):
                    covered.add((row, col))
        return covered

    def _draw_merge_ranges(
        self,
        *,
        draw: ImageDraw.ImageDraw,
        merge_ranges: Sequence[dict[str, Any]],
        viewport_row: int,
        viewport_col: int,
        viewport_rows: int,
        viewport_cols: int,
        cw: int,
        ch: int,
    ) -> None:
        for item in merge_ranges:
            start_row = int(item.get("start_row", -1))
            start_col = int(item.get("start_col", -1))
            row_span = int(item.get("row_span", 1))
            col_span = int(item.get("col_span", 1))
            end_row = start_row + row_span - 1
            end_col = start_col + col_span - 1
            if end_row < viewport_row or start_row >= viewport_row + viewport_rows:
                continue
            if end_col < viewport_col or start_col >= viewport_col + viewport_cols:
                continue

            visible_start_row = max(start_row, viewport_row)
            visible_start_col = max(start_col, viewport_col)
            visible_end_row = min(end_row, viewport_row + viewport_rows - 1)
            visible_end_col = min(end_col, viewport_col + viewport_cols - 1)
            x0 = self.header_width + (visible_start_col - viewport_col) * cw
            y0 = self.header_height + (visible_start_row - viewport_row) * ch
            x1 = self.header_width + (visible_end_col - viewport_col + 1) * cw
            y1 = self.header_height + (visible_end_row - viewport_row + 1) * ch
            draw.rectangle([x0, y0, x1, y1], fill="#dbeafe", outline="#64748b", width=2)
            text = _clip_text(draw, str(item.get("text", "")), max(1, x1 - x0 - 8), self.bold_font)
            text_width = _text_width(draw, text, self.bold_font)
            draw.text((x0 + max(4, (x1 - x0 - text_width) // 2), y0 + 7), text, fill="#111827", font=self.bold_font)

    def _draw_icon(self, draw: ImageDraw.ImageDraw, item: dict[str, Any], x0: int, y0: int, cw: int, ch: int) -> None:
        size = max(20, min(cw, ch) - 10)
        cx = x0 + cw // 2
        cy = y0 + ch // 2
        half = size // 2
        shape = str(item.get("shape", "circle"))
        pattern = str(item.get("pattern", "solid"))
        fill = "#111827" if pattern == "solid" else "#ffffff"
        outline = "#111827"
        box = [cx - half, cy - half, cx + half, cy + half]

        if shape == "circle":
            draw.ellipse(box, fill=fill, outline=outline, width=2)
        elif shape == "triangle":
            points = [(cx, cy - half), (cx - half, cy + half), (cx + half, cy + half)]
            draw.polygon(points, fill=fill, outline=outline)
            draw.line([*points, points[0]], fill=outline, width=2)
        elif shape == "diamond":
            points = [(cx, cy - half), (cx - half, cy), (cx, cy + half), (cx + half, cy)]
            draw.polygon(points, fill=fill, outline=outline)
            draw.line([*points, points[0]], fill=outline, width=2)
        else:
            points = [
                (cx - half // 2, cy - half),
                (cx + half // 2, cy - half),
                (cx + half, cy),
                (cx + half // 2, cy + half),
                (cx - half // 2, cy + half),
                (cx - half, cy),
            ]
            draw.polygon(points, fill=fill, outline=outline)
            draw.line([*points, points[0]], fill=outline, width=2)

        if pattern == "dots":
            for dx, dy in [(-5, -4), (5, -4), (0, 5)]:
                draw.ellipse([cx + dx - 2, cy + dy - 2, cx + dx + 2, cy + dy + 2], fill="#111827")
        elif pattern == "slash":
            draw.line([cx - half + 3, cy + half - 3, cx + half - 3, cy - half + 3], fill="#111827", width=2)

    def _draw_page_tabs(self, draw: ImageDraw.ImageDraw, page_graph: dict[str, Any], width: int, y0: int, height: int) -> None:
        pages = list(page_graph.get("pages", []))
        if not pages:
            return
        draw.rectangle([0, y0, width, y0 + height], fill="#eef2f7", outline="#cbd5e1")
        x = self.header_width
        for page in pages[:6]:
            label = str(page.get("label", page.get("page_id", "P")))
            role = str(page.get("role", ""))
            safe_label = label if len(label) <= 10 else label[:9] + "…"
            tab_w = max(72, _text_width(draw, safe_label, self.bold_font) + 18)
            fill = "#ffffff" if role in {"query", "main_table"} else "#e2e8f0"
            draw.rounded_rectangle([x, y0 + 4, x + tab_w, y0 + height - 4], radius=4, fill=fill, outline="#94a3b8")
            draw.text((x + 8, y0 + 9), safe_label, fill="#111827", font=self.bold_font)
            x += tab_w + 6
            if x > width - 80:
                break
