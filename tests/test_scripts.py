import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from table_env_bench.data.generators import list_families
from table_env_bench.scripts.audit_readability import build_parser as build_readability_audit_parser, run_audit
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
    args = parser.parse_args(["--instance-id", "public_dev_real_v1__channel_policy_transfer_icon_scope_cell_l1_s0"])
    assert args.instance_id == "public_dev_real_v1__channel_policy_transfer_icon_scope_cell_l1_s0"
    assert args.family is None
    assert args.level is None


def test_export_preview_gallery_writes_index_and_raster_artifacts(tmp_path) -> None:
    result = export_preview_gallery(tmp_path, seed=0)
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "review.html").exists()
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "workbook-canvas-renderer.js").exists()
    assert any(path.name.startswith("report_scope_reconciliation") for path in tmp_path.glob("*.png"))
    assert any(path.name.startswith("channel_policy_transfer") for path in tmp_path.glob("*.png"))
    assert any(path.name.startswith("inventory_exception_disambiguation") for path in tmp_path.glob("*.png"))
    assert any(path.name.startswith("report_scope_reconciliation") for path in tmp_path.glob("*.scene.json"))
    assert any(path.name.startswith("channel_policy_transfer") for path in tmp_path.glob("*.scene.json"))
    assert any(path.name.startswith("inventory_exception_disambiguation") for path in tmp_path.glob("*.scene.json"))
    manifest = (tmp_path / "manifest.json").read_text(encoding="utf-8")
    review_html = (tmp_path / "review.html").read_text(encoding="utf-8")
    assert '"surface_id"' in manifest
    assert '"kind"' in manifest
    assert '"sheet_id"' in manifest
    assert '"page_id"' in manifest
    assert "window.__TABLE_ENV_DEBUG__" in review_html
    assert 'searchParams.set(\'debug\', \'1\')' in review_html
    assert result["count"] > 0


def test_export_preview_gallery_can_filter_family_and_level(tmp_path) -> None:
    result = export_preview_gallery(tmp_path, seed=0, families=["channel_policy_transfer"], levels=[3])
    manifest = (tmp_path / "manifest.json").read_text(encoding="utf-8")

    assert result["count"] > 0
    assert "channel_policy_transfer" in manifest
    assert "report_scope_reconciliation" not in manifest
    assert '"level": "3"' in manifest
    assert '"level": "1"' not in manifest


def test_export_preview_gallery_includes_exception_note_overlay(tmp_path) -> None:
    export_preview_gallery(tmp_path, seed=0, families=["inventory_exception_disambiguation"], levels=[2, 3])
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    previews = manifest["previews"]

    assert previews
    assert all(preview["family"] == "inventory_exception_disambiguation" for preview in previews)
    assert any(preview["kind"] == "note_overlay" and preview["page_id"] == "exception-p2" for preview in previews)


def test_export_preview_gallery_supports_frozen_instance_pack(tmp_path) -> None:
    export_preview_gallery(
        tmp_path,
        pack="public_dev_real_v1",
        instance_ids=["public_dev_real_v1__report_scope_reconciliation_merged_scope_cell_l1_s0"],
    )
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["pack_id"] == "public_dev_real_v1"
    assert manifest["instance_ids"] == ["public_dev_real_v1__report_scope_reconciliation_merged_scope_cell_l1_s0"]
    assert any(
        preview["instance_id"] == "public_dev_real_v1__report_scope_reconciliation_merged_scope_cell_l1_s0"
        for preview in manifest["previews"]
    )


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
            "artifacts/tmp_public_pack_audit",
            "--pack",
            "public_smoke_real_v1",
            "--instance-id",
            "public_smoke_real_v1__channel_policy_transfer_icon_scope_cell_l1_s0",
            "--instance-id",
            "public_smoke_real_v1__report_scope_reconciliation_merged_scope_cell_l1_s0",
        ]
    )
    assert args.out == "artifacts/tmp_public_pack_audit"
    assert args.pack == "public_smoke_real_v1"
    assert args.instance_ids == [
        "public_smoke_real_v1__channel_policy_transfer_icon_scope_cell_l1_s0",
        "public_smoke_real_v1__report_scope_reconciliation_merged_scope_cell_l1_s0",
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
                                        {"mode": "workbench_navigation", "returncode": 0},
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


def test_run_audit_supports_public_pack_mode(monkeypatch, tmp_path) -> None:
    pack = SimpleNamespace(
        pack_id="public_smoke_real_v1",
        pack_label="Public Smoke Real v1",
        instances=(
            SimpleNamespace(
                instance_id="public_smoke_real_v1__channel_policy_transfer_icon_scope_cell_l1_s0",
                instance_label="채널 집행 기준 L1",
                family="channel_policy_transfer",
                level=1,
                benchmark_track="canonical_real_tableqa",
            ),
            SimpleNamespace(
                instance_id="public_smoke_real_v1__inventory_exception_disambiguation_pattern_vs_icon_statement_l1_s0",
                instance_label="재고 예외 판정 L1",
                family="inventory_exception_disambiguation",
                level=1,
                benchmark_track="canonical_real_tableqa",
            ),
        ),
    )

    monkeypatch.setattr("table_env_bench.scripts.audit_readability.load_instance_pack", lambda pack_id: pack)
    monkeypatch.setattr("table_env_bench.scripts.audit_readability.list_instances", lambda pack_id: list(pack.instances))

    def _fake_export_preview_gallery(out_dir, *, pack=None, instance_ids=None, **_kwargs):
        out_path = tmp_path / Path(out_dir).name if not isinstance(out_dir, Path) else out_dir
        out_path.mkdir(parents=True, exist_ok=True)
        previews = [
            {
                "surface_id": f"{instance_ids[0]}-query-query-p1",
                "family": "inventory_exception_disambiguation" if "inventory" in instance_ids[0] else "channel_policy_transfer",
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
        if "inventory" in instance_ids[0]:
            previews.append(
                {
                    "surface_id": f"{instance_ids[0]}-exception-exception-p2-note-scope-note",
                    "family": "inventory_exception_disambiguation",
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

    def _fake_run(command, cwd, env, capture_output, text, check):
        summary_path = env.get("PLAYWRIGHT_WORKBENCH_SUMMARY_PATH")
        if summary_path:
            Path(summary_path).write_text(
                json.dumps(
                    {
                        "pack_id": env.get("PLAYWRIGHT_TARGET_PACK_ID"),
                        "instance_id": env.get("PLAYWRIGHT_TARGET_INSTANCE_ID"),
                        "opened_notes": ["scope-note"] if "inventory" in env.get("PLAYWRIGHT_TARGET_INSTANCE_ID", "") else [],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            if "inventory" in env.get("PLAYWRIGHT_TARGET_INSTANCE_ID", ""):
                return SimpleNamespace(returncode=1, stdout="workbench failed", stderr="")
            return SimpleNamespace(returncode=0, stdout="workbench ok", stderr="")
        return SimpleNamespace(returncode=0, stdout="surface ok", stderr="")

    monkeypatch.setattr("table_env_bench.scripts.audit_readability.export_preview_gallery", _fake_export_preview_gallery)
    monkeypatch.setattr("table_env_bench.scripts.audit_readability.subprocess.run", _fake_run)
    monkeypatch.setattr("table_env_bench.scripts.audit_readability.shutil.which", lambda name: "/usr/bin/npm")

    summary = run_audit(out=tmp_path, pack="public_smoke_real_v1")

    assert summary["mode"] == "public_pack"
    assert summary["pack_id"] == "public_smoke_real_v1"
    assert summary["total_runs"] == 2
    assert summary["surface_failures"] == 0
    assert summary["workbench_failures"] == 1
    assert summary["blocking_failures"] == 1
    assert summary["runs"][0]["instance_id"] == "public_smoke_real_v1__channel_policy_transfer_icon_scope_cell_l1_s0"
    assert summary["runs"][1]["instance_id"] == "public_smoke_real_v1__inventory_exception_disambiguation_pattern_vs_icon_statement_l1_s0"
    assert summary["runs"][1]["workbench_navigation"]["summary"]["opened_notes"] == ["scope-note"]
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "summary.md").exists()
