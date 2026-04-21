from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import table_env_bench.authoring.stages as authoring_stages
from table_env_bench.authoring import build_target
from table_env_bench.authoring.models import PipelineContext
from table_env_bench.authoring.stages import RedTeamSolverAgent, VisualQAAgent
from table_env_bench.data.models import NoteSpec, PageSpec, RectSpec, RegionSpec, SheetSpec, TextBlockElementSpec, WorkbookSpec


@dataclass
class FakeCorrectness:
    value: float


@dataclass
class FakeEvaluation:
    correctness: FakeCorrectness


@dataclass
class FakeRunResult:
    evaluation: FakeEvaluation


def _metadata_for_exception_surface(level: int) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "required_sheet_ids": ["examples", "exception", "query"],
        "required_page_refs": [
            "examples:examples-p1",
            "exception:exception-p1",
            "query:query-p1",
        ],
        "required_actions": ["must_switch_sheet", "must_visit_exception"],
        "required_evidence": [
            {"kind": "page", "sheet_id": "examples", "page_id": "examples-p1"},
            {"kind": "page", "sheet_id": "exception", "page_id": "exception-p1"},
            {"kind": "page", "sheet_id": "query", "page_id": "query-p1"},
        ],
    }
    if level >= 2:
        metadata["required_page_refs"].append("exception:exception-p2")
        metadata["required_actions"].append("must_open_note")
        metadata["required_evidence"].extend(
            [
                {"kind": "page", "sheet_id": "exception", "page_id": "exception-p2"},
                {
                    "kind": "note",
                    "sheet_id": "exception",
                    "page_id": "exception-p2",
                    "note_id": "scope-note",
                },
            ]
        )
    return metadata


def _build_exception_env(
    level: int,
    *,
    include_note_marker: bool = True,
    include_scope_note: bool = True,
    metadata_override: dict[str, Any] | None = None,
) -> SimpleNamespace:
    examples_page = PageSpec(
        page_id="examples-p1",
        title="예시 시트",
        width=1280,
        height=900,
        elements=(
            TextBlockElementSpec(
                element_id="examples-block",
                rect=RectSpec(x=96, y=176, width=480, height=140),
                title="예시",
                lines=("예시",),
            ),
        ),
        regions=(
            RegionSpec(
                public_id="examples-region",
                role="annotation",
                label="예시",
                rect=RectSpec(x=96, y=176, width=480, height=140),
            ),
        ),
    )
    exception_pages = [
        PageSpec(
            page_id="exception-p1",
            title="예외 시트",
            width=1280,
            height=900,
            elements=(
                TextBlockElementSpec(
                    element_id="exception-block",
                    rect=RectSpec(x=96, y=176, width=480, height=140),
                    title="예외",
                    lines=("예외",),
                ),
            ),
            regions=(),
        )
    ]
    if level >= 2:
        notes = (NoteSpec(id="scope-note", title="적용 범위", text="scope-note"),) if include_scope_note else ()
        regions = (
            (
                {
                    "public_id": "exception-note-region",
                    "role": "note_marker",
                    "label": "범위 메모",
                    "rect": RectSpec(x=124, y=212, width=420, height=120),
                    "linked_note_id": "scope-note",
                }
                if include_note_marker
                else {
                    "public_id": "exception-note-region",
                    "role": "annotation",
                    "label": "범위 메모",
                    "rect": RectSpec(x=124, y=212, width=420, height=120),
                }
            ),
        )
        exception_pages.append(
            PageSpec(
                page_id="exception-p2",
                title="적용 범위",
                width=1280,
                height=900,
                elements=(
                    TextBlockElementSpec(
                        element_id="exception-note",
                        rect=RectSpec(x=124, y=212, width=420, height=120),
                        title="범위 메모",
                        lines=("scope-note",),
                    ),
                ),
                regions=tuple(
                    RegionSpec(
                        public_id=item["public_id"],
                        role=item["role"],
                        label=item["label"],
                        rect=item["rect"],
                        linked_note_id=item.get("linked_note_id"),
                    )
                    for item in regions
                ),
                notes=notes,
            )
        )

    query_page = PageSpec(
        page_id="query-p1",
        title="선택 시트",
        width=1280,
        height=900,
        elements=(
            TextBlockElementSpec(
                element_id="query-block",
                rect=RectSpec(x=96, y=176, width=480, height=140),
                title="질의",
                lines=("질의",),
            ),
        ),
        regions=(),
    )
    workbook = WorkbookSpec(
        workbook_id="exception-workbook",
        title="예외 워크북",
        sheets=tuple(
            SheetSpec(
                sheet_id=sheet_id,
                tab_label=sheet_id,
                pages=(examples_page,) if sheet_id == "examples" else tuple(exception_pages) if sheet_id == "exception" else (query_page,),
            )
            for sheet_id in ["examples", "exception", "query"]
        ),
    )
    metadata = _metadata_for_exception_surface(level)
    if metadata_override:
        metadata.update(metadata_override)

    first_page = examples_page.to_dict()
    observation = {
        "viewport_image_png_base64": "ZmFrZQ==",
        "viewport_scene": {"page": first_page},
        "current_sheet_name": "examples",
        "current_sheet_index": 0,
        "current_page_index": 0,
        "page_count_in_sheet": len(workbook.sheets[0].pages),
    }
    info = {"family": "inventory_exception_disambiguation", "sheet_tabs": [sheet.sheet_id for sheet in workbook.sheets]}
    spec = SimpleNamespace(workbook=workbook, metadata=metadata)
    return SimpleNamespace(spec=spec, reset=lambda: (observation, info))


def test_visual_qa_accepts_exception_surface_topology(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    context = PipelineContext(
        run_id="run-visual",
        target=build_target(family="inventory_exception_disambiguation", level=2, seed_samples=(0,)),
        repo_root=tmp_path,
        artifact_root=tmp_path / "artifacts/agent_runs/run-visual",
        backend="local",
        apply_changes=False,
    )

    monkeypatch.setattr(authoring_stages, "WorkbookEnv", lambda **kwargs: _build_exception_env(kwargs["level"]))

    result, mutations = VisualQAAgent().run(context, attempt=1)

    assert mutations == []
    assert result.status == "passed"
    assert not result.findings


def test_visual_qa_rejects_exception_note_structure_mismatch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    context = PipelineContext(
        run_id="run-visual-fail",
        target=build_target(family="inventory_exception_disambiguation", level=2, seed_samples=(0,)),
        repo_root=tmp_path,
        artifact_root=tmp_path / "artifacts/agent_runs/run-visual-fail",
        backend="local",
        apply_changes=False,
    )

    monkeypatch.setattr(
        authoring_stages,
        "WorkbookEnv",
        lambda **kwargs: _build_exception_env(
            kwargs["level"],
            include_note_marker=False,
            include_scope_note=False,
            metadata_override={
                "required_actions": ["must_switch_sheet", "must_visit_exception"],
                "required_evidence": [
                    {"kind": "page", "sheet_id": "examples", "page_id": "examples-p1"},
                    {"kind": "page", "sheet_id": "exception", "page_id": "exception-p1"},
                    {"kind": "page", "sheet_id": "query", "page_id": "query-p1"},
                ],
            },
        ),
    )

    result, _ = VisualQAAgent().run(context, attempt=1)

    assert result.status == "failed"
    assert any("exception-p2" in finding for finding in result.findings)
    assert any("note_marker" in finding for finding in result.findings)
    assert any("Required actions" in finding for finding in result.findings)
    assert any("Required evidence" in finding for finding in result.findings)


def test_red_team_solver_uses_exception_probes_and_thresholds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    context = PipelineContext(
        run_id="run-red-team",
        target=build_target(family="inventory_exception_disambiguation", level=2, seed_samples=(0,)),
        repo_root=tmp_path,
        artifact_root=tmp_path / "artifacts/agent_runs/run-red-team",
        backend="local",
        apply_changes=False,
    )

    observed_agents: list[str] = []

    def fake_workbook_env(**kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(spec=SimpleNamespace(family=kwargs["family"], level=kwargs["level"]))

    def fake_run_episode(env: Any, agent: Any) -> FakeRunResult:
        observed_agents.append(agent.name)
        score_map = {
            "no_exception": 0.25,
            "no_exception_note": 0.25,
            "text_scrape": 0.75,
        }
        return FakeRunResult(FakeEvaluation(FakeCorrectness(score_map.get(agent.name, 0.0))))

    monkeypatch.setattr(authoring_stages, "WorkbookEnv", fake_workbook_env)
    monkeypatch.setattr(authoring_stages, "run_episode", fake_run_episode)

    result, mutations = RedTeamSolverAgent().run(context, attempt=1)

    assert mutations == []
    assert result.status == "failed"
    assert "query_only" not in observed_agents
    assert "no_exception" in observed_agents
    assert "no_exception_note" in observed_agents
    assert result.metrics["level_average_correctness"]["l2"]["no_exception"] == pytest.approx(0.25)
    assert result.metrics["level_average_correctness"]["l2"]["no_exception_note"] == pytest.approx(0.25)
    assert result.metrics["level_average_correctness"]["l2"]["text_scrape"] == pytest.approx(0.75)
    assert any("No-exception probe" in finding for finding in result.findings)
    assert any("No-exception-note probe" in finding for finding in result.findings)
    assert any("Text scrape baseline" in finding for finding in result.findings)
