"""Rendering utilities for workbook scenes."""

from table_env_bench.render.layout import Rect, find_region_at_point, make_outer_viewbox, table_cell_layouts
from table_env_bench.render.renderer import RenderConfig, SvgWorkbookRenderer

SvgTableRenderer = SvgWorkbookRenderer

__all__ = [
    "Rect",
    "RenderConfig",
    "SvgWorkbookRenderer",
    "SvgTableRenderer",
    "find_region_at_point",
    "make_outer_viewbox",
    "table_cell_layouts",
]
