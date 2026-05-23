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

RENDER_TEXT_SIZES = {
    "page_title": 22,
    "page_meta": 12,
    "workbook_title": 17,
    "tab": 14,
    "table_title": 18,
    "table_subtitle": 14,
    "text_block_title": 16,
    "text_block_subtitle": 14,
    "text_block_body": 14,
    "answer_title": 16,
    "answer_body": 16,
    "note_overlay_title": 16,
    "note_overlay_body": 14,
    "footer": 11,
    "status": 12,
}

TABLE_STYLE = {
    "header": {"fill": "#e8eff6", "text": "#0b1220", "size": 15, "font": "bold", "align": "center"},
    "index": {"fill": "#f0f4f8", "text": "#334155", "size": 15, "font": "bold", "align": "center"},
    "row_label": {"fill": "#f4f7fb", "text": "#0b1220", "size": 15, "font": "bold", "align": "left"},
    "body": {"fill": "#ffffff", "text": "#0b1220", "size": 15, "font": "regular", "align": "center"},
    "numeric": {"fill": "#ffffff", "text": "#0b1220", "size": 15, "font": "mono", "align": "right"},
    "muted": {"fill": "#f8fafc", "text": "#475569", "size": 15, "font": "regular", "align": "center"},
    "accent": {"fill": "#ffffff", "text": "#1f2937", "size": 15, "font": "mono", "align": "right"},
    "highlight": {"fill": "#f2f6fd", "text": "#0b1220", "size": 15, "font": "mono", "align": "right"},
    "negative": {"fill": "#fff8ee", "text": "#8a3f07", "size": 15, "font": "mono", "align": "center"},
    "total": {"fill": "#e8eff6", "text": "#0b1220", "size": 15, "font": "mono", "align": "right"},
    "total_label": {"fill": "#e8eff6", "text": "#0b1220", "size": 15, "font": "bold", "align": "left"},
    "note": {"fill": "#f8fafc", "text": "#1f2937", "size": 15, "font": "regular", "align": "left"},
}

TEXT_STYLE = {
    "body": {"fill": "#ffffff", "title": "#0f172a", "text": "#475569"},
    "note": {"fill": "#f8fafc", "title": "#0f172a", "text": "#475569"},
    "callout": {"fill": "#eef4fb", "title": "#0f172a", "text": "#334155"},
}

PRODUCT_NAME = "문서 검토 자료"

TEMPLATE_THEMES = {
    "abbrev_doc_reference": {
        "accent": "#3159a4",
        "label": "운영 지표 검토",
        "workspace": "운영 지표 워크스페이스",
    },
    "symbol_rule_induction": {
        "accent": "#8a5a12",
        "label": "검사 코드 매핑",
        "workspace": "마킹 규칙 검수",
    },
    "color_condition_rule_induction": {
        "accent": "#0f766e",
        "label": "조건부 서식 감사",
        "workspace": "서식 감사 콘솔",
    },
    "legend_color_exception_scope": {
        "accent": "#8f2d3f",
        "label": "상태 범례 검토",
        "workspace": "예외 범례 검토",
    },
    "merged_header_scope": {
        "accent": "#4f46a5",
        "label": "운영 매트릭스 분석",
        "workspace": "매트릭스 범위 검토",
    },
    "wide_table_navigation": {
        "accent": "#475569",
        "label": "데이터 원장 탐색",
        "workspace": "데이터 원장 콘솔",
    },
    "wide_table_viewport_trace": {
        "accent": "#25636c",
        "label": "뷰포트 추적 기록",
        "workspace": "뷰포트 추적 콘솔",
    },
    "merged_header_pan_scope": {
        "accent": "#5b4b8a",
        "label": "원거리 헤더 범위",
        "workspace": "원거리 매트릭스",
    },
    "zoom_micro_marker_exception": {
        "accent": "#3f6f4f",
        "label": "미세 마커 검수",
        "workspace": "미세 마커 검수",
    },
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
        image = Image.new("RGB", (int(surface["width"]), int(surface["height"])), "#e9edf2")
        draw = ImageDraw.Draw(image)
        theme = self._theme(scene)
        self._draw_background(draw, image.size, theme)
        draw_chrome = self._should_draw_workbook_chrome(scene)
        if draw_chrome:
            self._draw_tabs(draw, scene, theme)
        else:
            self._draw_partial_viewport_chrome(draw, scene, theme)
        self._draw_page_scene(draw, scene, theme)
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

    def _theme(self, scene: dict[str, Any]) -> dict[str, str]:
        workbook = scene.get("workbook", {})
        metadata = workbook.get("metadata", {}) if isinstance(workbook, dict) else {}
        template_id = str(metadata.get("template_id", ""))
        return TEMPLATE_THEMES.get(
            template_id,
            {"accent": "#35557d", "label": "문서형 추론", "workspace": "문서 검토 자료"},
        )

    def _draw_background(self, draw: ImageDraw.ImageDraw, size: tuple[int, int], theme: dict[str, str]) -> None:
        width, height = size
        draw.rectangle((0, 0, width, height), fill="#f5f7fa")
        draw.rectangle((32, 24, width - 32, height - 24), fill="#ffffff")
        draw.line((32, 84, width - 32, 84), fill="#d9e2ec", width=1)

    def _draw_tabs(self, draw: ImageDraw.ImageDraw, scene: dict[str, Any], theme: dict[str, str]) -> None:
        workbook = scene["workbook"]
        tabs = workbook["sheet_tabs"]
        active_index = int(workbook["active_sheet_index"])
        x = 48
        y = 54
        surface_width = int(scene["surface"]["width"])
        title = str(workbook["title"])
        self._draw_text(
            draw,
            (48, 26),
            title,
            font=self._font("bold", RENDER_TEXT_SIZES["workbook_title"]),
            fill="#172033",
        )
        self._draw_text(
            draw,
            (430, 30),
            theme["label"],
            font=self._font("regular", RENDER_TEXT_SIZES["page_meta"]),
            fill="#64748b",
        )
        for index, label in enumerate(tabs):
            width = max(68, 26 + self._measure_text(label, self._font("bold", RENDER_TEXT_SIZES["tab"]))[0])
            fill = "#ffffff"
            outline = "#ffffff"
            draw.rectangle((x, y, x + width, y + 26), fill=fill, outline=outline, width=1)
            if index == active_index:
                draw.rectangle((x + 8, y + 23, x + width - 8, y + 25), fill=theme["accent"])
            self._draw_text(
                draw,
                (x + 12, y + 5),
                label,
                font=self._font("bold", RENDER_TEXT_SIZES["tab"]),
                fill="#0f172a" if index == active_index else "#475569",
            )
            x += width + 10
        self._draw_context_controls(draw, scene, theme, surface_width)

    def _draw_context_controls(
        self,
        draw: ImageDraw.ImageDraw,
        scene: dict[str, Any],
        theme: dict[str, str],
        surface_width: int,
    ) -> None:
        page = scene["page"]
        sheet_id = str(page.get("sheet_id", ""))
        page_id = str(page.get("page_id", ""))
        page_metadata = page.get("metadata", {}) if isinstance(page, dict) else {}
        workbook_metadata = scene.get("workbook", {}).get("metadata", {}) if isinstance(scene.get("workbook", {}), dict) else {}
        template_id = str(workbook_metadata.get("template_id", ""))
        is_query = sheet_id == "query"
        is_wide = bool(page_metadata.get("wide_table"))
        is_zoom = template_id == "zoom_micro_marker_exception" and ("zoom" in page_id or sheet_id == "query")
        controls: list[str] = []
        if is_wide:
            controls.append("표시 열 범위")
        elif is_zoom:
            controls.append("확대 160%")
        x = surface_width - 48
        for label in reversed(controls):
            width = max(96, int(self._measure_text(label, self._font("bold", RENDER_TEXT_SIZES["status"]))[0]) + 30)
            self._draw_status_pill(
                draw,
                (x - width, 54, x, 78),
                label,
                fill="#f8fafc",
                text_fill=theme["accent"] if label.startswith("확대") or label.startswith("표시") else "#475569",
                outline="#d6dee8",
            )
            x -= width + 12

    def _draw_partial_viewport_chrome(self, draw: ImageDraw.ImageDraw, scene: dict[str, Any], theme: dict[str, str]) -> None:
        page = scene["page"]
        viewport = scene["viewport"]
        surface = scene["surface"]
        surface_width = int(surface["width"])
        surface_height = int(surface["height"])
        bar_width = 360
        bar_right = surface_width - 48
        bar_left = bar_right - bar_width
        bar_y = surface_height - 58
        bar = (bar_left, bar_y, bar_right, bar_y + 14)
        draw.rounded_rectangle(bar, radius=7, fill="#d9e2ec", outline="#cbd5e1", width=1)
        page_width = max(float(page.get("width", 1)), 1.0)
        view_width = max(30.0, min(float(bar_width), float(bar_width) * (float(viewport["width"]) / page_width)))
        view_x = bar_left + min(float(bar_width) - view_width, float(bar_width) * (float(viewport["x"]) / page_width))
        draw.rounded_rectangle((view_x, bar_y + 1, view_x + view_width, bar_y + 13), radius=6, fill=theme["accent"])
        self._draw_text(draw, (bar_left - 98, bar_y + 3), "표시 열 범위", font=self._font("regular", 10), fill="#64748b")

    def _draw_page_scene(self, draw: ImageDraw.ImageDraw, scene: dict[str, Any], theme: dict[str, str]) -> None:
        page = scene["page"]
        if self._should_draw_workbook_chrome(scene):
            self._draw_text(draw, (48, 96), page["title"], font=self._font("bold", RENDER_TEXT_SIZES["page_title"]), fill="#0f172a")
            subtitle = f'{page["sheet_tab_label"]} · 페이지 {page["page_index"] + 1}/1'
            self._draw_text(draw, (320, 104), subtitle, font=self._font("regular", RENDER_TEXT_SIZES["page_meta"]), fill="#64748b")
            self._draw_page_affordances(draw, scene, theme)
            self._draw_neutral_footer(draw, scene, theme)
        for element in page["elements"]:
            if element["type"] == "table":
                self._draw_table(draw, scene, element, theme)
            elif element["type"] == "text_block":
                self._draw_text_block(draw, scene, element, theme)
        if self._should_draw_workbook_chrome(scene):
            self._draw_auto_context_panel(draw, scene, theme)

        selected_region = scene.get("selected_region_id")
        if selected_region:
            for region in page["regions"]:
                if region["public_id"] == selected_region:
                    rect = self._map_rect(scene, region["rect"])
                    draw.rounded_rectangle(rect, radius=12, outline="#2563eb", width=2)
                    break

    def _draw_auto_context_panel(self, draw: ImageDraw.ImageDraw, scene: dict[str, Any], theme: dict[str, str]) -> None:
        page = scene["page"]
        if page.get("metadata", {}).get("wide_table"):
            return
        elements = page.get("elements", ())
        if not elements:
            return
        for element in elements:
            if element.get("type") == "text_block" and str(element.get("title", "")) == "문서 표시 기준":
                return
        max_bottom = 0.0
        for element in elements:
            rect = element.get("rect")
            if not isinstance(rect, dict):
                continue
            _x1, _y1, _x2, y2 = self._map_rect(scene, rect)
            max_bottom = max(max_bottom, y2)
        surface = scene["surface"]
        surface_width = float(surface["width"])
        surface_height = float(surface["height"])
        context_bottom = surface_height - 96.0
        if max_bottom > context_bottom - 94.0:
            return
        y1 = max_bottom + 28.0
        y2 = context_bottom
        if y2 - y1 < 68:
            return
        x1, x2 = 64.0, surface_width - 64.0
        draw.rounded_rectangle((x1, y1, x2, y2), radius=5, fill="#fbfdff", outline="#d6dee8", width=1)
        draw.rectangle((x1, y1, x1 + 3, y2), fill=theme["accent"])
        self._draw_text(draw, (x1 + 18, y1 + 16), "문서 표시 기준", font=self._font("bold", RENDER_TEXT_SIZES["text_block_title"]), fill="#0f172a")
        lines = (
            f"{theme['label']} 화면은 원문 표기와 문서 구조를 유지해 표시합니다.",
            "문서 하단에는 버전, 표시 단위, 보존 기준 같은 공통 검토 정보를 배치합니다.",
        )
        for index, line in enumerate(lines):
            self._draw_text(draw, (x1 + 18, y1 + 46 + index * 23), line, font=self._font("regular", RENDER_TEXT_SIZES["text_block_body"]), fill="#334155")

    def _draw_page_affordances(self, draw: ImageDraw.ImageDraw, scene: dict[str, Any], theme: dict[str, str]) -> None:
        page = scene["page"]
        page_metadata = page.get("metadata", {}) if isinstance(page, dict) else {}
        viewport = scene["viewport"]
        surface_width = int(scene["surface"]["width"])
        if page_metadata.get("wide_table"):
            bar_right = surface_width - 56
            bar_left = bar_right - 324
            bar = (bar_left, 122, bar_right, 136)
            draw.rounded_rectangle(bar, radius=7, fill="#e2e8f0", outline="#cbd5e1", width=1)
            view_width = max(28.0, min(324.0, 324.0 * (float(viewport["width"]) / max(float(page.get("width", 1)), 1.0))))
            view_x = bar_left + min(324.0 - view_width, 324.0 * (float(viewport["x"]) / max(float(page.get("width", 1)), 1.0)))
            draw.rounded_rectangle((view_x, 123, view_x + view_width, 135), radius=6, fill=theme["accent"])
            self._draw_text(draw, (bar_left - 112, 124), "가로 표시 범위", font=self._font("regular", 11), fill="#64748b")
        workbook_metadata = scene.get("workbook", {}).get("metadata", {}) if isinstance(scene.get("workbook", {}), dict) else {}
        if str(workbook_metadata.get("template_id", "")) == "zoom_micro_marker_exception" and (
            "zoom" in str(page.get("page_id", "")) or str(page.get("sheet_id", "")) == "query"
        ):
            self._draw_status_pill(
                draw,
                (748, 122, 888, 148),
                "확대 검사 160%",
                fill="#f8fafc",
                text_fill="#475569",
                outline="#d6dee8",
            )

    def _draw_table(self, draw: ImageDraw.ImageDraw, scene: dict[str, Any], table: dict[str, Any], theme: dict[str, str]) -> None:
        rect = self._map_rect(scene, table["rect"])
        x1, y1, x2, y2 = rect
        title_y = y1 - 42
        draw.rounded_rectangle((x1, y1 - 50, x2, y2), radius=4, fill="#ffffff", outline="#d5dee8", width=1)
        draw.rectangle((x1, y1 - 50, x2, y1 - 4), fill="#ffffff")
        draw.line((x1, y1 - 5, x2, y1 - 5), fill="#d5dee8", width=1)
        draw.rectangle((x1, y1 - 50, x1 + 3, y1 - 5), fill=theme["accent"])
        self._draw_text(draw, (x1 + 16, title_y), table.get("title", ""), font=self._font("bold", RENDER_TEXT_SIZES["table_title"]), fill="#0b1220")
        subtitle = table.get("metadata", {}).get("subtitle")
        if subtitle:
            self._draw_text(draw, (x1 + 16, y1 - 20), subtitle, font=self._font("regular", RENDER_TEXT_SIZES["table_subtitle"]), fill="#475569")
        freeze_columns = int(table.get("metadata", {}).get("freeze_columns", 0) or 0)
        page = scene["page"]
        page_metadata = page.get("metadata", {}) if isinstance(page, dict) else {}
        show_freeze_badge = freeze_columns > 0 and bool(page_metadata.get("wide_table"))
        if show_freeze_badge:
            self._draw_status_pill(
                draw,
                (x2 - 146, y1 - 42, x2 - 14, y1 - 18),
                "고정 열 적용",
                fill="#e8eef6",
                text_fill="#475569",
                outline="#cbd5e1",
            )

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
            fill = style["fill"]
            if style_name == "body" and cell["row"] % 2 == 0:
                fill = "#fbfcfe"
            if style_name == "header":
                fill = "#edf3f8"
            draw.rectangle(mapped, fill=fill)
            mx1, my1, mx2, my2 = mapped
            draw.line((mx1, my2 - 1, mx2, my2 - 1), fill="#dce5ef", width=1)
            if cell.get("col_span", 1) > 1 or cell.get("row_span", 1) > 1:
                draw.rectangle(mapped, outline="#cbd7e3", width=1)
            if style_name == "header":
                draw.line((mx1 + 2, my2 - 1, mx2 - 2, my2 - 1), fill=theme["accent"], width=1)
            self._draw_cell_visual_metadata(draw, mapped, cell.get("metadata", {}))
            self._draw_cell_text(draw, mapped, cell.get("text", ""), style, cell.get("align", style["align"]))
        if table.get("metadata", {}).get("excel_chrome") and page_metadata.get("wide_table"):
            self._draw_table_minimap(draw, rect, theme)

    def _draw_neutral_footer(self, draw: ImageDraw.ImageDraw, scene: dict[str, Any], theme: dict[str, str]) -> None:
        page = scene["page"]
        surface = scene["surface"]
        surface_width = int(surface["width"])
        surface_height = int(surface["height"])
        sheet_id = str(page.get("sheet_id", ""))
        page_id = str(page.get("page_id", ""))
        if page.get("metadata", {}).get("wide_table"):
            footer = "고정 설명 열 · 가로 범위 · 원장 보기"
        elif sheet_id == "query":
            footer = "접수 문서 · 응답 포맷"
        elif page_id.endswith("p2"):
            footer = "보조 문서 · 적용 기준"
        else:
            footer = "원문 기준 · 표시 단위"
        y1 = surface_height - 48
        draw.line((48, y1, surface_width - 48, y1), fill="#e2e8f0", width=1)
        self._draw_text(draw, (56, y1 + 10), footer, font=self._font("regular", RENDER_TEXT_SIZES["footer"]), fill="#94a3b8")
        self._draw_text(
            draw,
            (surface_width - 330, y1 + 10),
            "원문 화면 기준 · 내부 분석 문서",
            font=self._font("regular", RENDER_TEXT_SIZES["footer"]),
            fill="#94a3b8",
        )

    def _draw_table_minimap(self, draw: ImageDraw.ImageDraw, rect: tuple[float, float, float, float], theme: dict[str, str]) -> None:
        x1, _y1, x2, y2 = rect
        if x2 - x1 < 260:
            return
        draw.rounded_rectangle((x2 - 220, y2 + 8, x2 - 18, y2 + 18), radius=5, fill="#e2e8f0")
        draw.rounded_rectangle((x2 - 210, y2 + 9, x2 - 126, y2 + 17), radius=4, fill=theme["accent"])

    def _draw_cell_visual_metadata(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[float, float, float, float],
        metadata: dict[str, Any],
    ) -> None:
        if not isinstance(metadata, dict):
            return
        x1, y1, x2, y2 = rect
        pattern = metadata.get("pattern")
        if isinstance(pattern, dict) and pattern.get("kind") == "diagonal_stripe":
            color = str(pattern.get("color", "#25636c"))
            step = 11
            start = int(x1 - (y2 - y1))
            end = int(x2 + (y2 - y1))
            for offset in range(start, end, step):
                draw.line((offset, y2 - 2, offset + (y2 - y1), y1 + 2), fill=color, width=1)
        frame = metadata.get("frame")
        if isinstance(frame, dict):
            color = str(frame.get("color", "#2d6a4f"))
            stroke_width = max(1, int(round(float(frame.get("stroke_width", 2)))))
            draw.rectangle((x1 + 3, y1 + 3, x2 - 3, y2 - 3), outline=color, width=stroke_width)
        icon = metadata.get("icon")
        if isinstance(icon, dict):
            color = str(icon.get("color", "#2d6a4f"))
            size = max(6, int(icon.get("size", 8)))
            anchor = str(icon.get("anchor", "top_right"))
            if anchor == "bottom_right":
                points = [(x2 - size - 4, y2 - 4), (x2 - 4, y2 - 4), (x2 - 4, y2 - size - 4)]
            elif anchor == "top_left":
                points = [(x1 + 4, y1 + 4), (x1 + size + 4, y1 + 4), (x1 + 4, y1 + size + 4)]
            else:
                points = [(x2 - size - 4, y1 + 4), (x2 - 4, y1 + 4), (x2 - 4, y1 + size + 4)]
            draw.polygon(points, fill=color)

    def _draw_text_block(self, draw: ImageDraw.ImageDraw, scene: dict[str, Any], block: dict[str, Any], theme: dict[str, str]) -> None:
        rect = self._map_rect(scene, block["rect"])
        style = TEXT_STYLE.get(block.get("style", "body"), TEXT_STYLE["body"])
        radius = 5 if block.get("element_id", "").startswith("answer-") else 7
        draw.rounded_rectangle(rect, radius=radius, fill=style["fill"], outline="#d6dee8", width=1)
        x1, y1, x2, y2 = rect
        if block.get("element_id", "").startswith("answer-"):
            draw.rectangle((x1, y1, x1 + 4, y2), fill=theme["accent"])
        is_answer = block.get("element_id", "").startswith("answer-")
        title_size = RENDER_TEXT_SIZES["answer_title"] if is_answer else RENDER_TEXT_SIZES["text_block_title"]
        body_size = RENDER_TEXT_SIZES["answer_body"] if is_answer else RENDER_TEXT_SIZES["text_block_body"]
        self._draw_text(draw, (x1 + 18, y1 + 12), block.get("title", ""), font=self._font("bold", title_size), fill=style["title"])
        subtitle = block.get("metadata", {}).get("subtitle")
        y_cursor = y1 + 38
        if subtitle:
            self._draw_text(draw, (x1 + 18, y_cursor), subtitle, font=self._font("regular", RENDER_TEXT_SIZES["text_block_subtitle"]), fill="#475569")
            y_cursor += 21
        for line in block.get("lines", []):
            for wrapped in self._wrap_text(line, self._font("regular", body_size), max(12, int((x2 - x1 - 36) / 8))):
                self._draw_text(draw, (x1 + 18, y_cursor), wrapped, font=self._font("regular", body_size), fill=style["text"])
                y_cursor += max(22, body_size + 8)

    def _draw_note_overlay(self, draw: ImageDraw.ImageDraw, scene: dict[str, Any], note: dict[str, Any]) -> None:
        surface = scene["surface"]
        box = (surface["width"] - 420, 118, surface["width"] - 48, 280)
        draw.rounded_rectangle(box, radius=14, fill="#f8fafc", outline="#cbd5e1", width=1)
        self._draw_text(draw, (box[0] + 18, box[1] + 16), note["title"], font=self._font("bold", RENDER_TEXT_SIZES["note_overlay_title"]), fill="#0f172a")
        y = box[1] + 46
        for line in self._wrap_text(note["text"], self._font("regular", RENDER_TEXT_SIZES["note_overlay_body"]), 28):
            self._draw_text(draw, (box[0] + 18, y), line, font=self._font("regular", RENDER_TEXT_SIZES["note_overlay_body"]), fill="#334155")
            y += 22

    def _draw_status_pill(
        self,
        draw: ImageDraw.ImageDraw,
        box: tuple[float, float, float, float],
        label: str,
        *,
        fill: str,
        text_fill: str,
        outline: str = "#d5dee9",
    ) -> None:
        draw.rounded_rectangle(box, radius=4, fill=fill, outline=outline, width=1)
        text_width, text_height = self._measure_text(label, self._font("bold", RENDER_TEXT_SIZES["status"]))
        x1, y1, x2, y2 = box
        self._draw_text(
            draw,
            (x1 + ((x2 - x1 - text_width) / 2), y1 + ((y2 - y1 - text_height) / 2) - 1),
            label,
            font=self._font("bold", RENDER_TEXT_SIZES["status"]),
            fill=text_fill,
        )

    def _draw_cell_text(self, draw: ImageDraw.ImageDraw, rect: tuple[float, float, float, float], text: str, style: dict[str, Any], align: str) -> None:
        text = str(text)
        if not text:
            return
        font = self._font(style["font"], int(style["size"]))
        x1, y1, x2, y2 = rect
        text_width, text_height = self._measure_text(text, font)
        if align == "left":
            x = x1 + 14
        elif align == "right":
            x = x2 - text_width - 14
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
