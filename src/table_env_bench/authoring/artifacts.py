"""Artifact and mutation helpers for the authoring pipeline."""

from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any

from table_env_bench.authoring.models import FileMutation, StageResult


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Unsupported JSON value: {type(value)!r}")


class ArtifactStore:
    def __init__(self, *, repo_root: Path, artifact_root: Path) -> None:
        self.repo_root = repo_root
        self.artifact_root = artifact_root
        self.artifact_root.mkdir(parents=True, exist_ok=True)

    def stage_dir(self, stage: str, attempt: int = 1) -> Path:
        path = self.artifact_root / stage / f"attempt_{attempt}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_json(self, path: Path, payload: dict[str, Any]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
        return path

    def write_text(self, path: Path, content: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def persist_stage_payload(self, *, stage: str, attempt: int, name: str, payload: dict[str, Any]) -> str:
        path = self.write_json(self.stage_dir(stage, attempt) / name, payload)
        return self._rel(path)

    def persist_stage_result(self, result: StageResult) -> str:
        path = self.write_json(self.stage_dir(result.stage, result.attempt) / "stage_result.json", result.to_dict())
        return self._rel(path)

    def materialize_mutations(
        self,
        *,
        stage: str,
        attempt: int,
        allowed_prefixes: tuple[str, ...],
        mutations: list[FileMutation],
        apply_changes: bool,
    ) -> tuple[list[str], list[str]]:
        stage_dir = self.stage_dir(stage, attempt)
        changed_files: list[str] = []
        patch_chunks: list[str] = []

        for mutation in mutations:
            relative_path = mutation.path.replace("\\", "/")
            if not any(relative_path == prefix or relative_path.startswith(f"{prefix}/") for prefix in allowed_prefixes):
                raise ValueError(f"Stage {stage} cannot modify {relative_path}")

            file_path = self.repo_root / relative_path
            old_content = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
            if old_content == mutation.content:
                continue
            diff_lines = difflib.unified_diff(
                old_content.splitlines(keepends=True),
                mutation.content.splitlines(keepends=True),
                fromfile=relative_path,
                tofile=relative_path,
            )
            patch_chunks.append("".join(diff_lines))
            changed_files.append(relative_path)
            if apply_changes:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(mutation.content, encoding="utf-8")

        patch_path = stage_dir / "changes.patch"
        patch_content = "\n".join(chunk for chunk in patch_chunks if chunk)
        self.write_text(patch_path, patch_content)
        return ([self._rel(patch_path)] if patch_path.exists() else []), changed_files

    def persist_manifest(self, payload: dict[str, Any]) -> str:
        path = self.write_json(self.artifact_root / "manifest.json", payload)
        return self._rel(path)

    def _rel(self, path: Path) -> str:
        return str(path.relative_to(self.repo_root))
