"""Scene serialization for canvas and image renderers."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from table_env_bench.data.models import NoteSpec, WorkbookSpec
from table_env_bench.render.layout import Rect
from table_env_bench.render.renderer import RenderConfig


def build_page_scene(
    workbook: WorkbookSpec,
    *,
    sheet_index: int,
    page_index: int,
    viewport: Rect,
    config: RenderConfig,
    overlay_note: NoteSpec | None = None,
    selected_region_id: str | None = None,
) -> dict[str, Any]:
    sheet = workbook.sheets[sheet_index]
    page = sheet.pages[page_index]
    return {
        "version": 1,
        "surface": {
            "width": config.viewport_width,
            "height": config.viewport_height,
            "header_height": config.header_height,
            "page_margin": config.page_margin,
        },
        "viewport": {
            "x": viewport.x,
            "y": viewport.y,
            "width": viewport.width,
            "height": viewport.height,
        },
        "workbook": {
            "title": workbook.title,
            "sheet_tabs": [item.tab_label for item in workbook.sheets],
            "active_sheet_index": sheet_index,
            "active_sheet_id": sheet.sheet_id,
        },
        "page": {
            "sheet_id": sheet.sheet_id,
            "sheet_tab_label": sheet.tab_label,
            "page_index": page_index,
            "page_id": page.page_id,
            "title": page.title,
            "width": page.width,
            "height": page.height,
            "elements": [element.to_dict() for element in page.elements],
            "regions": [region.to_dict() for region in page.regions],
            "notes": [note.to_dict() for note in page.notes],
        },
        "overlay_note": overlay_note.to_dict() if overlay_note is not None else None,
        "selected_region_id": selected_region_id,
    }
