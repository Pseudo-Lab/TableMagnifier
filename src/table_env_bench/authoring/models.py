"""Types for the authoring pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

StageStatus = Literal["pending", "running", "passed", "failed", "blocked"]
BackendName = Literal["local", "openai"]
DEFAULT_SEED_SAMPLES = (0, 1, 2)

DEFAULT_STAGE_ORDER = (
    "rulebook",
    "family_builder",
    "visual_qa",
    "viewport_readability",
    "red_team_solver",
    "regression_gate",
)
VALID_STAGES = set(DEFAULT_STAGE_ORDER)
MUTATING_STAGES = {"rulebook", "family_builder"}
VALIDATION_STAGES = {"visual_qa", "viewport_readability", "red_team_solver"}


@dataclass(frozen=True)
class PipelineTarget:
    family: str
    level: int | None = None
    template_id: str | None = None
    suite: str | None = None
    stages: tuple[str, ...] | None = None
    seed_samples: tuple[int, ...] = DEFAULT_SEED_SAMPLES

    def resolved_stages(self) -> tuple[str, ...]:
        if self.stages is None:
            return DEFAULT_STAGE_ORDER
        return tuple(stage for stage in DEFAULT_STAGE_ORDER if stage in self.stages)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["stages"] = list(self.stages) if self.stages is not None else None
        payload["seed_samples"] = list(self.seed_samples)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PipelineTarget":
        return cls(
            family=str(payload["family"]),
            level=int(payload["level"]) if payload.get("level") is not None else None,
            template_id=str(payload["template_id"]) if payload.get("template_id") is not None else None,
            suite=str(payload["suite"]) if payload.get("suite") is not None else None,
            stages=tuple(str(stage) for stage in payload["stages"]) if payload.get("stages") is not None else None,
            seed_samples=tuple(int(seed) for seed in payload.get("seed_samples", DEFAULT_SEED_SAMPLES)),
        )


@dataclass
class StageResult:
    stage: str
    status: StageStatus
    summary: str
    findings: list[str] = field(default_factory=list)
    artifact_paths: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    attempt: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "status": self.status,
            "summary": self.summary,
            "findings": list(self.findings),
            "artifact_paths": list(self.artifact_paths),
            "changed_files": list(self.changed_files),
            "metrics": dict(self.metrics),
            "attempt": self.attempt,
        }


@dataclass
class PipelineRunRecord:
    run_id: str
    target: PipelineTarget
    overall_status: StageStatus
    stage_results: list[StageResult]
    started_at: str
    finished_at: str
    backend: BackendName
    apply_changes: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "target": self.target.to_dict(),
            "overall_status": self.overall_status,
            "stage_results": [result.to_dict() for result in self.stage_results],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "backend": self.backend,
            "apply_changes": self.apply_changes,
        }


@dataclass(frozen=True)
class FileMutation:
    path: str
    content: str


@dataclass
class PipelineContext:
    run_id: str
    target: PipelineTarget
    repo_root: Path
    artifact_root: Path
    backend: BackendName
    apply_changes: bool
    repair_round: int = 0
    repair_reason: str | None = None

    @property
    def stage_names(self) -> tuple[str, ...]:
        return self.target.resolved_stages()


class AuthoringAgent(Protocol):
    name: str
    stage: str
    allowed_prefixes: tuple[str, ...]

    def run(self, context: PipelineContext, *, attempt: int = 1) -> tuple[StageResult, list[FileMutation]]:
        ...
