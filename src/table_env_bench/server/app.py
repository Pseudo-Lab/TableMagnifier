"""FastAPI app for local human-play and benchmark inspection."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from table_env_bench.authoring import PipelineTarget
from table_env_bench.data.canonical_catalog import benchmark_suite_manifest
from table_env_bench.data.generators import FAMILY_LABELS, generate_episode, list_families, list_instance_packs, list_levels
from table_env_bench.server.schemas import (
    ActionRequest,
    AuthoringRunCreateRequest,
    AuthoringRunEnvelope,
    CatalogFamily,
    CatalogLevel,
    GeneratedBenchmarkRecord,
    GeneratedBenchmarkSuite,
    GeneratedBenchmarkSuiteEnvelope,
    GeneratedBenchmarkTemplate,
    HealthResponse,
    InstancePackEnvelope,
    InstanceSummary,
    ObservationEnvelope,
    ReplayEnvelope,
    SessionCreateRequest,
    StepEnvelope,
)
from table_env_bench.server.authoring_store import AuthoringRunStore
from table_env_bench.server.session_store import SessionStore

app = FastAPI(title="table-env-bench API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = SessionStore()
authoring_store = AuthoringRunStore()

PREFERRED_GENERATOR_FAMILY = "marker_position_rule_transfer"
GENERATED_BENCHMARK_SUITE_ORDER = ("canonical_dev",)
GENERATED_BENCHMARK_SUITE_LABELS = {
    "canonical_dev": "Canonical 개발 세트",
}
GENERATED_BENCHMARK_SUITE_DESCRIPTIONS = {
    "canonical_dev": "공개 frozen pack 없이 canonical generator에서 즉시 생성하는 개발용 benchmark record입니다.",
}


def _catalog_family_order(family: str) -> tuple[int, str]:
    return (0 if family == PREFERRED_GENERATOR_FAMILY else 1, family)


def _catalog() -> list[CatalogFamily]:
    families: list[CatalogFamily] = []
    for family in sorted(list_families(), key=_catalog_family_order):
        levels: list[CatalogLevel] = []
        for level in list_levels(family):
            episode = generate_episode(family, level, seed=0)
            total_pages = sum(len(sheet.pages) for sheet in episode.sheets)
            levels.append(
                CatalogLevel(
                    level=level,
                    sample_episode_id=episode.episode_id,
                    sample_question=episode.question,
                    max_actions=episode.max_actions,
                    page_count=total_pages,
                    sheet_count=len(episode.sheets),
                )
            )
        families.append(
            CatalogFamily(
                family=family,
                family_display_name=FAMILY_LABELS.get(family, family),
                family_status=(
                    "preferred"
                    if family == PREFERRED_GENERATOR_FAMILY
                    else "active"
                ),
                is_preferred=family == PREFERRED_GENERATOR_FAMILY,
                levels=levels,
            )
        )
    return families


def _generated_template_order(ref: dict[str, object]) -> tuple[int, int, str, str, int]:
    family = str(ref["family"])
    return (
        0 if family == PREFERRED_GENERATOR_FAMILY else 1,
        family,
        str(ref["template_id"]),
        int(ref["level"]),
    )


def _generated_benchmark_suites() -> GeneratedBenchmarkSuiteEnvelope:
    suite_manifest = benchmark_suite_manifest()
    suites: list[GeneratedBenchmarkSuite] = []
    for suite_id in GENERATED_BENCHMARK_SUITE_ORDER:
        refs = sorted(suite_manifest[suite_id], key=_generated_template_order)
        templates: list[GeneratedBenchmarkTemplate] = []
        for ref in refs:
            family = str(ref["family"])
            level = int(ref["level"])
            template_id = str(ref["template_id"])
            seed_slots = [int(seed) for seed in ref["seed_slots"]]  # type: ignore[index]
            records = [
                GeneratedBenchmarkRecord(
                    family=family,
                    level=level,
                    template_id=template_id,
                    seed=seed,
                    episode_id=f"{family}_{template_id}_l{level}_s{seed}",
                    record_label=f"seed {seed}",
                    required_navigation=dict(ref.get("required_navigation") or {}),
                )
                for seed in sorted(seed_slots)
            ]
            templates.append(
                GeneratedBenchmarkTemplate(
                    family=family,
                    family_display_name=FAMILY_LABELS.get(family, family),
                    level=level,
                    template_id=template_id,
                    template_label=str(ref["template_label"]),
                    seed_slots=sorted(seed_slots),
                    benchmark_track=str(ref["benchmark_track"]) if ref.get("benchmark_track") is not None else None,
                    difficulty_tier=str(ref["difficulty_tier"]) if ref.get("difficulty_tier") is not None else None,
                    is_active=True,
                    answer_form=str(ref["answer_form"]) if ref.get("answer_form") is not None else None,
                    primary_operator=str(ref["primary_operator"]) if ref.get("primary_operator") is not None else None,
                    support_operator=str(ref["support_operator"]) if ref.get("support_operator") is not None else None,
                    records=records,
                )
            )
        suites.append(
            GeneratedBenchmarkSuite(
                suite_id=suite_id,
                suite_label=GENERATED_BENCHMARK_SUITE_LABELS[suite_id],
                suite_description=GENERATED_BENCHMARK_SUITE_DESCRIPTIONS[suite_id],
                record_count=sum(len(template.records) for template in templates),
                templates=templates,
            )
        )
    return GeneratedBenchmarkSuiteEnvelope(suites=suites)


def _instance_catalog() -> list[InstancePackEnvelope]:
    packs: list[InstancePackEnvelope] = []
    for pack in list_instance_packs():
        packs.append(
            InstancePackEnvelope(
                pack_id=pack.pack_id,
                pack_label=pack.pack_label,
                version=pack.version,
                locale=pack.locale,
                instance_count=pack.instance_count,
                benchmark_track=pack.benchmark_track,
                pack_role=pack.pack_role,
                instances=[
                    InstanceSummary(
                        instance_id=instance.instance_id,
                        instance_label=instance.instance_label,
                        family=instance.family,
                        family_display_name=instance.family_display_name,
                        level=instance.level,
                        source_template_id=instance.source_template_id,
                        source_seed=instance.source_seed,
                        source_episode_id=instance.source_episode_id,
                        task_summary=instance.task_summary,
                        decisive_evidence_surfaces=list(instance.decisive_evidence_surfaces),
                        expected_failure_mode=instance.expected_failure_mode,
                        question=instance.question,
                        workbook_title=instance.workbook_title,
                        max_actions=instance.max_actions,
                        sheet_count=instance.sheet_count,
                        page_count=instance.page_count,
                        benchmark_track=instance.benchmark_track,
                        reasoning_archetype=instance.reasoning_archetype,
                        abstraction_tier=instance.abstraction_tier,
                        support_surface_policy=instance.support_surface_policy,
                        qa_dependency=instance.qa_dependency,
                        generalization_group=instance.generalization_group,
                        pack_role=instance.pack_role,
                    )
                    for instance in pack.instances
                ],
            )
        )
    return packs


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.get("/api/catalog", response_model=list[CatalogFamily])
def catalog() -> list[CatalogFamily]:
    return _catalog()


@app.get("/api/benchmark-suites", response_model=GeneratedBenchmarkSuiteEnvelope)
def benchmark_suites() -> GeneratedBenchmarkSuiteEnvelope:
    return _generated_benchmark_suites()


@app.get("/api/instances", response_model=list[InstancePackEnvelope])
def instances() -> list[InstancePackEnvelope]:
    return _instance_catalog()


@app.post("/api/sessions", response_model=ObservationEnvelope)
def create_session(payload: SessionCreateRequest) -> ObservationEnvelope:
    try:
        record = store.create(
            family=payload.family,
            level=payload.level,
            seed=payload.seed,
            instance_id=payload.instance_id,
            template_id=payload.template_id,
            mode=payload.mode,
            debug=payload.debug,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown family or level: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ObservationEnvelope(session_id=record.session_id, observation=record.observation, info=record.info)


@app.get("/api/sessions/{session_id}", response_model=ObservationEnvelope)
def get_session(session_id: str) -> ObservationEnvelope:
    try:
        record = store.get(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown session: {session_id}") from exc
    return ObservationEnvelope(session_id=record.session_id, observation=record.observation, info=record.info)


@app.post("/api/sessions/{session_id}/actions", response_model=StepEnvelope)
def apply_action(session_id: str, payload: ActionRequest) -> StepEnvelope:
    try:
        record, reward, terminated, truncated = store.step(session_id, payload.model_dump(exclude_none=True))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown session: {session_id}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return StepEnvelope(
        session_id=record.session_id,
        observation=record.observation,
        info=record.info,
        reward=reward,
        terminated=terminated,
        truncated=truncated,
        submitted_answer=record.env.submitted_answer,
    )


@app.get("/api/sessions/{session_id}/replay", response_model=ReplayEnvelope)
def get_replay(session_id: str) -> ReplayEnvelope:
    try:
        record = store.get(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown session: {session_id}") from exc
    return ReplayEnvelope(session_id=record.session_id, replay=record.env.replay.to_dict(record.env.spec.metadata))


@app.post("/api/agent-runs", response_model=AuthoringRunEnvelope)
def create_authoring_run(payload: AuthoringRunCreateRequest) -> AuthoringRunEnvelope:
    try:
        state = authoring_store.create(
            target=PipelineTarget(
                family=payload.family,
                level=payload.level,
                template_id=payload.template_id,
                suite=payload.suite,
                stages=tuple(payload.stages) if payload.stages is not None else None,
                seed_samples=tuple(payload.seed_samples),
            ),
            backend=payload.backend,  # type: ignore[arg-type]
            apply_changes=payload.apply_changes,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AuthoringRunEnvelope(**state.record.to_dict())


@app.get("/api/agent-runs", response_model=list[AuthoringRunEnvelope])
def list_authoring_runs() -> list[AuthoringRunEnvelope]:
    return [AuthoringRunEnvelope(**state.record.to_dict()) for state in authoring_store.list()]


@app.get("/api/agent-runs/{run_id}", response_model=AuthoringRunEnvelope)
def get_authoring_run(run_id: str) -> AuthoringRunEnvelope:
    try:
        state = authoring_store.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown authoring run: {run_id}") from exc
    return AuthoringRunEnvelope(**state.record.to_dict())
