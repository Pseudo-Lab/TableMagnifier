import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

from table_env_bench.data.generators import list_families
from table_env_bench.scripts.audit_readability import build_parser as build_readability_audit_parser, run_audit
from table_env_bench.scripts.export_agent_observation_gallery import export_agent_observation_gallery
from table_env_bench.scripts.export_preview_gallery import export_preview_gallery
from table_env_bench.scripts.eval_llm import build_parser as build_llm_parser
from table_env_bench.scripts.run_authoring_pipeline import build_parser as build_authoring_parser
from table_env_bench.scripts.run_demo import build_parser


def test_run_demo_parser_accepts_registered_families() -> None:
    parser = build_parser()
    args = parser.parse_args(["--family", list_families()[0], "--level", "1"])
    assert args.family in list_families()
    assert args.level == 1


def test_run_demo_parser_rejects_unknown_families() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--family", "subtotal_footnote", "--level", "1"])


def test_run_demo_parser_accepts_instance_id_without_family() -> None:
    parser = build_parser()
    args = parser.parse_args(["--instance-id", "example_pack_v1__k_vis_table_arc_symbol_rule_induction_l1_s0"])
    assert args.instance_id == "example_pack_v1__k_vis_table_arc_symbol_rule_induction_l1_s0"
    assert args.family is None
    assert args.level is None


def test_export_preview_gallery_writes_index_and_raster_artifacts(tmp_path) -> None:
    result = export_preview_gallery(tmp_path, seed=0)
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "review.html").exists()
    assert (tmp_path / "manifest.json").exists()
    assert any(path.name.startswith("k_vis_table_arc") for path in tmp_path.glob("*.png"))
    assert any(path.name.startswith("k_vis_table_arc") for path in tmp_path.glob("*.png"))
    assert any(path.name.startswith("k_vis_table_arc") for path in tmp_path.glob("*.scene.json"))
    assert any(path.name.startswith("k_vis_table_arc") for path in tmp_path.glob("*.scene.json"))
    manifest = (tmp_path / "manifest.json").read_text(encoding="utf-8")
    review_html = (tmp_path / "review.html").read_text(encoding="utf-8")
    assert '"surface_id"' in manifest
    assert '"kind"' in manifest
    assert '"sheet_id"' in manifest
    assert '"page_id"' in manifest
    assert '"required_navigation"' in manifest
    assert "window.__TABLE_ENV_DEBUG__" in review_html
    assert 'searchParams.set(\'debug\', \'1\')' in review_html
    assert result["count"] > 0


def test_export_preview_gallery_can_filter_family_and_level(tmp_path) -> None:
    result = export_preview_gallery(tmp_path, seed=0, families=["k_vis_table_arc"], levels=[3])
    manifest = (tmp_path / "manifest.json").read_text(encoding="utf-8")

    assert result["count"] > 0
    assert "k_vis_table_arc" in manifest
    assert '"level": "3"' in manifest
    assert '"level": "1"' not in manifest


def test_export_preview_gallery_includes_level3_exception_page(tmp_path) -> None:
    export_preview_gallery(tmp_path, seed=0, families=["k_vis_table_arc"], levels=[3])
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    previews = manifest["previews"]

    assert previews
    assert all(preview["family"] == "k_vis_table_arc" for preview in previews)
    assert any(preview["kind"] == "exception" and preview["page_id"] == "query-p2" for preview in previews)


def test_export_preview_gallery_rejects_removed_public_instance_pack(tmp_path) -> None:
    with pytest.raises(KeyError, match="Unknown instance pack"):
        export_preview_gallery(tmp_path, pack="example_pack_v1")


def test_export_agent_observation_gallery_writes_agent_view_artifacts(tmp_path) -> None:
    result = export_agent_observation_gallery(
        tmp_path,
        family="k_vis_table_arc",
        levels=[1],
        seeds=[0],
        template_id="symbol_rule_induction",
    )
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    review_html = (tmp_path / "review.html").read_text(encoding="utf-8")

    assert result["count"] == 2
    assert manifest["mode"] == "agent_observation"
    assert all(surface["family"] == "k_vis_table_arc" for surface in manifest["surfaces"])
    assert all((tmp_path / surface["png"]).exists() for surface in manifest["surfaces"])
    assert all((tmp_path / surface["observation"]).exists() for surface in manifest["surfaces"])
    assert all(surface["metric_source"] == "exporter_full_scene" for surface in manifest["surfaces"])
    assert all(surface["review_contract_version"] == 1 for surface in manifest["surfaces"])
    assert all((tmp_path / surface["semantic_snapshot"]).exists() for surface in manifest["surfaces"])
    assert manifest["validation"]["missing_semantic_snapshot_count"] == 0
    assert manifest["validation"]["stale_semantic_snapshot_count"] == 0
    assert manifest["validation"]["metric_source_mismatch"] == []
    index_html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "Agent surface QA" in index_html
    assert "review-dashboard-data" in index_html
    assert (tmp_path / "review-dashboard-assets" / "review-dashboard.css").exists()
    assert (tmp_path / "review-dashboard-assets" / "review-dashboard.js").exists()
    assert "agent-observation" in review_html
    assert 'data-review-contract-version="1"' in review_html
    assert "review-snapshot-json" in review_html
    assert "review-validation" in review_html
    assert "review-metrics" in review_html
    assert "review-status" in review_html
    assert "zoom-fit" in review_html
    assert "focus-toggle" in review_html
    assert result["dashboard"]["status"] == "skipped"
    assert result["dashboard"]["reason"] == "missing_human_screenshot_dir"


def test_export_agent_observation_gallery_delegates_dashboard_generation(tmp_path, monkeypatch) -> None:
    artifacts_root = tmp_path / "artifacts"
    human_dir = artifacts_root / "ui-design-review" / "all-problems"
    agent_dir = artifacts_root / "agent_observations_active"
    human_dir.mkdir(parents=True)
    calls: list[dict[str, Path]] = []

    fake_module = types.ModuleType("table_env_bench.scripts.export_review_dashboard")

    def fake_export_review_dashboard(*, artifacts_root, human_dir, agent_dir, agent_manifest):
        assert agent_manifest.exists()
        calls.append(
            {
                "artifacts_root": artifacts_root,
                "human_dir": human_dir,
                "agent_dir": agent_dir,
                "agent_manifest": agent_manifest,
            }
        )
        return {"index": str(artifacts_root / "index.html"), "agent_index": str(agent_dir / "index.html")}

    fake_module.export_review_dashboard = fake_export_review_dashboard
    monkeypatch.setitem(sys.modules, "table_env_bench.scripts.export_review_dashboard", fake_module)

    result = export_agent_observation_gallery(
        agent_dir,
        family="k_vis_table_arc",
        levels=[1],
        seeds=[0],
        template_id="symbol_rule_induction",
    )

    assert result["dashboard"]["status"] == "generated"
    assert calls == [
        {
            "artifacts_root": artifacts_root,
            "human_dir": human_dir,
            "agent_dir": agent_dir,
            "agent_manifest": agent_dir / "manifest.json",
        }
    ]


def test_eval_llm_parser_accepts_suite_and_model() -> None:
    parser = build_llm_parser()
    args = parser.parse_args(["--suite", "canonical_dev", "--model", "gpt-4o-mini"])
    assert args.suite == "canonical_dev"
    assert args.model == "gpt-4o-mini"


def test_run_authoring_pipeline_parser_accepts_stage_subset() -> None:
    parser = build_authoring_parser()
    args = parser.parse_args(["--family", list_families()[0], "--stages", "rulebook", "visual_qa"])
    assert args.family == list_families()[0]
    assert args.stages == ["rulebook", "visual_qa"]


def test_audit_readability_parser_accepts_family_subset_and_seed_samples() -> None:
    parser = build_readability_audit_parser()
    args = parser.parse_args(
        ["--out", "artifacts/tmp_audit", "--seed-samples", "0", "2", "--families", *list_families(), "--smoke", "--canonical-only"]
    )
    assert args.out == "artifacts/tmp_audit"
    assert args.seed_samples == [0, 2]
    assert args.families == list_families()
    assert args.smoke is True
    assert args.canonical_only is True


def test_audit_readability_parser_accepts_pack_and_instance_ids() -> None:
    parser = build_readability_audit_parser()
    args = parser.parse_args(
        [
            "--out",
            "artifacts/tmp_fixture_pack_audit",
            "--pack",
            "fixture_pack_v1",
            "--instance-id",
            "fixture_pack_v1__k_vis_table_arc_symbol_rule_induction_l1_s0",
            "--instance-id",
            "fixture_pack_v1__k_vis_table_arc_wide_table_navigation_l1_s0",
        ]
    )
    assert args.out == "artifacts/tmp_fixture_pack_audit"
    assert args.pack == "fixture_pack_v1"
    assert args.instance_ids == [
        "fixture_pack_v1__k_vis_table_arc_symbol_rule_induction_l1_s0",
        "fixture_pack_v1__k_vis_table_arc_wide_table_navigation_l1_s0",
    ]


def test_run_audit_writes_summary_and_counts_failures(monkeypatch, tmp_path) -> None:
    class FakeLeadAgent:
        def __init__(self) -> None:
            self.calls = []

        def run(self, *, target, backend="local", apply_changes=False):
            self.calls.append((target.family, target.level, tuple(target.seed_samples)))

            class _Result:
                def __init__(self, family: str) -> None:
                    self.run_id = f"run-{family}"
                    self.overall_status = "failed" if family == "beta" else "passed"
                    self.stage_results = [
                        type(
                            "Stage",
                            (),
                            {
                                "stage": "viewport_readability",
                                "findings": ["Invalid layout in surface review."] if family == "beta" else [],
                                "metrics": {
                                    "review_runs": [
                                        {"mode": "surface_review", "returncode": 1 if family == "beta" else 0},
                                        {"mode": "navigation_review", "returncode": 0},
                                    ]
                                },
                                "to_dict": lambda self: {"stage": "viewport_readability", "status": "failed" if family == "beta" else "passed"},
                            },
                        )()
                    ]

            return _Result(target.family)

    monkeypatch.setattr("table_env_bench.scripts.audit_readability.list_families", lambda: ["alpha", "beta"])
    monkeypatch.setattr("table_env_bench.scripts.audit_readability.list_levels", lambda family: [1])
    monkeypatch.setattr("table_env_bench.scripts.audit_readability.canonical_seed_capacity", lambda family, level: 4)

    lead = FakeLeadAgent()
    summary = run_audit(out=tmp_path, lead=lead)

    assert summary["blocking_failures"] == 1
    assert summary["surface_failures"] == 1
    assert summary["invalid_layout_count"] == 1
    assert summary["seed_coverage"] == {"alpha:L1": [0, 1, 2], "beta:L1": [0, 1, 2]}
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "summary.md").exists()


def test_run_audit_supports_instance_pack_mode(monkeypatch, tmp_path) -> None:
    pack = SimpleNamespace(
        pack_id="fixture_pack_v1",
        pack_label="Fixture Pack v1",
        instances=(
            SimpleNamespace(
                instance_id="fixture_pack_v1__k_vis_table_arc_symbol_rule_induction_l1_s0",
                instance_label="채널 집행 기준 L1",
                family="k_vis_table_arc",
                level=1,
                benchmark_track="korean_visual_table_agent_reasoning",
            ),
            SimpleNamespace(
                instance_id="fixture_pack_v1__k_vis_table_arc_wide_table_navigation_l1_s0",
                instance_label="재고 예외 판정 L1",
                family="k_vis_table_arc",
                level=1,
                benchmark_track="korean_visual_table_agent_reasoning",
            ),
        ),
    )

    monkeypatch.setattr("table_env_bench.scripts.audit_readability.load_instance_pack", lambda pack_id: pack)
    monkeypatch.setattr("table_env_bench.scripts.audit_readability.list_instances", lambda pack_id: list(pack.instances))
    monkeypatch.setattr("table_env_bench.scripts.audit_readability.load_instance", lambda instance_id: SimpleNamespace(metadata={}))

    def _fake_export_preview_gallery(out_dir, *, pack=None, instance_ids=None, **_kwargs):
        out_path = tmp_path / Path(out_dir).name if not isinstance(out_dir, Path) else out_dir
        out_path.mkdir(parents=True, exist_ok=True)
        (out_path / "index.html").write_text("<html></html>", encoding="utf-8")
        (out_path / "review.html").write_text("<html></html>", encoding="utf-8")
        (out_path / "demo.png").write_bytes(b"png")
        (out_path / "demo.scene.json").write_text("{}", encoding="utf-8")
        (out_path / "note.png").write_bytes(b"png")
        (out_path / "note.scene.json").write_text("{}", encoding="utf-8")
        previews = [
            {
                "surface_id": f"{instance_ids[0]}-query-query-p1",
                "family": "k_vis_table_arc",
                "family_label": "demo",
                "level": "1",
                "kind": "query",
                "sheet": "확인",
                "sheet_id": "query",
                "page": "확인 시트",
                "page_id": "query-p1",
                "png": "demo.png",
                "scene": "demo.scene.json",
                "instance_id": instance_ids[0],
                "pack_id": pack,
            }
        ]
        if "wide_table_navigation" in instance_ids[0]:
            previews.append(
                {
                    "surface_id": f"{instance_ids[0]}-exception-exception-p2-note-scope-note",
                    "family": "k_vis_table_arc",
                    "family_label": "demo",
                    "level": "1",
                    "kind": "note_overlay",
                    "sheet": "예외",
                    "sheet_id": "exception",
                    "page": "적용 범위 · 메모 scope-note",
                    "page_id": "exception-p2",
                    "png": "note.png",
                    "scene": "note.scene.json",
                    "instance_id": instance_ids[0],
                    "pack_id": pack,
                }
            )
        (out_path / "manifest.json").write_text(json.dumps({"previews": previews}, ensure_ascii=False), encoding="utf-8")
        return {"count": len(previews)}

    monkeypatch.setattr("table_env_bench.scripts.audit_readability.export_preview_gallery", _fake_export_preview_gallery)

    summary = run_audit(out=tmp_path, pack="fixture_pack_v1")

    assert summary["mode"] == "instance_pack"
    assert summary["pack_id"] == "fixture_pack_v1"
    assert summary["total_runs"] == 2
    assert summary["surface_failures"] == 0
    assert summary["navigation_failures"] == 0
    assert summary["blocking_failures"] == 0
    assert summary["runs"][0]["instance_id"] == "fixture_pack_v1__k_vis_table_arc_symbol_rule_induction_l1_s0"
    assert summary["runs"][1]["instance_id"] == "fixture_pack_v1__k_vis_table_arc_wide_table_navigation_l1_s0"
    assert summary["runs"][1]["navigation_review"]["required_navigation"] == {}
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "summary.md").exists()
