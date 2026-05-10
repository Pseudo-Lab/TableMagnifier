from __future__ import annotations

from dataclasses import replace
from dataclasses import dataclass, field
from pathlib import Path
from subprocess import CompletedProcess
from types import SimpleNamespace

import pytest

from table_env_bench.authoring import LeadAgent, build_target
from table_env_bench.authoring.models import DEFAULT_SEED_SAMPLES, FileMutation, PipelineContext, StageResult
from table_env_bench.authoring.stages import RedTeamSolverAgent, ViewportReadabilityAgent, VisualQAAgent
import table_env_bench.authoring.stages as authoring_stages


@dataclass
class FakeStage:
    stage: str
    allowed_prefixes: tuple[str, ...]
    mutations: list[FileMutation] = field(default_factory=list)
    fail_attempts: set[int] = field(default_factory=set)
    calls: list[int] = field(default_factory=list)
    name: str = "fake"

    def run(self, context: PipelineContext, *, attempt: int = 1) -> tuple[StageResult, list[FileMutation]]:
        self.calls.append(attempt)
        status = "failed" if attempt in self.fail_attempts else "passed"
        return (
            StageResult(
                stage=self.stage,
                status=status,
                summary=f"{self.stage} attempt {attempt}",
                findings=[f"{self.stage} failed"] if status == "failed" else [],
                attempt=attempt,
            ),
            list(self.mutations),
        )


def _stage_map(*, fail_visual: bool = False, bad_mutation: bool = False) -> dict[str, FakeStage]:
    return {
        "rulebook": FakeStage(
            stage="rulebook",
            allowed_prefixes=("docs",),
            mutations=[FileMutation("docs/authoring/rule_contracts/demo.json", '{"ok": true}\n')],
        ),
        "family_builder": FakeStage(
            stage="family_builder",
            allowed_prefixes=("src/table_env_bench/data/families/contracts",),
            mutations=[
                FileMutation(
                    "oops/outside.json" if bad_mutation else "src/table_env_bench/data/families/contracts/demo.json",
                    '{"built": true}\n',
                )
            ],
        ),
        "visual_qa": FakeStage(
            stage="visual_qa",
            allowed_prefixes=(),
            fail_attempts={1} if fail_visual else set(),
        ),
        "viewport_readability": FakeStage(stage="viewport_readability", allowed_prefixes=()),
        "red_team_solver": FakeStage(stage="red_team_solver", allowed_prefixes=()),
        "regression_gate": FakeStage(stage="regression_gate", allowed_prefixes=()),
    }


def test_lead_agent_runs_default_stage_order_and_persists_manifest(tmp_path: Path) -> None:
    stage_map = _stage_map()
    lead = LeadAgent(repo_root=tmp_path, stage_map=stage_map)

    record = lead.run(target=build_target(family="demo_family"), apply_changes=False)

    assert [result.stage for result in record.stage_results[:6]] == [
        "rulebook",
        "family_builder",
        "visual_qa",
        "viewport_readability",
        "red_team_solver",
        "regression_gate",
    ]
    assert record.overall_status == "passed"
    assert (tmp_path / "artifacts/agent_runs" / record.run_id / "manifest.json").exists()
    assert not (tmp_path / "docs/authoring/rule_contracts/demo.json").exists()
    assert not (tmp_path / "src/table_env_bench/data/families/contracts/demo.json").exists()


def test_lead_agent_apply_writes_repo_files(tmp_path: Path) -> None:
    stage_map = _stage_map()
    lead = LeadAgent(repo_root=tmp_path, stage_map=stage_map)

    record = lead.run(target=build_target(family="demo_family"), apply_changes=True)

    assert record.overall_status == "passed"
    assert (tmp_path / "docs/authoring/rule_contracts/demo.json").read_text(encoding="utf-8") == '{"ok": true}\n'
    assert (tmp_path / "src/table_env_bench/data/families/contracts/demo.json").read_text(encoding="utf-8") == '{"built": true}\n'


def test_lead_agent_rejects_out_of_scope_mutation(tmp_path: Path) -> None:
    lead = LeadAgent(repo_root=tmp_path, stage_map=_stage_map(bad_mutation=True))

    with pytest.raises(ValueError, match="cannot modify"):
        lead.run(target=build_target(family="demo_family"), apply_changes=False)


def test_lead_agent_repair_loop_runs_once(tmp_path: Path) -> None:
    stage_map = _stage_map(fail_visual=True)
    lead = LeadAgent(repo_root=tmp_path, stage_map=stage_map)

    record = lead.run(target=build_target(family="demo_family"), apply_changes=False)

    visual_attempts = [result.attempt for result in record.stage_results if result.stage == "visual_qa"]
    assert visual_attempts == [1, 2]
    assert stage_map["rulebook"].calls == [1, 2]
    assert stage_map["family_builder"].calls == [1, 2]
    assert record.overall_status == "failed"


def test_viewport_readability_agent_runs_playwright_review(monkeypatch, tmp_path: Path) -> None:
    frontend_root = tmp_path / "frontend"
    frontend_root.mkdir()
    context = PipelineContext(
        run_id="demo-run",
        target=build_target(family="k_vis_table_arc", level=3, seed_samples=(0,)),
        repo_root=tmp_path,
        artifact_root=tmp_path / "artifacts/agent_runs/demo-run",
        backend="local",
        apply_changes=False,
    )

    def fake_export_preview_gallery(out_dir, *, seed, families, levels, template_id):
        review_dir = Path(out_dir)
        review_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = review_dir / "manifest.json"
        manifest_path.write_text(
            '{"seed": 0, "previews": [{"family": "k_vis_table_arc", "level": "3", "surface_id": "surface-1", "kind": "note_overlay", "page_id": "exception-p2"}]}',
            encoding="utf-8",
        )
        return {"count": 1}

    def fake_subprocess_run(*args, **kwargs):
        command = args[0]
        env = kwargs.get("env", {})
        if "workbench-navigation-readability.spec.ts" in " ".join(command):
            summary_path = Path(env["PLAYWRIGHT_WORKBENCH_SUMMARY_PATH"])
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary_path.write_text(
                '{"visited_pages": ["exception:1/2", "exception:2/2"], "opened_notes": ["anchor-scope-note"]}',
                encoding="utf-8",
            )
        return CompletedProcess(args=command, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(authoring_stages.shutil, "which", lambda _: "/usr/bin/npm")
    monkeypatch.setattr(authoring_stages, "export_preview_gallery", fake_export_preview_gallery)
    monkeypatch.setattr(authoring_stages.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(authoring_stages, "canonical_seed_capacity", lambda family, level: 1)

    context = PipelineContext(
        run_id="demo-run",
        target=build_target(family="k_vis_table_arc", level=3, seed_samples=(0,)),
        repo_root=tmp_path,
        artifact_root=tmp_path / "artifacts/agent_runs/demo-run",
        backend="local",
        apply_changes=False,
    )

    result, mutations = ViewportReadabilityAgent().run(context, attempt=1)

    assert mutations == []
    assert result.status == "passed"
    assert any(path.endswith("manifest.json") for path in result.artifact_paths)
    assert any(path.endswith(".stdout.log") for path in result.artifact_paths)
    assert any(path.endswith(".stderr.log") for path in result.artifact_paths)
    assert any(path.endswith(".summary.json") for path in result.artifact_paths)
    assert result.metrics["review_runs"][-1]["summary"]["opened_notes"] == ["anchor-scope-note"]
    assert result.metrics["full_seed_mode"] is False


def test_viewport_readability_agent_expands_default_seed_samples_to_full_capacity(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "frontend").mkdir()

    def fake_export_preview_gallery(out_dir, *, seed, families, levels, template_id):
        review_dir = Path(out_dir)
        review_dir.mkdir(parents=True, exist_ok=True)
        (review_dir / "manifest.json").write_text(
            '{"seed": 0, "previews": [{"family": "k_vis_table_arc", "level": "1", "surface_id": "surface-1", "kind": "overview", "page_id": "examples-p1"}]}',
            encoding="utf-8",
        )
        return {"count": 1}

    def fake_subprocess_run(*args, **kwargs):
        command = args[0]
        env = kwargs.get("env", {})
        if "workbench-navigation-readability.spec.ts" in " ".join(command):
            summary_path = Path(env["PLAYWRIGHT_WORKBENCH_SUMMARY_PATH"])
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary_path.write_text('{"visited_pages": ["examples:1/1"]}', encoding="utf-8")
        return CompletedProcess(args=command, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(authoring_stages.shutil, "which", lambda _: "/usr/bin/npm")
    monkeypatch.setattr(authoring_stages, "export_preview_gallery", fake_export_preview_gallery)
    monkeypatch.setattr(authoring_stages.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(authoring_stages, "canonical_seed_capacity", lambda family, level: 4)

    context = PipelineContext(
        run_id="demo-run",
        target=build_target(family="k_vis_table_arc", level=1, seed_samples=DEFAULT_SEED_SAMPLES),
        repo_root=tmp_path,
        artifact_root=tmp_path / "artifacts/agent_runs/demo-run",
        backend="local",
        apply_changes=False,
    )

    result, _ = ViewportReadabilityAgent().run(context, attempt=1)

    assert result.status == "passed"
    assert result.metrics["full_seed_mode"] is True
    assert result.metrics["seed_map"] == {"l1": [0, 1, 2, 3]}
    assert result.metrics["review_target_count"] == 4


def test_visual_qa_agent_checks_required_evidence_metadata(monkeypatch) -> None:
    result, _ = VisualQAAgent().run(
        PipelineContext(
            run_id="marker-run",
            target=build_target(family="k_vis_table_arc", level=3, seed_samples=(0,)),
            repo_root=Path.cwd(),
            artifact_root=Path("artifacts/agent_runs/marker-run"),
            backend="local",
            apply_changes=False,
        ),
        attempt=1,
    )
    assert result.status == "passed"

    real_env = authoring_stages.WorkbookEnv

    class MissingEvidenceEnv:
        def __init__(self, *args, **kwargs):
            self._env = real_env(*args, **kwargs)

        def reset(self):
            observation, info = self._env.reset()
            metadata = dict(self._env.spec.metadata)
            metadata["required_evidence"] = []
            self.spec = replace(self._env.spec, metadata=metadata)
            return observation, info

    monkeypatch.setattr(authoring_stages, "WorkbookEnv", MissingEvidenceEnv)
    broken_result, _ = VisualQAAgent().run(
        PipelineContext(
            run_id="marker-run",
            target=build_target(family="k_vis_table_arc", level=3, seed_samples=(0,)),
            repo_root=Path.cwd(),
            artifact_root=Path("artifacts/agent_runs/marker-run"),
            backend="local",
            apply_changes=False,
        ),
        attempt=1,
    )
    assert broken_result.status == "failed"
    assert any("Missing required_evidence" in finding for finding in broken_result.findings)


def test_viewport_readability_agent_checks_marker_position_note(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "frontend").mkdir()

    def fake_export_preview_gallery(out_dir, *, seed, families, levels, template_id):
        review_dir = Path(out_dir)
        review_dir.mkdir(parents=True, exist_ok=True)
        (review_dir / "manifest.json").write_text(
            '{"seed": 0, "previews": [{"family": "k_vis_table_arc", "level": "3", "surface_id": "surface-1", "kind": "note_overlay", "page_id": "exception-p2"}]}',
            encoding="utf-8",
        )
        return {"count": 1}

    def fake_subprocess_run(*args, **kwargs):
        command = args[0]
        env = kwargs.get("env", {})
        if "workbench-navigation-readability.spec.ts" in " ".join(command):
            summary_path = Path(env["PLAYWRIGHT_WORKBENCH_SUMMARY_PATH"])
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary_path.write_text('{"visited_pages": ["exception:2/2"], "opened_notes": ["anchor-scope-note"]}', encoding="utf-8")
        return CompletedProcess(args=command, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(authoring_stages.shutil, "which", lambda _: "/usr/bin/npm")
    monkeypatch.setattr(authoring_stages, "export_preview_gallery", fake_export_preview_gallery)
    monkeypatch.setattr(authoring_stages.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(authoring_stages, "canonical_seed_capacity", lambda family, level: 1)

    result, _ = ViewportReadabilityAgent().run(
        PipelineContext(
            run_id="marker-run",
            target=build_target(family="k_vis_table_arc", level=3, seed_samples=(0,)),
            repo_root=tmp_path,
            artifact_root=tmp_path / "artifacts/agent_runs/marker-run",
            backend="local",
            apply_changes=False,
        ),
        attempt=1,
    )
    assert result.status == "passed"
    assert result.metrics["review_runs"][-1]["summary"]["opened_notes"] == ["anchor-scope-note"]


def test_red_team_solver_agent_enforces_marker_position_thresholds(monkeypatch) -> None:
    class StaticEnv:
        def __init__(self, *, family, level, seed, template_id):
            self.family = family
            self.level = level
            self.seed = seed
            self.template_id = template_id

    def fake_run_episode(env, agent):
        value = 1.0 if agent.name == "query_only" else 0.0
        return SimpleNamespace(evaluation=SimpleNamespace(correctness=SimpleNamespace(value=value)))

    monkeypatch.setattr(authoring_stages, "WorkbookEnv", StaticEnv)
    monkeypatch.setattr(authoring_stages, "run_episode", fake_run_episode)

    result, _ = RedTeamSolverAgent().run(
        PipelineContext(
            run_id="marker-run",
            target=build_target(family="k_vis_table_arc", level=2, seed_samples=(0,)),
            repo_root=Path.cwd(),
            artifact_root=Path("artifacts/agent_runs/marker-run"),
            backend="local",
            apply_changes=False,
        ),
        attempt=1,
    )
    assert result.status == "failed"
    assert any("Query-only" in finding for finding in result.findings)


def test_viewport_readability_agent_fails_missing_required_viewport_state(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "frontend").mkdir()

    def fake_export_preview_gallery(out_dir, *, seed, families, levels, template_id):
        review_dir = Path(out_dir)
        review_dir.mkdir(parents=True, exist_ok=True)
        (review_dir / "manifest.json").write_text(
            '{"seed": 0, "previews": [{"family": "k_vis_table_arc", "level": "1", "surface_id": "surface-1", "kind": "query", "page_id": "query-p1"}]}',
            encoding="utf-8",
        )
        return {"count": 1}

    def fake_subprocess_run(*args, **kwargs):
        command = args[0]
        env = kwargs.get("env", {})
        if "workbench-navigation-readability.spec.ts" in " ".join(command):
            summary_path = Path(env["PLAYWRIGHT_WORKBENCH_SUMMARY_PATH"])
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary_path.write_text('{"visited_viewport_states": []}', encoding="utf-8")
        return CompletedProcess(args=command, returncode=0, stdout="ok", stderr="")

    fake_spec = SimpleNamespace(
        metadata={
            "required_navigation": {
                "required_viewport_states": [{"state_id": "query-zoom-pan-evidence"}],
            }
        }
    )

    monkeypatch.setattr(authoring_stages.shutil, "which", lambda _: "/usr/bin/npm")
    monkeypatch.setattr(authoring_stages, "export_preview_gallery", fake_export_preview_gallery)
    monkeypatch.setattr(authoring_stages.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(authoring_stages, "canonical_seed_capacity", lambda family, level: 1)
    monkeypatch.setattr(authoring_stages, "generate_episode", lambda *args, **kwargs: fake_spec)

    result, _ = ViewportReadabilityAgent().run(
        PipelineContext(
            run_id="viewport-state-run",
            target=build_target(family="k_vis_table_arc", level=1, seed_samples=(0,)),
            repo_root=tmp_path,
            artifact_root=tmp_path / "artifacts/agent_runs/viewport-state-run",
            backend="local",
            apply_changes=False,
        ),
        attempt=1,
    )

    assert result.status == "failed"
    assert any("query-zoom-pan-evidence" in finding for finding in result.findings)


def test_red_team_solver_derives_generic_navigation_probes(monkeypatch, tmp_path: Path) -> None:
    observed_agents: list[str] = []
    fake_manifest = SimpleNamespace(
        required_navigation={
            "forbidden_shortcuts": ["initial_viewport_only", "no_pan_zoom", "sheet_skip"],
        }
    )

    def fake_run_episode(env, agent):
        observed_agents.append(agent.name)
        value = 0.25 if agent.name == "sheet_skip" else 0.0
        return SimpleNamespace(evaluation=SimpleNamespace(correctness=SimpleNamespace(value=value)))

    monkeypatch.setattr(authoring_stages, "list_templates", lambda family, level: ["template-a"])
    monkeypatch.setattr(authoring_stages, "template_manifest", lambda family, level, template_id: fake_manifest)
    monkeypatch.setattr(authoring_stages, "canonical_seed_capacity", lambda family, level: 1)
    monkeypatch.setattr(authoring_stages, "WorkbookEnv", lambda **kwargs: SimpleNamespace(spec=SimpleNamespace(family=kwargs["family"])))
    monkeypatch.setattr(authoring_stages, "run_episode", fake_run_episode)

    result, _ = RedTeamSolverAgent().run(
        PipelineContext(
            run_id="red-team-navigation-run",
            target=build_target(family="k_vis_table_arc", level=1, seed_samples=(0,)),
            repo_root=tmp_path,
            artifact_root=tmp_path / "artifacts/agent_runs/red-team-navigation-run",
            backend="local",
            apply_changes=False,
        ),
        attempt=1,
    )

    assert {"initial_viewport_only", "no_pan_zoom", "sheet_skip"}.issubset(set(observed_agents))
    assert result.status == "failed"
    assert any("sheet_skip probe" in finding for finding in result.findings)
