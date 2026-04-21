"""In-memory store for authoring pipeline runs."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from table_env_bench.authoring import LeadAgent, PipelineRunRecord, PipelineTarget
from table_env_bench.authoring.models import BackendName


@dataclass
class AuthoringRunState:
    record: PipelineRunRecord


class AuthoringRunStore:
    def __init__(self, *, lead_agent: LeadAgent | None = None) -> None:
        self._lead_agent = lead_agent or LeadAgent()
        self._runs: dict[str, AuthoringRunState] = {}
        self._lock = Lock()

    def create(
        self,
        *,
        target: PipelineTarget,
        backend: BackendName,
        apply_changes: bool,
    ) -> AuthoringRunState:
        record = self._lead_agent.run(target=target, backend=backend, apply_changes=apply_changes)
        state = AuthoringRunState(record=record)
        with self._lock:
            self._runs[record.run_id] = state
        return state

    def get(self, run_id: str) -> AuthoringRunState:
        with self._lock:
            if run_id not in self._runs:
                raise KeyError(run_id)
            return self._runs[run_id]

    def list(self) -> list[AuthoringRunState]:
        with self._lock:
            return list(reversed(list(self._runs.values())))
