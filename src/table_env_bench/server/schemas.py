"""Pydantic schemas for the benchmark API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    family: str | None = None
    level: int | None = None
    seed: int = 0
    instance_id: str | None = None
    template_id: str | None = None
    mode: str = "agent"
    debug: bool = False


class ActionRequest(BaseModel):
    type: str
    x: float | None = None
    y: float | None = None
    sheet: str | int | None = None
    text: str | None = None


class ObservationEnvelope(BaseModel):
    session_id: str
    observation: dict[str, Any]
    info: dict[str, Any]


class StepEnvelope(ObservationEnvelope):
    reward: float
    terminated: bool
    truncated: bool
    submitted_answer: str | None = None


class CatalogLevel(BaseModel):
    level: int
    sample_episode_id: str
    sample_question: str
    max_actions: int
    page_count: int
    sheet_count: int


class CatalogFamily(BaseModel):
    family: str
    family_display_name: str
    family_status: str = "active"
    is_preferred: bool = False
    levels: list[CatalogLevel]


class InstanceSummary(BaseModel):
    instance_id: str
    instance_label: str
    family: str
    family_display_name: str
    level: int
    source_template_id: str
    source_seed: int
    source_episode_id: str
    task_summary: str
    decisive_evidence_surfaces: list[str]
    expected_failure_mode: str
    question: str
    workbook_title: str
    max_actions: int
    sheet_count: int
    page_count: int
    benchmark_track: str | None = None
    reasoning_archetype: str | None = None
    abstraction_tier: str | None = None
    support_surface_policy: str | None = None
    qa_dependency: str | None = None
    generalization_group: str | None = None
    pack_role: str | None = None


class InstancePackEnvelope(BaseModel):
    pack_id: str
    pack_label: str
    version: str
    locale: str
    instance_count: int
    benchmark_track: str | None = None
    pack_role: str | None = None
    instances: list[InstanceSummary]


class ReplayEnvelope(BaseModel):
    session_id: str
    replay: dict[str, Any]


class HealthResponse(BaseModel):
    status: str = Field(default="ok")


class AuthoringRunCreateRequest(BaseModel):
    family: str
    level: int | None = None
    template_id: str | None = None
    suite: str | None = None
    stages: list[str] | None = None
    seed_samples: list[int] = Field(default_factory=lambda: [0, 1, 2])
    backend: str = "local"
    apply_changes: bool = False


class AuthoringRunEnvelope(BaseModel):
    run_id: str
    target: dict[str, Any]
    overall_status: str
    stage_results: list[dict[str, Any]]
    started_at: str
    finished_at: str
    backend: str
    apply_changes: bool
