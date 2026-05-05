"""JSON loading helpers for benchmark specs."""

from __future__ import annotations

import json
from pathlib import Path

from table_env_bench.data.models import EpisodeSpec


def load_episode_spec(path: str | Path) -> EpisodeSpec:
    file_path = Path(path)
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    return EpisodeSpec.from_dict(payload)


def save_episode_spec(spec: EpisodeSpec, path: str | Path) -> Path:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(spec.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return file_path


def default_specs_dir() -> Path:
    return Path(__file__).resolve().parent / "specs"
