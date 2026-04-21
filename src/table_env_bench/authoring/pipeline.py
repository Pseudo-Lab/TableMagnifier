"""Lead-agent orchestration for authoring runs."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from uuid import uuid4

from table_env_bench.authoring.artifacts import ArtifactStore
from table_env_bench.authoring.models import (
    BackendName,
    DEFAULT_STAGE_ORDER,
    DEFAULT_SEED_SAMPLES,
    MUTATING_STAGES,
    PipelineContext,
    PipelineRunRecord,
    PipelineTarget,
    StageResult,
    VALID_STAGES,
    VALIDATION_STAGES,
)
from table_env_bench.authoring.stages import default_stage_map

ARTIFACT_ROOT = Path("artifacts/agent_runs")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _overall_status(results: list[StageResult]) -> str:
    if any(result.status == "failed" for result in results):
        return "failed"
    if any(result.status == "blocked" for result in results):
        return "blocked"
    if all(result.status == "passed" for result in results):
        return "passed"
    return "pending"


class LeadAgent:
    def __init__(self, *, repo_root: Path | None = None, stage_map: dict[str, object] | None = None) -> None:
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.stage_map = stage_map or default_stage_map()
        self._apply_lock = Lock()

    def run(self, *, target: PipelineTarget, backend: BackendName = "local", apply_changes: bool = False) -> PipelineRunRecord:
        invalid_stages = [stage for stage in target.resolved_stages() if stage not in VALID_STAGES]
        if invalid_stages:
            raise ValueError(f"Unknown stages: {invalid_stages}")
        run_id = uuid4().hex
        artifact_root = self.repo_root / ARTIFACT_ROOT / run_id
        store = ArtifactStore(repo_root=self.repo_root, artifact_root=artifact_root)
        context = PipelineContext(
            run_id=run_id,
            target=target,
            repo_root=self.repo_root,
            artifact_root=artifact_root,
            backend=backend,
            apply_changes=apply_changes,
        )
        started_at = _utc_now()

        if apply_changes:
            with self._apply_lock:
                stage_results = self._run_stages(context, store)
        else:
            stage_results = self._run_stages(context, store)

        record = PipelineRunRecord(
            run_id=run_id,
            target=target,
            overall_status=_overall_status(stage_results),  # type: ignore[arg-type]
            stage_results=stage_results,
            started_at=started_at,
            finished_at=_utc_now(),
            backend=backend,
            apply_changes=apply_changes,
        )
        store.persist_manifest(record.to_dict())
        return record

    def _run_stages(self, context: PipelineContext, store: ArtifactStore) -> list[StageResult]:
        stage_results: list[StageResult] = []
        repair_attempted = False
        selected_stages = context.target.resolved_stages()

        for stage_name in selected_stages:
            result = self._run_one_stage(stage_name, context, store, attempt=1)
            stage_results.append(result)

            if (
                result.status == "failed"
                and stage_name in VALIDATION_STAGES
                and not repair_attempted
                and any(stage in selected_stages for stage in MUTATING_STAGES)
            ):
                repair_attempted = True
                repair_context = replace(context, repair_round=1, repair_reason=f"{stage_name} failed")
                for mutable_stage in DEFAULT_STAGE_ORDER:
                    if mutable_stage not in MUTATING_STAGES or mutable_stage not in selected_stages:
                        continue
                    stage_results.append(self._run_one_stage(mutable_stage, repair_context, store, attempt=2))
                stage_results.append(self._run_one_stage(stage_name, repair_context, store, attempt=2))

        return stage_results

    def _run_one_stage(self, stage_name: str, context: PipelineContext, store: ArtifactStore, *, attempt: int) -> StageResult:
        stage = self.stage_map[stage_name]
        result, mutations = stage.run(context, attempt=attempt)
        patch_artifacts, changed_files = store.materialize_mutations(
            stage=stage_name,
            attempt=attempt,
            allowed_prefixes=tuple(getattr(stage, "allowed_prefixes", ())),
            mutations=mutations,
            apply_changes=context.apply_changes,
        )
        result.artifact_paths.extend(patch_artifacts)
        result.changed_files.extend(changed_files)
        stage_result_path = store.persist_stage_result(result)
        result.artifact_paths.append(stage_result_path)
        return result


def build_target(
    *,
    family: str,
    level: int | None = None,
    template_id: str | None = None,
    suite: str | None = None,
    stages: tuple[str, ...] | None = None,
    seed_samples: tuple[int, ...] = DEFAULT_SEED_SAMPLES,
) -> PipelineTarget:
    return PipelineTarget(
        family=family,
        level=level,
        template_id=template_id,
        suite=suite,
        stages=stages,
        seed_samples=seed_samples,
    )
