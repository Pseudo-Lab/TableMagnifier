"""Restricted baselines for shortcut-resistant evaluation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from table_env_bench.baselines.heuristic_agent import _parse_svg
from table_env_bench.env.actions import WorkbookAction


def _visible_tokens(svg: str) -> list[str]:
    memory = _parse_svg(svg)
    return [node.text for node in memory.text_nodes]


def _visible_numbers(svg: str) -> list[str]:
    values: list[str] = []
    for token in _visible_tokens(svg):
        match = re.search(r"([+-]?\d+(?:\.\d+)?)", token.replace(",", ""))
        if match:
            values.append(match.group(1))
    return values


def _visible_choices(svg: str) -> list[str]:
    choices: list[str] = []
    for token in _visible_tokens(svg):
        match = re.search(r"선택지\s*([A-D])", token, re.IGNORECASE)
        if match:
            choice = match.group(1).upper()
            if choice not in choices:
                choices.append(choice)
    return choices


@dataclass
class SinglePageAgent:
    name: str = "single_page"
    submitted: bool = field(init=False, default=False)

    def reset(self, observation: dict[str, Any], info: dict[str, Any]) -> None:
        self.submitted = False

    def act(self, observation: dict[str, Any], info: dict[str, Any]) -> WorkbookAction:
        if not self.submitted:
            self.submitted = True
            choices = _visible_choices(observation["viewport_svg"])
            if choices:
                return WorkbookAction(type="submit_answer", text=choices[0])
            numbers = _visible_numbers(observation["viewport_svg"])
            return WorkbookAction(type="submit_answer", text=numbers[0] if numbers else "0")
        return WorkbookAction(type="submit_answer", text="0")


@dataclass
class NoNoteAgent:
    name: str = "no_note"
    family: str | None = field(init=False, default=None)

    def reset(self, observation: dict[str, Any], info: dict[str, Any]) -> None:
        self.family = info["family"]

    def act(self, observation: dict[str, Any], info: dict[str, Any]) -> WorkbookAction:
        current_sheet = int(observation["current_sheet_index"])
        current_page = int(observation["current_page_index"])
        last_sheet = len(info["sheet_tabs"]) - 1
        if current_sheet < last_sheet:
            return WorkbookAction(type="select_sheet", sheet=info["sheet_tabs"][last_sheet])
        if current_page < observation["page_count_in_sheet"] - 1:
            return WorkbookAction(type="next_page")
        choices = _visible_choices(observation["viewport_svg"])
        if choices:
            return WorkbookAction(type="submit_answer", text=choices[0])
        numbers = _visible_numbers(observation["viewport_svg"])
        return WorkbookAction(type="submit_answer", text=numbers[0] if numbers else "0")


@dataclass
class TextScrapeHeuristicAgent:
    name: str = "text_scrape"

    def reset(self, observation: dict[str, Any], info: dict[str, Any]) -> None:
        return None

    def act(self, observation: dict[str, Any], info: dict[str, Any]) -> WorkbookAction:
        current_sheet = int(observation["current_sheet_index"])
        current_page = int(observation["current_page_index"])
        if current_sheet < len(info["sheet_tabs"]) - 1:
            return WorkbookAction(type="select_sheet", sheet=info["sheet_tabs"][current_sheet + 1])
        if current_page < observation["page_count_in_sheet"] - 1:
            return WorkbookAction(type="next_page")
        tokens = _visible_tokens(observation["viewport_svg"])
        choices = _visible_choices(observation["viewport_svg"])
        if choices:
            for choice in ("B", "C", "A", "D"):
                if choice in choices:
                    return WorkbookAction(type="submit_answer", text=choice)
        for token in reversed(tokens):
            if re.fullmatch(r"[A-D]", token.strip(), re.IGNORECASE):
                return WorkbookAction(type="submit_answer", text=token.strip().upper())
        numbers = _visible_numbers(observation["viewport_svg"])
        return WorkbookAction(type="submit_answer", text=numbers[-1] if numbers else "0")


@dataclass
class GreedySubmitAgent:
    name: str = "greedy_submit"
    seen_first_page: bool = field(init=False, default=False)

    def reset(self, observation: dict[str, Any], info: dict[str, Any]) -> None:
        self.seen_first_page = False

    def act(self, observation: dict[str, Any], info: dict[str, Any]) -> WorkbookAction:
        if not self.seen_first_page:
            self.seen_first_page = True
            current_sheet = int(observation["current_sheet_index"])
            current_page = int(observation["current_page_index"])
            if current_page < observation["page_count_in_sheet"] - 1:
                return WorkbookAction(type="next_page")
            if current_sheet < len(info["sheet_tabs"]) - 1:
                return WorkbookAction(type="select_sheet", sheet=info["sheet_tabs"][current_sheet + 1])

        choices = _visible_choices(observation["viewport_svg"])
        if choices:
            return WorkbookAction(type="submit_answer", text=choices[0])
        numbers = _visible_numbers(observation["viewport_svg"])
        return WorkbookAction(type="submit_answer", text=numbers[0] if numbers else "0")
