"""Workbook action model and validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


ACTION_NAMES = {
    "select_sheet",
    "next_page",
    "prev_page",
    "zoom_in",
    "zoom_out",
    "pan_up",
    "pan_down",
    "pan_left",
    "pan_right",
    "click_region",
    "submit_answer",
}

LEGACY_ALIASES = {
    "open_sheet": "select_sheet",
    "click": "click_region",
}


def _normalize_action_name(raw_value: Any) -> str:
    if raw_value is None:
        return ""
    candidate = str(raw_value).strip()
    if not candidate:
        return ""
    lowered = candidate.lower()
    normalized = LEGACY_ALIASES.get(lowered, lowered)
    if normalized in ACTION_NAMES:
        return normalized
    return ""


@dataclass(frozen=True)
class WorkbookAction:
    type: str
    x: float | None = None
    y: float | None = None
    sheet: str | int | None = None
    text: str | None = None

    def compact(self) -> str:
        if self.type == "select_sheet":
            return f"select_sheet({self.sheet})"
        if self.type == "click_region":
            return f"click_region({int(self.x or 0)},{int(self.y or 0)})"
        if self.type == "submit_answer":
            return f"submit_answer({self.text})"
        return self.type

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"type": self.type}
        if self.x is not None:
            payload["x"] = self.x
        if self.y is not None:
            payload["y"] = self.y
        if self.sheet is not None:
            payload["sheet"] = self.sheet
        if self.text is not None:
            payload["text"] = self.text
        return payload


def parse_action(action: WorkbookAction | Mapping[str, Any]) -> WorkbookAction:
    if isinstance(action, WorkbookAction):
        parsed = action
    else:
        action_type = _normalize_action_name(action.get("type")) or _normalize_action_name(action.get("name"))
        action_type_from_text = False
        if not action_type:
            action_type = _normalize_action_name(action.get("text"))
            action_type_from_text = bool(action_type)
        sheet_value: str | int | None = None
        if "sheet" in action:
            raw_sheet = action["sheet"]
            sheet_value = int(raw_sheet) if isinstance(raw_sheet, int) else str(raw_sheet)
        elif "index" in action:
            raw_index = action["index"]
            sheet_value = int(raw_index) if isinstance(raw_index, int) else str(raw_index)
        elif "name" in action and action_type == "select_sheet":
            sheet_value = str(action["name"])

        parsed = WorkbookAction(
            type=action_type,
            x=float(action["x"]) if "x" in action else None,
            y=float(action["y"]) if "y" in action else None,
            sheet=sheet_value,
            text=str(action["text"]) if "text" in action and not action_type_from_text else None,
        )

    if parsed.type not in ACTION_NAMES:
        raise ValueError(f"Unsupported action: {parsed.type}")
    if parsed.type == "select_sheet" and parsed.sheet is None:
        raise ValueError("select_sheet requires sheet name or index")
    if parsed.type == "click_region" and (parsed.x is None or parsed.y is None):
        raise ValueError("click_region requires x and y")
    if parsed.type == "submit_answer" and parsed.text is None:
        raise ValueError("submit_answer requires text")
    return parsed


TableAction = WorkbookAction
