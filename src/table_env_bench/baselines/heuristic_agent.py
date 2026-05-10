"""Simple workbook traversal baseline."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

from table_env_bench.env.actions import WorkbookAction


@dataclass(frozen=True)
class TextNode:
    text: str
    x: float
    y: float


@dataclass
class PageMemory:
    text_nodes: list[TextNode]
    svg: str


def _parse_svg(svg: str) -> PageMemory:
    root = ET.fromstring(svg)
    nodes: list[TextNode] = []
    for element in root.iter():
        if element.tag.endswith("text") and element.text and element.text.strip():
            nodes.append(
                TextNode(
                    text=element.text.strip(),
                    x=float(element.attrib.get("x", "0")),
                    y=float(element.attrib.get("y", "0")),
                )
            )
    return PageMemory(text_nodes=nodes, svg=svg)


@dataclass
class HeuristicAgent:
    name: str = "heuristic"
    sheet_tabs: list[str] = field(init=False, default_factory=list)
    sheet_page_counts: list[int] = field(init=False, default_factory=list)
    visited: set[tuple[int, int]] = field(init=False, default_factory=set)

    def reset(self, observation: dict[str, Any], info: dict[str, Any]) -> None:
        self.sheet_tabs = list(info["sheet_tabs"])
        self.sheet_page_counts = list(info["sheet_page_counts"])
        self.visited = set()

    def act(self, observation: dict[str, Any], info: dict[str, Any]) -> WorkbookAction:
        current_sheet = int(observation["current_sheet_index"])
        current_page = int(observation["current_page_index"])
        self.visited.add((current_sheet, current_page))

        next_target = self._next_unvisited_target()
        if next_target is not None:
            target_sheet, target_page = next_target
            if current_sheet != target_sheet:
                return WorkbookAction(type="select_sheet", sheet=self.sheet_tabs[target_sheet])
            if current_page < target_page:
                return WorkbookAction(type="next_page")
            if current_page > target_page:
                return WorkbookAction(type="prev_page")

        choices = [node.text for node in _parse_svg(observation["viewport_svg"]).text_nodes if node.text in {"A", "B", "C", "D"}]
        return WorkbookAction(type="submit_answer", text=choices[0] if choices else "0")

    def _next_unvisited_target(self) -> tuple[int, int] | None:
        for sheet_index, page_count in enumerate(self.sheet_page_counts):
            for page_index in range(page_count):
                if (sheet_index, page_index) not in self.visited:
                    return sheet_index, page_index
        return None
