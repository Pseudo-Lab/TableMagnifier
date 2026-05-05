"""Declarative workbook benchmark spec models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _tuple_of_strings(values: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    return tuple(str(value) for value in (values or ()))


def _tuple_of_floats(values: list[float] | tuple[float, ...] | None) -> tuple[float, ...]:
    return tuple(float(value) for value in (values or ()))


def _tuple_of_ints(values: list[int] | tuple[int, ...] | None) -> tuple[int, ...]:
    return tuple(int(value) for value in (values or ()))


@dataclass(frozen=True)
class RectSpec:
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

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RectSpec":
        return cls(
            x=float(payload["x"]),
            y=float(payload["y"]),
            width=float(payload["width"]),
            height=float(payload["height"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


@dataclass(frozen=True)
class NoteSpec:
    id: str
    title: str
    text: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "NoteSpec":
        return cls(
            id=str(payload["id"]),
            title=str(payload.get("title", payload["id"])),
            text=str(payload["text"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "title": self.title, "text": self.text}


@dataclass(frozen=True)
class RegionSpec:
    public_id: str
    role: str
    label: str
    rect: RectSpec
    linked_note_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RegionSpec":
        return cls(
            public_id=str(payload["public_id"]),
            role=str(payload["role"]),
            label=str(payload.get("label", payload["public_id"])),
            rect=RectSpec.from_dict(payload["rect"]),
            linked_note_id=str(payload["linked_note_id"]) if payload.get("linked_note_id") is not None else None,
            metadata=dict(payload.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "public_id": self.public_id,
            "role": self.role,
            "label": self.label,
            "rect": self.rect.to_dict(),
        }
        if self.linked_note_id is not None:
            payload["linked_note_id"] = self.linked_note_id
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


@dataclass(frozen=True)
class TableCellSpec:
    row: int
    col: int
    text: str
    row_span: int = 1
    col_span: int = 1
    style: str = "body"
    align: str = "center"
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TableCellSpec":
        return cls(
            row=int(payload["row"]),
            col=int(payload["col"]),
            text=str(payload["text"]),
            row_span=int(payload.get("row_span", 1)),
            col_span=int(payload.get("col_span", 1)),
            style=str(payload.get("style", "body")),
            align=str(payload.get("align", "center")),
            metadata=dict(payload.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "row": self.row,
            "col": self.col,
            "text": self.text,
            "row_span": self.row_span,
            "col_span": self.col_span,
            "style": self.style,
            "align": self.align,
        }
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


@dataclass(frozen=True)
class TableElementSpec:
    element_id: str
    rect: RectSpec
    title: str
    n_rows: int
    n_cols: int
    column_widths: tuple[int, ...]
    row_heights: tuple[int, ...]
    cells: tuple[TableCellSpec, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    type: str = field(init=False, default="table")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TableElementSpec":
        return cls(
            element_id=str(payload["element_id"]),
            rect=RectSpec.from_dict(payload["rect"]),
            title=str(payload.get("title", "")),
            n_rows=int(payload["n_rows"]),
            n_cols=int(payload["n_cols"]),
            column_widths=_tuple_of_ints(payload["column_widths"]),
            row_heights=_tuple_of_ints(payload["row_heights"]),
            cells=tuple(TableCellSpec.from_dict(item) for item in payload["cells"]),
            metadata=dict(payload.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": self.type,
            "element_id": self.element_id,
            "rect": self.rect.to_dict(),
            "title": self.title,
            "n_rows": self.n_rows,
            "n_cols": self.n_cols,
            "column_widths": list(self.column_widths),
            "row_heights": list(self.row_heights),
            "cells": [cell.to_dict() for cell in self.cells],
        }
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


@dataclass(frozen=True)
class ChartSeriesSpec:
    name: str
    color: str
    values: tuple[float, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ChartSeriesSpec":
        return cls(
            name=str(payload["name"]),
            color=str(payload["color"]),
            values=_tuple_of_floats(payload["values"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "color": self.color, "values": list(self.values)}


@dataclass(frozen=True)
class ChartElementSpec:
    element_id: str
    rect: RectSpec
    chart_type: str
    title: str
    categories: tuple[str, ...]
    series: tuple[ChartSeriesSpec, ...]
    y_axis_label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    type: str = field(init=False, default="chart")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ChartElementSpec":
        return cls(
            element_id=str(payload["element_id"]),
            rect=RectSpec.from_dict(payload["rect"]),
            chart_type=str(payload["chart_type"]),
            title=str(payload.get("title", "")),
            categories=_tuple_of_strings(payload["categories"]),
            series=tuple(ChartSeriesSpec.from_dict(item) for item in payload["series"]),
            y_axis_label=str(payload.get("y_axis_label", "")),
            metadata=dict(payload.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": self.type,
            "element_id": self.element_id,
            "rect": self.rect.to_dict(),
            "chart_type": self.chart_type,
            "title": self.title,
            "categories": list(self.categories),
            "series": [item.to_dict() for item in self.series],
            "y_axis_label": self.y_axis_label,
        }
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


@dataclass(frozen=True)
class LegendItemSpec:
    label: str
    color: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LegendItemSpec":
        return cls(label=str(payload["label"]), color=str(payload["color"]))

    def to_dict(self) -> dict[str, Any]:
        return {"label": self.label, "color": self.color}


@dataclass(frozen=True)
class LegendElementSpec:
    element_id: str
    rect: RectSpec
    title: str
    items: tuple[LegendItemSpec, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    type: str = field(init=False, default="legend")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LegendElementSpec":
        return cls(
            element_id=str(payload["element_id"]),
            rect=RectSpec.from_dict(payload["rect"]),
            title=str(payload.get("title", "")),
            items=tuple(LegendItemSpec.from_dict(item) for item in payload["items"]),
            metadata=dict(payload.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": self.type,
            "element_id": self.element_id,
            "rect": self.rect.to_dict(),
            "title": self.title,
            "items": [item.to_dict() for item in self.items],
        }
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


@dataclass(frozen=True)
class TextBlockElementSpec:
    element_id: str
    rect: RectSpec
    title: str
    lines: tuple[str, ...]
    style: str = "body"
    metadata: dict[str, Any] = field(default_factory=dict)

    type: str = field(init=False, default="text_block")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TextBlockElementSpec":
        return cls(
            element_id=str(payload["element_id"]),
            rect=RectSpec.from_dict(payload["rect"]),
            title=str(payload.get("title", "")),
            lines=_tuple_of_strings(payload.get("lines")),
            style=str(payload.get("style", "body")),
            metadata=dict(payload.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": self.type,
            "element_id": self.element_id,
            "rect": self.rect.to_dict(),
            "title": self.title,
            "lines": list(self.lines),
            "style": self.style,
        }
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


PageElementSpec = TableElementSpec | ChartElementSpec | LegendElementSpec | TextBlockElementSpec


def element_from_dict(payload: dict[str, Any]) -> PageElementSpec:
    element_type = str(payload["type"])
    if element_type == "table":
        return TableElementSpec.from_dict(payload)
    if element_type == "chart":
        return ChartElementSpec.from_dict(payload)
    if element_type == "legend":
        return LegendElementSpec.from_dict(payload)
    if element_type == "text_block":
        return TextBlockElementSpec.from_dict(payload)
    raise ValueError(f"Unsupported element type: {element_type}")


@dataclass(frozen=True)
class PageSpec:
    page_id: str
    title: str
    width: int
    height: int
    elements: tuple[PageElementSpec, ...]
    regions: tuple[RegionSpec, ...]
    notes: tuple[NoteSpec, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PageSpec":
        return cls(
            page_id=str(payload["page_id"]),
            title=str(payload["title"]),
            width=int(payload.get("width", 1280)),
            height=int(payload.get("height", 900)),
            elements=tuple(element_from_dict(item) for item in payload.get("elements", [])),
            regions=tuple(RegionSpec.from_dict(item) for item in payload.get("regions", [])),
            notes=tuple(NoteSpec.from_dict(item) for item in payload.get("notes", [])),
            metadata=dict(payload.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "page_id": self.page_id,
            "title": self.title,
            "width": self.width,
            "height": self.height,
            "elements": [element.to_dict() for element in self.elements],
            "regions": [region.to_dict() for region in self.regions],
        }
        if self.notes:
            payload["notes"] = [note.to_dict() for note in self.notes]
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


@dataclass(frozen=True)
class SheetSpec:
    sheet_id: str
    tab_label: str
    pages: tuple[PageSpec, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SheetSpec":
        return cls(
            sheet_id=str(payload["sheet_id"]),
            tab_label=str(payload.get("tab_label", payload["sheet_id"])),
            pages=tuple(PageSpec.from_dict(item) for item in payload["pages"]),
            metadata=dict(payload.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "sheet_id": self.sheet_id,
            "tab_label": self.tab_label,
            "pages": [page.to_dict() for page in self.pages],
        }
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


@dataclass(frozen=True)
class WorkbookSpec:
    workbook_id: str
    title: str
    sheets: tuple[SheetSpec, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WorkbookSpec":
        return cls(
            workbook_id=str(payload.get("workbook_id", "workbook")),
            title=str(payload["title"]),
            sheets=tuple(SheetSpec.from_dict(item) for item in payload["sheets"]),
            metadata=dict(payload.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "workbook_id": self.workbook_id,
            "title": self.title,
            "sheets": [sheet.to_dict() for sheet in self.sheets],
        }
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


@dataclass(frozen=True)
class AnswerSpec:
    canonical: str
    accepted: tuple[str, ...] = ()
    normalizer: str = "basic"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AnswerSpec":
        return cls(
            canonical=str(payload["canonical"]),
            accepted=_tuple_of_strings(payload.get("accepted")),
            normalizer=str(payload.get("normalizer", "basic")),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"canonical": self.canonical, "normalizer": self.normalizer}
        if self.accepted:
            payload["accepted"] = list(self.accepted)
        return payload


@dataclass(frozen=True)
class EpisodeSpec:
    episode_id: str
    family: str
    family_display_name: str
    level: int
    seed: int
    locale: str
    question: str
    workbook: WorkbookSpec
    answer: AnswerSpec
    max_actions: int = 12
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def sheets(self) -> tuple[SheetSpec, ...]:
        return self.workbook.sheets

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EpisodeSpec":
        workbook_payload = payload.get("workbook")
        if workbook_payload is None:
            raise ValueError("EpisodeSpec requires a workbook field")
        return cls(
            episode_id=str(payload["episode_id"]),
            family=str(payload["family"]),
            family_display_name=str(payload.get("family_display_name", payload["family"])),
            level=int(payload["level"]),
            seed=int(payload.get("seed", 0)),
            locale=str(payload.get("locale", "ko-KR")),
            question=str(payload["question"]),
            workbook=WorkbookSpec.from_dict(workbook_payload),
            answer=AnswerSpec.from_dict(payload["answer"]),
            max_actions=int(payload.get("max_actions", 12)),
            metadata=dict(payload.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "episode_id": self.episode_id,
            "family": self.family,
            "family_display_name": self.family_display_name,
            "level": self.level,
            "seed": self.seed,
            "locale": self.locale,
            "question": self.question,
            "workbook": self.workbook.to_dict(),
            "answer": self.answer.to_dict(),
            "max_actions": self.max_actions,
        }
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload
