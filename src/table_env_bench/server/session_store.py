"""In-memory environment session store."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from uuid import uuid4

from table_env_bench.data.instances import load_instance
from table_env_bench.env.environment import TableEnv


@dataclass
class SessionRecord:
    session_id: str
    env: TableEnv
    observation: dict
    info: dict


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionRecord] = {}
        self._lock = Lock()

    def create(
        self,
        *,
        family: str | None,
        level: int | None,
        seed: int,
        instance_id: str | None,
        template_id: str | None,
        mode: str,
        debug: bool,
    ) -> SessionRecord:
        if instance_id is not None:
            env = TableEnv(episode_spec=load_instance(instance_id), mode=mode, debug=debug)
        else:
            if family is None or level is None:
                raise ValueError("family and level are required when instance_id is not provided")
            env = TableEnv(family=family, level=level, seed=seed, template_id=template_id, mode=mode, debug=debug)
        observation, info = env.reset()
        record = SessionRecord(session_id=uuid4().hex, env=env, observation=observation, info=info)
        with self._lock:
            self._sessions[record.session_id] = record
        return record

    def get(self, session_id: str) -> SessionRecord:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(session_id)
            return self._sessions[session_id]

    def step(self, session_id: str, action: dict) -> tuple[SessionRecord, float, bool, bool]:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(session_id)
            record = self._sessions[session_id]
            observation, reward, terminated, truncated, info = record.env.step(action)
            record.observation = observation
            record.info = info
            return record, reward, terminated, truncated
