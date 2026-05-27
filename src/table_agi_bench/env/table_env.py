from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from table_agi_bench.core.types import Action, ActionType, Observation, TaskSpec
from table_agi_bench.env.renderer import TableRenderer
from table_agi_bench.eval.metrics import is_correct_answer


class TableAGIEnv:
    """Turn-based Table-AGI environment.

    Agent-facing observations contain image paths and safe metadata only.
    Raw table values and reference answers remain inside this object.
    """

    def __init__(
        self,
        task: TaskSpec,
        run_dir: str | Path,
        viewport_rows: int = 12,
        viewport_cols: int = 6,
        renderer: TableRenderer | None = None,
    ) -> None:
        self.task = task
        self.run_dir = Path(run_dir)
        self.viewport_rows = viewport_rows
        self.viewport_cols = viewport_cols
        self.renderer = renderer or TableRenderer()
        self.valid_actions = [a.value for a in ActionType]
        self.trace: list[dict[str, Any]] = []
        self.reset()

    def reset(self) -> Observation:
        self.action_count = 0
        self.cursor_row = 0
        self.cursor_col = 0
        self.viewport_row = 0
        self.viewport_col = 0
        self.zoom = 1
        self.done = False
        self.submitted_answer: Any | None = None
        self.correct: bool | None = None
        self.trace.clear()
        return self._observe(feedback=None)

    @property
    def n_rows(self) -> int:
        return len(self.task.table)

    @property
    def n_cols(self) -> int:
        return max((len(row) for row in self.task.table), default=0)

    def step(self, payload: dict[str, Any] | Action) -> Observation:
        action = payload if isinstance(payload, Action) else Action.from_dict(payload)

        if self.done:
            obs = self._observe(feedback="already_done")
            self.trace[-1]["action"] = self._action_to_dict(action)
            self.trace[-1]["ignored_post_terminal"] = True
            self.trace[-1]["submitted_answer"] = self.submitted_answer
            self.trace[-1]["correct"] = self.correct
            return obs

        self.action_count += 1
        feedback = "ok"

        if action.type == ActionType.MOVE_CURSOR:
            feedback = self._move_cursor(action.direction, action.steps)
        elif action.type == ActionType.MOVE_VIEWPORT:
            feedback = self._move_viewport(action.direction, action.steps)
        elif action.type == ActionType.ZOOM:
            feedback = self._zoom(action.value)
        elif action.type == ActionType.SELECT:
            # Selection is represented visually by the cursor. Future versions can add image-only crop views.
            feedback = "selected"
        elif action.type == ActionType.ANSWER:
            self.done = True
            self.submitted_answer = action.value
            self.correct = is_correct_answer(
                submitted=action.value,
                reference=self.task.answer,
                answer_type=self.task.answer_type,
                tolerance=self.task.tolerance,
            )
            feedback = "terminal_correct" if self.correct else "terminal_incorrect"
        elif action.type == ActionType.NOOP:
            if isinstance(action.value, dict) and "invalid_type" in action.value:
                feedback = "invalid_action_type"
            else:
                feedback = "noop"

        if self.action_count >= self.task.max_actions and not self.done:
            self.done = True
            self.correct = False
            feedback = "max_actions_exceeded"

        obs = self._observe(feedback=feedback)
        self.trace[-1]["action"] = self._action_to_dict(action)
        self.trace[-1]["submitted_answer"] = self.submitted_answer
        self.trace[-1]["correct"] = self.correct
        return obs

    def _move_cursor(self, direction: str | None, steps: int) -> str:
        if direction not in {"up", "down", "left", "right"}:
            return "invalid_direction"
        if direction == "up":
            self.cursor_row = max(0, self.cursor_row - steps)
        elif direction == "down":
            self.cursor_row = min(max(0, self.n_rows - 1), self.cursor_row + steps)
        elif direction == "left":
            self.cursor_col = max(0, self.cursor_col - steps)
        elif direction == "right":
            self.cursor_col = min(max(0, self.n_cols - 1), self.cursor_col + steps)
        self._ensure_cursor_visible()
        return "ok"

    def _move_viewport(self, direction: str | None, steps: int) -> str:
        if direction not in {"up", "down", "left", "right"}:
            return "invalid_direction"
        row_page = max(1, self.viewport_rows // 2)
        col_page = max(1, self.viewport_cols // 2)
        if direction == "up":
            self.viewport_row = max(0, self.viewport_row - steps * row_page)
        elif direction == "down":
            self.viewport_row = min(max(0, self.n_rows - self.viewport_rows), self.viewport_row + steps * row_page)
        elif direction == "left":
            self.viewport_col = max(0, self.viewport_col - steps * col_page)
        elif direction == "right":
            self.viewport_col = min(max(0, self.n_cols - self.viewport_cols), self.viewport_col + steps * col_page)
        return "ok"

    def _zoom(self, value: Any) -> str:
        if value == "in":
            self.zoom = min(2, self.zoom + 1)
            return "ok"
        if value == "out":
            self.zoom = max(1, self.zoom - 1)
            return "ok"
        return "invalid_zoom"

    def _ensure_cursor_visible(self) -> None:
        if self.cursor_row < self.viewport_row:
            self.viewport_row = self.cursor_row
        if self.cursor_row >= self.viewport_row + self.viewport_rows:
            self.viewport_row = self.cursor_row - self.viewport_rows + 1
        if self.cursor_col < self.viewport_col:
            self.viewport_col = self.cursor_col
        if self.cursor_col >= self.viewport_col + self.viewport_cols:
            self.viewport_col = self.cursor_col - self.viewport_cols + 1

    def _observe(self, feedback: str | None) -> Observation:
        image_path = self.run_dir / self.task.task_id / f"obs_{self.action_count:04d}.png"
        self.renderer.render_viewport(
            table=self.task.table,
            out_path=image_path,
            viewport_row=self.viewport_row,
            viewport_col=self.viewport_col,
            viewport_rows=self.viewport_rows,
            viewport_cols=self.viewport_cols,
            cursor_row=self.cursor_row,
            cursor_col=self.cursor_col,
            zoom=self.zoom,
            visual_metadata=self.task.private_metadata,
        )
        image_sha256 = hashlib.sha256(Path(image_path).read_bytes()).hexdigest()
        obs = Observation(
            task_id=self.task.task_id,
            question=self.task.question,
            image_path=str(image_path),
            action_count=self.action_count,
            max_actions=self.task.max_actions,
            valid_actions=self.valid_actions,
            done=self.done,
            feedback=feedback,
        )
        self.trace.append(
            {
                "turn": self.action_count,
                "image_path": str(image_path),
                "image_sha256": image_sha256,
                "observation": obs.to_agent_payload(),
                "action": None,
                "done": self.done,
                "feedback": feedback,
            }
        )
        return obs

    @staticmethod
    def _action_to_dict(action: Action) -> dict[str, Any]:
        return {
            "type": action.type.value,
            "direction": action.direction,
            "steps": action.steps,
            "value": action.value,
        }

    def save_trace(
        self,
        path: str | Path,
        agent_id: str = "unknown",
        run_id: str | None = None,
        efficiency_score: float | None = None,
    ) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "run_id": run_id or path.parent.name,
            "task_id": self.task.task_id,
            "agent_id": agent_id,
            "events": self.trace,
            "result": {
                "submitted_answer": self.submitted_answer,
                "correct": self.correct,
                "action_count": self.action_count,
            },
        }
        if efficiency_score is not None:
            payload["result"]["efficiency_score"] = efficiency_score
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path
