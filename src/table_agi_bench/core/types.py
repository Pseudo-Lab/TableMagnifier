from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

AnswerType = Literal["string", "integer", "float", "boolean", "ordered_list", "unordered_set"]
Direction = Literal["up", "down", "left", "right"]


class ActionType(str, Enum):
    MOVE_CURSOR = "move_cursor"
    MOVE_VIEWPORT = "move_viewport"
    ZOOM = "zoom"
    SELECT = "select"
    ANSWER = "answer"
    NOOP = "noop"


@dataclass(frozen=True)
class Action:
    type: ActionType
    direction: Direction | None = None
    steps: int = 1
    value: Any | None = None

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "Action":
        raw_type = payload.get("type", "noop")
        try:
            action_type = ActionType(raw_type)
        except ValueError:
            return Action(type=ActionType.NOOP, value={"invalid_type": raw_type})

        steps = payload.get("steps", 1)
        if not isinstance(steps, int) or steps < 1:
            steps = 1
        return Action(
            type=action_type,
            direction=payload.get("direction"),
            steps=steps,
            value=payload.get("value"),
        )


@dataclass
class Cell:
    text: str
    bg: str = "#ffffff"
    fg: str = "#111111"
    bold: bool = False

    @staticmethod
    def from_any(value: Any) -> "Cell":
        if isinstance(value, Cell):
            return value
        if isinstance(value, dict):
            return Cell(
                text=str(value.get("text", "")),
                bg=str(value.get("bg", "#ffffff")),
                fg=str(value.get("fg", "#111111")),
                bold=bool(value.get("bold", False)),
            )
        return Cell(text=str(value))

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "bg": self.bg, "fg": self.fg, "bold": self.bold}


@dataclass
class TaskSpec:
    task_id: str
    split: str
    question: str
    answer: Any
    answer_type: AnswerType
    table: list[list[Cell]]
    tags: list[str] = field(default_factory=list)
    max_actions: int = 100
    seed: int | None = None
    tolerance: float | None = None
    human_mean_actions: float | None = None
    human_second_best_actions: float | None = None
    human_median_actions: float | None = None
    private_metadata: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "TaskSpec":
        rows = payload["table"]["rows"]
        table = [[Cell.from_any(cell) for cell in row] for row in rows]
        return TaskSpec(
            task_id=payload["task_id"],
            split=payload.get("split", "dev"),
            question=payload["question"],
            answer=payload["answer"],
            answer_type=payload.get("answer_type", "string"),
            table=table,
            tags=list(payload.get("tags", [])),
            max_actions=int(payload.get("max_actions", 100)),
            seed=payload.get("seed"),
            tolerance=payload.get("tolerance"),
            human_mean_actions=payload.get("human_mean_actions"),
            human_second_best_actions=payload.get("human_second_best_actions"),
            human_median_actions=payload.get("human_median_actions"),
            private_metadata=dict(payload.get("private_metadata", {})),
        )

    def to_private_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "split": self.split,
            "seed": self.seed,
            "question": self.question,
            "answer": self.answer,
            "answer_type": self.answer_type,
            "tolerance": self.tolerance,
            "table": {"rows": [[cell.to_dict() for cell in row] for row in self.table]},
            "tags": self.tags,
            "max_actions": self.max_actions,
            "human_mean_actions": self.human_mean_actions,
            "human_second_best_actions": self.human_second_best_actions,
            "human_median_actions": self.human_median_actions,
            "private_metadata": self.private_metadata,
        }


@dataclass
class Observation:
    task_id: str
    question: str
    image_path: str
    action_count: int
    max_actions: int
    valid_actions: list[str]
    done: bool = False
    feedback: str | None = None

    def to_agent_payload(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "question": self.question,
            "image_path": self.image_path,
            "action_count": self.action_count,
            "max_actions": self.max_actions,
            "valid_actions": self.valid_actions,
            "done": self.done,
            "feedback": self.feedback,
        }
