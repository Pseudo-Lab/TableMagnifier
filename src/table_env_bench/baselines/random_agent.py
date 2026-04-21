"""Random workbook navigation baseline."""

from __future__ import annotations

import random
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

from table_env_bench.env.actions import WorkbookAction


def _extract_visible_tokens(svg: str) -> list[str]:
    root = ET.fromstring(svg)
    tokens: list[str] = []
    for element in root.iter():
        if element.tag.endswith("text") and element.text and element.text.strip():
            tokens.append(element.text.strip())
    return tokens


@dataclass
class RandomAgent:
    seed: int = 0
    name: str = "random"
    rng: random.Random = field(init=False)

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)

    def reset(self, observation: dict[str, Any], info: dict[str, Any]) -> None:
        self.rng = random.Random(self.seed + info["level"])

    def act(self, observation: dict[str, Any], info: dict[str, Any]) -> WorkbookAction:
        tokens = _extract_visible_tokens(observation["viewport_svg"])
        numbers = [match.group(1) for token in tokens if (match := re.search(r"([+-]?\d+(?:\.\d+)?)", token.replace(",", "")))]
        remaining = observation["remaining_action_budget"]
        if remaining <= 1:
            guess = self.rng.choice(numbers) if numbers else "0"
            return WorkbookAction(type="submit_answer", text=guess)

        action_type = self.rng.choice(
            [
                "zoom_in",
                "zoom_out",
                "pan_up",
                "pan_down",
                "pan_left",
                "pan_right",
                "next_page",
                "prev_page",
                "click_region",
                "select_sheet",
            ]
        )
        if action_type == "select_sheet":
            return WorkbookAction(type="select_sheet", sheet=self.rng.choice(info["sheet_tabs"]))
        if action_type == "click_region":
            return WorkbookAction(
                type="click_region",
                x=float(self.rng.randint(120, 980)),
                y=float(self.rng.randint(120, 620)),
            )
        if self.rng.random() < 0.18 and numbers:
            return WorkbookAction(type="submit_answer", text=self.rng.choice(numbers))
        return WorkbookAction(type=action_type)
