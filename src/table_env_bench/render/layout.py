"""Workbook geometry helpers."""

from __future__ import annotations

from dataclasses import dataclass

from table_env_bench.data.models import PageSpec, RectSpec, RegionSpec, TableCellSpec, TableElementSpec


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    width: float
    height: float

    @property
    def center_x(self) -> float:
        return self.x + (self.width / 2)

    @property
    def center_y(self) -> float:
        return self.y + (self.height / 2)

    def contains(self, x: float, y: float) -> bool:
        return self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height

    @classmethod
    def from_spec(cls, rect: RectSpec) -> "Rect":
        return cls(x=rect.x, y=rect.y, width=rect.width, height=rect.height)


@dataclass(frozen=True)
class RegionLayout:
    region: RegionSpec
    rect: Rect


@dataclass(frozen=True)
class TableCellLayout:
    cell: TableCellSpec
    rect: Rect


def make_outer_viewbox(page: PageSpec, aspect_ratio: float) -> Rect:
    page_ratio = page.width / page.height
    if page_ratio >= aspect_ratio:
        width = float(page.width)
        height = width / aspect_ratio
    else:
        height = float(page.height)
        width = height * aspect_ratio
    return Rect(
        x=(page.width - width) / 2,
        y=(page.height - height) / 2,
        width=width,
        height=height,
    )


def find_region_at_point(page: PageSpec, x: float, y: float) -> RegionLayout | None:
    for region in page.regions:
        rect = Rect.from_spec(region.rect)
        if rect.contains(x, y):
            return RegionLayout(region=region, rect=rect)
    return None


def table_cell_layouts(table: TableElementSpec) -> tuple[TableCellLayout, ...]:
    rect = table.rect
    x_positions = [rect.x]
    for width in table.column_widths:
        x_positions.append(x_positions[-1] + width)

    y_positions = [rect.y]
    for height in table.row_heights:
        y_positions.append(y_positions[-1] + height)

    layouts: list[TableCellLayout] = []
    for cell in table.cells:
        cell_rect = Rect(
            x=float(x_positions[cell.col]),
            y=float(y_positions[cell.row]),
            width=float(sum(table.column_widths[cell.col : cell.col + cell.col_span])),
            height=float(sum(table.row_heights[cell.row : cell.row + cell.row_span])),
        )
        layouts.append(TableCellLayout(cell=cell, rect=cell_rect))
    return tuple(layouts)
