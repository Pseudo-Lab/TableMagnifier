"""PIL-based raster renderer for workbook scenes."""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[3]

FONT_REGULAR = (
    Path("/mnt/c/Windows/Fonts/malgun.ttf"),
    Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    REPO_ROOT / "assets/fonts/BMJUA.ttf",
)
FONT_BOLD = (
    Path("/mnt/c/Windows/Fonts/malgunbd.ttf"),
    Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"),
    REPO_ROOT / "assets/fonts/BMJUA.ttf",
)
FONT_MONO = (
    Path("/mnt/c/Windows/Fonts/gulim.ttc"),
    Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansMonoCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansMonoCJK-Regular.ttc"),
)

TABLE_STYLE = {
    "header": {"fill": "#dbe4ee", "text": "#0f172a", "size": 13, "font": "bold", "align": "center"},
    "index": {"fill": "#e8edf4", "text": "#475569", "size": 12, "font": "bold", "align": "center"},
    "row_label": {"fill": "#f3f6fb", "text": "#0f172a", "size": 13, "font": "bold", "align": "left"},
    "body": {"fill": "#ffffff", "text": "#0f172a", "size": 13, "font": "regular", "align": "center"},
    "numeric": {"fill": "#ffffff", "text": "#0f172a", "size": 13, "font": "mono", "align": "right"},
    "muted": {"fill": "#f8fafc", "text": "#64748b", "size": 12, "font": "regular", "align": "center"},
    "accent": {"fill": "#ffffff", "text": "#334155", "size": 13, "font": "mono", "align": "right"},
    "highlight": {"fill": "#eef4ff", "text": "#0f172a", "size": 13, "font": "mono", "align": "right"},
    "negative": {"fill": "#fff7ed", "text": "#b45309", "size": 13, "font": "mono", "align": "right"},
    "total": {"fill": "#dbe4ee", "text": "#0f172a", "size": 13, "font": "mono", "align": "right"},
    "total_label": {"fill": "#dbe4ee", "text": "#0f172a", "size": 13, "font": "bold", "align": "left"},
    "note": {"fill": "#f8fafc", "text": "#334155", "size": 13, "font": "regular", "align": "left"},
}

TEXT_STYLE = {
    "body": {"fill": "#ffffff", "title": "#0f172a", "text": "#475569"},
    "note": {"fill": "#f8fafc", "title": "#0f172a", "text": "#475569"},
    "callout": {"fill": "#eef3f8", "title": "#0f172a", "text": "#475569"},
}


class SceneImageRenderer:
    def __init__(self) -> None:
        self._font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}

    def render_png_bytes(self, scene: dict[str, Any]) -> bytes:
        image = self._render_image(scene)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def render_png_base64(self, scene: dict[str, Any]) -> str:
        return base64.b64encode(self.render_png_bytes(scene)).decode("ascii")

    def _render_image(self, scene: dict[str, Any]) -> Image.Image:
        surface = scene["surface"]
        image = Image.new("RGB", (int(surface["width"]), int(surface["height"])), "#f8fafc")
        draw = ImageDraw.Draw(image)
        self._draw_background(draw, image.size)
        draw_chrome = self._should_draw_workbook_chrome(scene)
        if draw_chrome:
            self._draw_tabs(draw, scene)
        self._draw_page_scene(draw, scene)
        overlay_note = scene.get("overlay_note")
        if overlay_note is not None:
            self._draw_note_overlay(draw, scene, overlay_note)
        return image

    def _should_draw_workbook_chrome(self, scene: dict[str, Any]) -> bool:
        page = scene["page"]
        viewport = scene["viewport"]
        page_width = float(page.get("width", 0.0) or 0.0)
        page_height = float(page.get("height", 0.0) or 0.0)
        if page_width <= 0.0 or page_height <= 0.0:
            return True
        covers_page_width = float(viewport["width"]) >= page_width * 0.98
        covers_page_height = float(viewport["height"]) >= page_height * 0.98
        near_origin = abs(float(viewport["x"])) <= 8.0 and abs(float(viewport["y"])) <= 8.0
        return covers_page_width and covers_page_height and near_origin

    def _draw_background(self, draw: ImageDraw.ImageDraw, size: tuple[int, int]) -> None:
        width, height = size
        draw.rounded_rectangle((18, 18, width - 18, height - 18), radius=18, fill="#ffffff", outline="#dbe4ee", width=1)
        draw.rounded_rectangle((40, 42, width - 40, height - 24), radius=16, fill="#ffffff", outline="#e2e8f0", width=1)

    def _draw_tabs(self, draw: ImageDraw.ImageDraw, scene: dict[str, Any]) -> None:
        workbook = scene["workbook"]
        tabs = workbook["sheet_tabs"]
        active_index = int(workbook["active_sheet_index"])
        x = 78
        y = 56
        for index, label in enumerate(tabs):
            width = max(72, 26 + self._measure_text(label, self._font("bold", 13))[0])
            fill = "#eef3f8" if index == active_index else "#f8fafc"
            draw.rounded_rectangle((x, y, x + width, y + 26), radius=8, fill=fill, outline="#dbe4ee", width=1)
            self._draw_text(draw, (x + 14, y + 6), label, font=self._font("bold", 13), fill="#334155")
            x += width + 10

    def _draw_page_scene(self, draw: ImageDraw.ImageDraw, scene: dict[str, Any]) -> None:
        page = scene["page"]
        if self._should_draw_workbook_chrome(scene):
            self._draw_text(draw, (76, 92), page["title"], font=self._font("bold", 18), fill="#0f172a")
            subtitle = f'{page["sheet_tab_label"]} · 페이지 {page["page_index"] + 1}/1'
            self._draw_text(draw, (76, 120), subtitle, font=self._font("regular", 11), fill="#64748b")
        for element in page["elements"]:
            if element["type"] == "table":
                self._draw_table(draw, scene, element)
            elif element["type"] == "text_block":
                self._draw_text_block(draw, scene, element)

        selected_region = scene.get("selected_region_id")
        if selected_region:
            for region in page["regions"]:
                if region["public_id"] == selected_region:
                    rect = self._map_rect(scene, region["rect"])
                    draw.rounded_rectangle(rect, radius=12, outline="#2563eb", width=2)
                    break

    def _draw_table(self, draw: ImageDraw.ImageDraw, scene: dict[str, Any], table: dict[str, Any]) -> None:
        rect = self._map_rect(scene, table["rect"])
        draw.rounded_rectangle(rect, radius=14, fill="#ffffff", outline="#dbe4ee", width=1)
        x1, y1, x2, y2 = rect
        title_y = y1 - 44
        self._draw_text(draw, (x1, title_y), table.get("title", ""), font=self._font("bold", 16), fill="#0f172a")
        subtitle = table.get("metadata", {}).get("subtitle")
        if subtitle:
            self._draw_text(draw, (x1, y1 - 22), subtitle, font=self._font("regular", 11), fill="#64748b")

        col_offsets = [0]
        for width in table["column_widths"]:
            col_offsets.append(col_offsets[-1] + width)
        row_offsets = [0]
        for height in table["row_heights"]:
            row_offsets.append(row_offsets[-1] + height)

        cells = sorted(table["cells"], key=lambda cell: (cell["row"], cell["col"]))
        page_rect = table["rect"]
        page_x = page_rect["x"]
        page_y = page_rect["y"]
        for cell in cells:
            cell_left = page_x + col_offsets[cell["col"]]
            cell_top = page_y + row_offsets[cell["row"]]
            cell_width = sum(table["column_widths"][cell["col"] : cell["col"] + cell.get("col_span", 1)])
            cell_height = sum(table["row_heights"][cell["row"] : cell["row"] + cell.get("row_span", 1)])
            mapped = self._map_rect(
                scene,
                {"x": cell_left, "y": cell_top, "width": cell_width, "height": cell_height},
            )
            style_name = cell.get("style", "body")
            style = TABLE_STYLE.get(style_name, TABLE_STYLE["body"])
            draw.rectangle(mapped, fill=style["fill"], outline="#dbe4ee", width=1)
            self._draw_cell_text(draw, mapped, cell.get("text", ""), style, cell.get("align", style["align"]))

    def _draw_text_block(self, draw: ImageDraw.ImageDraw, scene: dict[str, Any], block: dict[str, Any]) -> None:
        rect = self._map_rect(scene, block["rect"])
        style = TEXT_STYLE.get(block.get("style", "body"), TEXT_STYLE["body"])
        draw.rounded_rectangle(rect, radius=12, fill=style["fill"], outline="#e2e8f0", width=1)
        x1, y1, x2, y2 = rect
        self._draw_text(draw, (x1 + 18, y1 + 12), block.get("title", ""), font=self._font("bold", 15), fill=style["title"])
        subtitle = block.get("metadata", {}).get("subtitle")
        y_cursor = y1 + 36
        if subtitle:
            self._draw_text(draw, (x1 + 18, y_cursor), subtitle, font=self._font("regular", 11), fill="#64748b")
            y_cursor += 18
        for line in block.get("lines", []):
            for wrapped in self._wrap_text(line, self._font("regular", 12), max(12, int((x2 - x1 - 36) / 8))):
                self._draw_text(draw, (x1 + 18, y_cursor), wrapped, font=self._font("regular", 12), fill=style["text"])
                y_cursor += 18

    def _draw_note_overlay(self, draw: ImageDraw.ImageDraw, scene: dict[str, Any], note: dict[str, Any]) -> None:
        surface = scene["surface"]
        box = (surface["width"] - 420, 118, surface["width"] - 48, 280)
        draw.rounded_rectangle(box, radius=14, fill="#f8fafc", outline="#cbd5e1", width=1)
        self._draw_text(draw, (box[0] + 18, box[1] + 16), note["title"], font=self._font("bold", 16), fill="#0f172a")
        y = box[1] + 46
        for line in self._wrap_text(note["text"], self._font("regular", 12), 28):
            self._draw_text(draw, (box[0] + 18, y), line, font=self._font("regular", 12), fill="#475569")
            y += 18

    def _draw_cell_text(self, draw: ImageDraw.ImageDraw, rect: tuple[float, float, float, float], text: str, style: dict[str, Any], align: str) -> None:
        text = str(text)
        if not text:
            return
        font = self._font(style["font"], int(style["size"]))
        x1, y1, x2, y2 = rect
        text_width, text_height = self._measure_text(text, font)
        if align == "left":
            x = x1 + 12
        elif align == "right":
            x = x2 - text_width - 12
        else:
            x = x1 + ((x2 - x1 - text_width) / 2)
        y = y1 + ((y2 - y1 - text_height) / 2) - 1
        self._draw_text(draw, (x, y), text, font=font, fill=style["text"])

    def _map_rect(self, scene: dict[str, Any], rect: dict[str, Any]) -> tuple[float, float, float, float]:
        viewport = scene["viewport"]
        surface = scene["surface"]
        x1 = (rect["x"] - viewport["x"]) / viewport["width"] * surface["width"]
        y1 = (rect["y"] - viewport["y"]) / viewport["height"] * surface["height"]
        x2 = ((rect["x"] + rect["width"]) - viewport["x"]) / viewport["width"] * surface["width"]
        y2 = ((rect["y"] + rect["height"]) - viewport["y"]) / viewport["height"] * surface["height"]
        return (x1, y1, x2, y2)

    def _font(self, family: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        key = (family, size)
        cached = self._font_cache.get(key)
        if cached is not None:
            return cached
        paths = FONT_BOLD if family == "bold" else FONT_MONO if family == "mono" else FONT_REGULAR
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None
        for path in paths:
            if not path.exists():
                continue
            try:
                font = ImageFont.truetype(str(path), size=size)
                break
            except OSError:
                continue
        if font is None:
            font = ImageFont.load_default()
        self._font_cache[key] = font
        return font

    def _measure_text(self, text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> tuple[float, float]:
        box = font.getbbox(text)
        return float(box[2] - box[0]), float(box[3] - box[1])

    def _draw_text(
        self,
        draw: ImageDraw.ImageDraw,
        position: tuple[float, float],
        text: str,
        *,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        fill: str,
    ) -> None:
        draw.text(position, text, font=font, fill=fill)

    def _wrap_text(
        self,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        max_chars: int,
    ) -> list[str]:
        if len(text) <= max_chars:
            return [text]
        parts: list[str] = []
        current = ""
        for token in text.split():
            candidate = token if not current else f"{current} {token}"
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    parts.append(current)
                current = token
        if current:
            parts.append(current)
        return parts or [text]
