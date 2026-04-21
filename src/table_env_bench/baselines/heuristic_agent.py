"""Simple workbook-aware heuristic baseline."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

from table_env_bench.env.actions import WorkbookAction


@dataclass(frozen=True)
class TextNode:
    text: str
    x: float
    y: float


@dataclass(frozen=True)
class RectNode:
    x: float
    y: float
    width: float
    height: float
    fill: str

    @property
    def center_x(self) -> float:
        return self.x + (self.width / 2)

    @property
    def center_y(self) -> float:
        return self.y + (self.height / 2)


@dataclass(frozen=True)
class CircleNode:
    x: float
    y: float
    radius: float
    fill: str


@dataclass
class PageMemory:
    text_nodes: list[TextNode]
    rect_nodes: list[RectNode]
    circle_nodes: list[CircleNode]
    svg: str


def _parse_text_nodes(root: ET.Element) -> list[TextNode]:
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
    return nodes


def _parse_rect_nodes(root: ET.Element) -> list[RectNode]:
    rects: list[RectNode] = []
    for element in root.iter():
        if element.tag.endswith("rect"):
            rects.append(
                RectNode(
                    x=float(element.attrib.get("x", "0")),
                    y=float(element.attrib.get("y", "0")),
                    width=float(element.attrib.get("width", "0")),
                    height=float(element.attrib.get("height", "0")),
                    fill=str(element.attrib.get("fill", "")),
                )
            )
    return rects


def _parse_circle_nodes(root: ET.Element) -> list[CircleNode]:
    circles: list[CircleNode] = []
    for element in root.iter():
        if element.tag.endswith("circle"):
            circles.append(
                CircleNode(
                    x=float(element.attrib.get("cx", "0")),
                    y=float(element.attrib.get("cy", "0")),
                    radius=float(element.attrib.get("r", "0")),
                    fill=str(element.attrib.get("fill", "")),
                )
            )
    return circles


def _parse_svg(svg: str) -> PageMemory:
    root = ET.fromstring(svg)
    return PageMemory(
        text_nodes=_parse_text_nodes(root),
        rect_nodes=_parse_rect_nodes(root),
        circle_nodes=_parse_circle_nodes(root),
        svg=svg,
    )


def _extract_first_number(text: str) -> float | None:
    match = re.search(r"([+-]?\d+(?:\.\d+)?)", text.replace(",", ""))
    if not match:
        return None
    return float(match.group(1))


def _find_text(nodes: list[TextNode], substring: str) -> TextNode | None:
    return next((node for node in nodes if substring in node.text), None)


def _numbers_on_same_row(nodes: list[TextNode], label_substring: str) -> list[float]:
    label = _find_text(nodes, label_substring)
    if label is None:
        return []
    same_row = [node for node in nodes if abs(node.y - label.y) <= 16 and node.x > label.x]
    parsed: list[tuple[float, float]] = []
    for node in same_row:
        value = _extract_first_number(node.text)
        if value is not None:
            parsed.append((node.x, value))
    return [value for _, value in sorted(parsed)]


def _row_value(nodes: list[TextNode], label_substring: str) -> float | None:
    values = _numbers_on_same_row(nodes, label_substring)
    if not values:
        return None
    return values[0]


def _unit_multiplier(nodes: list[TextNode]) -> int:
    joined = " ".join(node.text for node in nodes)
    if "백만원" in joined:
        return 1_000_000
    if "억원" in joined:
        return 100_000_000
    if "만원" in joined:
        return 10_000
    return 1


def _joined_text(memory: PageMemory) -> str:
    return " ".join(node.text for node in memory.text_nodes)


def _extract_adjustment_from_text(text: str, keyword: str, unit_keyword: str = "억원") -> float | None:
    match = re.search(rf"{re.escape(keyword)}[^0-9+-]*([+-]?\d+(?:\.\d+)?)\s*{re.escape(unit_keyword)}", text)
    if match:
        return float(match.group(1))
    return None


def _category_texts(memory: PageMemory) -> list[TextNode]:
    return [
        node
        for node in memory.text_nodes
        if re.search(r"(월|분기)$", node.text) and 520 <= node.y <= 620
    ]


def _legend_map(memory: PageMemory) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for rect in memory.rect_nodes:
        if 12 <= rect.width <= 24 and 12 <= rect.height <= 24 and rect.x >= 880 and rect.y >= 200:
            candidates = [node for node in memory.text_nodes if abs(node.y - rect.center_y) <= 16 and node.x > rect.x]
            if candidates:
                nearest = min(candidates, key=lambda node: node.x - rect.x)
                mapping[nearest.text] = rect.fill
    return mapping


def _highest_bar_category(memory: PageMemory, series_name: str) -> str | None:
    legend = _legend_map(memory)
    color = legend.get(series_name)
    if color is None:
        return None
    bars = [
        rect
        for rect in memory.rect_nodes
        if rect.fill == color and 16 <= rect.width <= 120 and rect.height >= 24 and 120 <= rect.x <= 860 and 160 <= rect.y <= 560
    ]
    if not bars:
        return None
    target = max(bars, key=lambda item: item.height)
    categories = _category_texts(memory)
    if not categories:
        return None
    closest = min(categories, key=lambda node: abs(node.x - target.center_x))
    return closest.text


def _highest_line_category(memory: PageMemory, series_name: str) -> str | None:
    legend = _legend_map(memory)
    color = legend.get(series_name)
    if color is None:
        return None
    points = [circle for circle in memory.circle_nodes if circle.fill == color and 100 <= circle.x <= 860 and 160 <= circle.y <= 560]
    if not points:
        return None
    target = min(points, key=lambda item: item.y)
    categories = _category_texts(memory)
    if not categories:
        return None
    closest = min(categories, key=lambda node: abs(node.x - target.x))
    return closest.text


@dataclass
class HeuristicAgent:
    name: str = "heuristic"
    family: str | None = field(init=False, default=None)
    question: str | None = field(init=False, default=None)
    sheet_tabs: list[str] = field(init=False, default_factory=list)
    sheet_page_counts: list[int] = field(init=False, default_factory=list)
    visited: dict[tuple[int, int], PageMemory] = field(init=False, default_factory=dict)

    def reset(self, observation: dict[str, Any], info: dict[str, Any]) -> None:
        self.family = info["family"]
        self.question = observation["question"]
        self.sheet_tabs = list(info["sheet_tabs"])
        self.sheet_page_counts = list(info["sheet_page_counts"])
        self.visited = {}

    def act(self, observation: dict[str, Any], info: dict[str, Any]) -> WorkbookAction:
        current_sheet = int(observation["current_sheet_index"])
        current_page = int(observation["current_page_index"])
        self.visited[(current_sheet, current_page)] = _parse_svg(observation["viewport_svg"])

        next_target = self._next_unvisited_target()
        if next_target is not None:
            target_sheet, target_page = next_target
            if current_sheet != target_sheet:
                return WorkbookAction(type="select_sheet", sheet=self.sheet_tabs[target_sheet])
            if current_page < target_page:
                return WorkbookAction(type="next_page")
            if current_page > target_page:
                return WorkbookAction(type="prev_page")

        answer = self._solve()
        return WorkbookAction(type="submit_answer", text=str(answer if answer is not None else 0))

    def _next_unvisited_target(self) -> tuple[int, int] | None:
        for sheet_index, page_count in enumerate(self.sheet_page_counts):
            for page_index in range(page_count):
                if (sheet_index, page_index) not in self.visited:
                    return sheet_index, page_index
        return None

    def _all_pages(self) -> list[PageMemory]:
        return [self.visited[key] for key in sorted(self.visited)]

    def _solve(self) -> int | None:
        if self.family == "summary_appendix_override":
            return self._solve_summary_appendix()
        if self.family == "chart_to_detail_lookup":
            return self._solve_chart_lookup()
        if self.family == "scale_shift_cross_sheet":
            return self._solve_scale_shift()
        return None

    def _solve_summary_appendix(self) -> int | None:
        target_label = "서비스 영업이익" if "서비스 영업이익" in (self.question or "") else "영업이익"
        shown_value = None
        adjustment = None

        for memory in self._all_pages():
            shown_value = shown_value if shown_value is not None else _row_value(memory.text_nodes, target_label)
            adjustment_label = f"{target_label} 조정"
            if adjustment is None:
                row_adjustment = _row_value(memory.text_nodes, adjustment_label)
                if row_adjustment is not None:
                    adjustment = row_adjustment
            if adjustment is None:
                text_adjustment = _extract_adjustment_from_text(_joined_text(memory), adjustment_label)
                if text_adjustment is not None:
                    adjustment = text_adjustment
            if shown_value is not None and adjustment is not None:
                break

        if shown_value is None or adjustment is None:
            return None
        return int(round((shown_value + adjustment) * 100_000_000))

    def _solve_chart_lookup(self) -> int | None:
        series_name = "온라인"
        if "제품 B" in (self.question or ""):
            series_name = "제품 B"
        elif "플랫폼" in (self.question or ""):
            series_name = "플랫폼"

        target_period = None
        for memory in self._all_pages():
            target_period = _highest_bar_category(memory, series_name)
            if target_period is None:
                target_period = _highest_line_category(memory, series_name)
            if target_period is not None:
                break

        if target_period is None:
            return None

        candidates: list[float] = []
        for memory in self._all_pages():
            value = _row_value(memory.text_nodes, target_period)
            if value is not None:
                candidates.append(value)
        if not candidates:
            return None
        return int(round(max(candidates)))

    def _solve_scale_shift(self) -> int | None:
        question = self.question or ""
        if "클라우드" in question:
            summary_label = "2분기 클라우드 매출"
            detail_label = "1분기 클라우드 매출"
            adjustment = 0.0
        elif "서비스" in question:
            summary_label = "상반기 서비스 매출"
            detail_label = "하반기 서비스 매출"
            adjustment = 0.0
        else:
            summary_label = "1분기 플랫폼 계약액"
            detail_label = "2분기 플랫폼 계약액"
            adjustment = 0.0

        summary_value = None
        detail_value = None
        summary_multiplier = None
        detail_multiplier = None

        for memory in self._all_pages():
            if summary_value is None:
                value = _row_value(memory.text_nodes, summary_label)
                if value is not None:
                    summary_value = value
                    summary_multiplier = _unit_multiplier(memory.text_nodes)
            if detail_value is None:
                value = _row_value(memory.text_nodes, detail_label)
                if value is not None:
                    detail_value = value
                    detail_multiplier = _unit_multiplier(memory.text_nodes)
            if "파일럿 매출" in _joined_text(memory):
                match = re.search(r"파일럿 매출\s+(\d+(?:\.\d+)?)백만원", _joined_text(memory))
                if match:
                    adjustment = float(match.group(1))

        if summary_value is None or detail_value is None or summary_multiplier is None or detail_multiplier is None:
            return None

        adjusted_detail = detail_value - adjustment
        return int(round((summary_value * summary_multiplier) + (adjusted_detail * detail_multiplier)))
