from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from table_env_bench.authoring import LeadAgent, build_target
from table_env_bench.authoring.models import DEFAULT_SEED_SAMPLES, FileMutation, PipelineContext, StageResult
from table_env_bench.authoring.stages import ViewportReadabilityAgent
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
        target=build_target(family="channel_policy_transfer", level=3, seed_samples=(0,)),
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
            '{"seed": 0, "previews": [{"family": "inventory_exception_disambiguation", "level": "3", "surface_id": "surface-1", "kind": "note_overlay", "page_id": "exception-p2"}]}',
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
                '{"visited_pages": ["exception:1/2", "exception:2/2"], "opened_notes": ["scope-note"]}',
                encoding="utf-8",
            )
        return CompletedProcess(args=command, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(authoring_stages.shutil, "which", lambda _: "/usr/bin/npm")
    monkeypatch.setattr(authoring_stages, "export_preview_gallery", fake_export_preview_gallery)
    monkeypatch.setattr(authoring_stages.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(authoring_stages, "canonical_seed_capacity", lambda family, level: 1)

    context = PipelineContext(
        run_id="demo-run",
        target=build_target(family="inventory_exception_disambiguation", level=3, seed_samples=(0,)),
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
    assert result.metrics["review_runs"][-1]["summary"]["opened_notes"] == ["scope-note"]
    assert result.metrics["full_seed_mode"] is False


def test_viewport_readability_agent_expands_default_seed_samples_to_full_capacity(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "frontend").mkdir()

    def fake_export_preview_gallery(out_dir, *, seed, families, levels, template_id):
        review_dir = Path(out_dir)
        review_dir.mkdir(parents=True, exist_ok=True)
        (review_dir / "manifest.json").write_text(
            '{"seed": 0, "previews": [{"family": "channel_policy_transfer", "level": "1", "surface_id": "surface-1", "kind": "overview", "page_id": "examples-p1"}]}',
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
        target=build_target(family="channel_policy_transfer", level=1, seed_samples=DEFAULT_SEED_SAMPLES),
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
