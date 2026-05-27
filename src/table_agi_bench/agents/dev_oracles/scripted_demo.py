from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from table_agi_bench.core.types import TaskSpec
from table_agi_bench.env.table_env import TableAGIEnv


@dataclass(frozen=True)
class DemoPolicyResult:
    """Private result from the development-only scripted demo policy."""

    actions: list[dict[str, Any]] = field(default_factory=list)
    note: str = "development-only oracle policy"


class ScriptedDemoOraclePolicy:
    """Development-only policy that proves environment plumbing.

    This policy may use `task.answer`. Keep oracle access isolated here so the
    public runner and public artifacts remain answer-free.
    """

    agent_id = "scripted_demo_oracle"

    def run_private(self, task: TaskSpec, env: TableAGIEnv) -> DemoPolicyResult:
        actions: list[dict[str, Any]] = []

        for _ in range(7):
            action = {"type": "move_viewport", "direction": "down", "steps": 1}
            env.step(action)
            actions.append(action)

        answer_action = {"type": "answer", "value": task.answer}
        env.step(answer_action)
        actions.append(answer_action)

        return DemoPolicyResult(actions=actions)

