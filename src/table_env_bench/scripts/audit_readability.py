"""Run a repo-wide viewport readability audit."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

from table_env_bench.authoring import LeadAgent, build_target
from table_env_bench.authoring.models import DEFAULT_SEED_SAMPLES
from table_env_bench.data.generators import (
    canonical_seed_capacity,
    list_instance_packs,
    list_instances,
    list_canonical_families,
    list_families,
    list_legacy_families,
    list_levels,
    list_pilot_families,
    load_instance_pack,
)
from table_env_bench.scripts.export_preview_gallery import export_preview_gallery


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the viewport readability audit across benchmark families.")
    parser.add_argument("--out", default="artifacts/readability_audit")
    parser.add_argument("--families", nargs="*")
    parser.add_argument("--seed-samples", nargs="*", type=int)
    parser.add_argument("--pack")
    parser.add_argument("--instance-id", action="append", dest="instance_ids")
    parser.add_argument("--canonical-only", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    return parser


def _family_tracks() -> dict[str, str]:
    tracks: dict[str, str] = {}
    for family in list_canonical_families():
        tracks[family] = "canonical"
    for family in list_legacy_families():
        tracks[family] = "legacy"
    for family in list_pilot_families():
        tracks[family] = "pilot"
    for family in list_families():
        tracks.setdefault(family, "canonical")
    return tracks


def _render_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Viewport Readability Audit",
        "",
        f"- mode: {summary['mode']}",
        f"- total runs: {summary['total_runs']}",
        f"- passing runs: {summary['passing_runs']}",
        f"- blocking failures: {summary['blocking_failures']}",
        f"- invalid layout count: {summary['invalid_layout_count']}",
        f"- surface failures: {summary['surface_failures']}",
        f"- workbench failures: {summary['workbench_failures']}",
        "",
        "## Runs",
    ]
    for run in summary["runs"]:
        status = "PASS" if run["passed"] else "FAIL"
        if run.get("instance_id") is not None:
            lines.append(
                f"- [{status}] {run['pack_id']} · {run['instance_id']} · {run['family']} L{run['level']}"
            )
        else:
            lines.append(
                f"- [{status}] {run['family']} L{run['level']} · {run['track']} · seeds {run['seeds']} · {run['run_id']}"
            )
    return "\n".join(lines) + "\n"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _frontend_root(repo_root: Path) -> Path:
    frontend_root = repo_root / "frontend"
    if not frontend_root.exists():
        raise RuntimeError("Frontend workspace is missing; Playwright readability gate could not run.")
    if shutil.which("npm") is None:
        raise RuntimeError("npm is unavailable; Playwright readability gate could not run.")
    return frontend_root


def _relpath(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _resolve_pack_instances(*, pack: str | None, instance_ids: list[str] | None) -> tuple[Any, list[Any]]:
    if pack is not None:
        pack_manifest = load_instance_pack(pack)
        instances_by_id = {instance.instance_id: instance for instance in list_instances(pack)}
        if instance_ids:
            selected_instances: list[Any] = []
            for instance_id in instance_ids:
                if instance_id not in instances_by_id:
                    raise KeyError(f"Unknown benchmark instance in pack {pack}: {instance_id}")
                selected_instances.append(instances_by_id[instance_id])
            return pack_manifest, selected_instances
        return pack_manifest, list(pack_manifest.instances)

    if instance_ids:
        owners: dict[str, tuple[Any, Any]] = {}
        for pack_manifest in list_instance_packs():
            for instance in pack_manifest.instances:
                owners[instance.instance_id] = (pack_manifest, instance)
        resolved: list[tuple[Any, Any]] = []
        for instance_id in instance_ids:
            owner = owners.get(instance_id)
            if owner is None:
                raise KeyError(f"Unknown benchmark instance: {instance_id}")
            resolved.append(owner)
        pack_ids = {pack_manifest.pack_id for pack_manifest, _ in resolved}
        if len(pack_ids) != 1:
            raise ValueError("All --instance-id values must belong to the same pack when --pack is omitted.")
        pack_manifest = resolved[0][0]
        return pack_manifest, [instance for _, instance in resolved]

    packs = list_instance_packs()
    if not packs:
        raise ValueError("No frozen instance packs are available.")
    pack_manifest = packs[0]
    return pack_manifest, list(pack_manifest.instances)


def _run_playwright(
    *,
    frontend_root: Path,
    command: list[str],
    env: dict[str, str],
    stdout_path: Path,
    stderr_path: Path,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=frontend_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    return completed


def _run_pack_audit(
    *,
    out_dir: Path,
    pack: str | None,
    instance_ids: list[str] | None,
) -> dict[str, Any]:
    repo_root = _repo_root()
    frontend_root = _frontend_root(repo_root)
    pack_manifest, selected_instances = _resolve_pack_instances(pack=pack, instance_ids=instance_ids)

    rows: list[dict[str, Any]] = []
    invalid_layout_count = 0
    surface_failures = 0
    workbench_failures = 0

    for index, instance in enumerate(selected_instances):
        instance_dir = out_dir / pack_manifest.pack_id / instance.instance_id
        review_dir = instance_dir / "preview_review"
        review_dir.mkdir(parents=True, exist_ok=True)
        export_result = export_preview_gallery(review_dir, pack=pack_manifest.pack_id, instance_ids=[instance.instance_id])
        manifest_path = review_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_note_overlay = any(preview.get("kind") == "note_overlay" for preview in manifest.get("previews", []))

        surface_stdout_path = instance_dir / "surface.stdout.log"
        surface_stderr_path = instance_dir / "surface.stderr.log"
        surface_artifact_root = instance_dir / "playwright_surface"
        surface_port = 8781 + (index % 10)
        surface_env = os.environ.copy()
        surface_env.update(
            {
                "PLAYWRIGHT_ENABLE_WORKBENCH": "0",
                "PLAYWRIGHT_REVIEW_DIR": os.path.relpath(review_dir, frontend_root),
                "PLAYWRIGHT_BASE_URL": f"http://127.0.0.1:{surface_port}",
                "PLAYWRIGHT_STATIC_PORT": str(surface_port),
                "PLAYWRIGHT_ARTIFACT_ROOT": os.path.relpath(surface_artifact_root, frontend_root),
            }
        )
        surface_completed = _run_playwright(
            frontend_root=frontend_root,
            command=[
                "npm",
                "exec",
                "--",
                "playwright",
                "test",
                "playwright/surface-readability.spec.ts",
                "--project=chromium-fullhd",
            ],
            env=surface_env,
            stdout_path=surface_stdout_path,
            stderr_path=surface_stderr_path,
        )

        workbench_stdout_path = instance_dir / "workbench.stdout.log"
        workbench_stderr_path = instance_dir / "workbench.stderr.log"
        workbench_summary_path = instance_dir / "workbench.summary.json"
        workbench_artifact_root = instance_dir / "playwright_workbench"
        workbench_env = os.environ.copy()
        workbench_env.update(
            {
                "PLAYWRIGHT_ENABLE_WORKBENCH": "1",
                "PLAYWRIGHT_TARGET_PACK_ID": pack_manifest.pack_id,
                "PLAYWRIGHT_TARGET_INSTANCE_ID": instance.instance_id,
                "PLAYWRIGHT_WORKBENCH_SUMMARY_PATH": os.path.relpath(workbench_summary_path, frontend_root),
                "PLAYWRIGHT_ARTIFACT_ROOT": os.path.relpath(workbench_artifact_root, frontend_root),
            }
        )
        workbench_completed = _run_playwright(
            frontend_root=frontend_root,
            command=[
                "npm",
                "exec",
                "--",
                "playwright",
                "test",
                "playwright/workbench-navigation-readability.spec.ts",
                "--project=chromium-fullhd",
            ],
            env=workbench_env,
            stdout_path=workbench_stdout_path,
            stderr_path=workbench_stderr_path,
        )

        workbench_summary = None
        if workbench_summary_path.exists():
            workbench_summary = json.loads(workbench_summary_path.read_text(encoding="utf-8"))

        findings: list[str] = []
        if surface_completed.returncode != 0:
            surface_failures += 1
            invalid_layout_count += 1
            findings.append("Surface readability gate failed.")
        if workbench_completed.returncode != 0:
            workbench_failures += 1
            findings.append("Workbench traversal readability gate failed.")
        if expected_note_overlay and not (workbench_summary or {}).get("opened_notes"):
            findings.append("Expected note overlay exists but no note was opened during workbench traversal.")

        artifact_paths = [
            _relpath(manifest_path, repo_root),
            _relpath(surface_stdout_path, repo_root),
            _relpath(surface_stderr_path, repo_root),
            _relpath(workbench_stdout_path, repo_root),
            _relpath(workbench_stderr_path, repo_root),
        ]
        if surface_artifact_root.exists():
            artifact_paths.append(_relpath(surface_artifact_root, repo_root))
        if workbench_artifact_root.exists():
            artifact_paths.append(_relpath(workbench_artifact_root, repo_root))
        if workbench_summary_path.exists():
            artifact_paths.append(_relpath(workbench_summary_path, repo_root))

        rows.append(
            {
                "pack_id": pack_manifest.pack_id,
                "pack_label": pack_manifest.pack_label,
                "instance_id": instance.instance_id,
                "instance_label": instance.instance_label,
                "family": instance.family,
                "level": instance.level,
                "track": instance.benchmark_track,
                "passed": not findings,
                "run_id": instance.instance_id,
                "surface_review": {
                    "returncode": surface_completed.returncode,
                    "surface_count": export_result["count"],
                    "review_dir": _relpath(review_dir, repo_root),
                },
                "workbench_navigation": {
                    "returncode": workbench_completed.returncode,
                    "summary": workbench_summary,
                },
                "expected_note_overlay": expected_note_overlay,
                "artifact_paths": artifact_paths,
                "findings": findings,
            }
        )

    summary = {
        "mode": "public_pack",
        "canonical_only": False,
        "pack_id": pack_manifest.pack_id,
        "pack_label": pack_manifest.pack_label,
        "instance_ids": [instance.instance_id for instance in selected_instances],
        "total_runs": len(rows),
        "passing_runs": sum(1 for row in rows if row["passed"]),
        "blocking_failures": sum(1 for row in rows if not row["passed"]),
        "invalid_layout_count": invalid_layout_count,
        "surface_failures": surface_failures,
        "workbench_failures": workbench_failures,
        "seed_coverage": {},
        "runs": rows,
    }
    return summary


def _selected_families(*, requested: list[str] | None, canonical_only: bool) -> list[str]:
    if requested:
        return requested
    if canonical_only:
        return list_canonical_families()
    return list_families()


def _selected_seed_samples(*, family: str, level: int, smoke: bool, requested: list[int] | None) -> tuple[int, ...]:
    capacity = canonical_seed_capacity(family, level)
    if smoke:
        seeds = requested if requested is not None else [0]
        return tuple(seed for seed in seeds if 0 <= seed < capacity)
    if requested is not None:
        return tuple(seed for seed in requested if 0 <= seed < capacity)
    return DEFAULT_SEED_SAMPLES


def run_audit(
    *,
    out: str | Path,
    families: list[str] | None = None,
    seed_samples: list[int] | None = None,
    pack: str | None = None,
    instance_ids: list[str] | None = None,
    canonical_only: bool = False,
    smoke: bool = False,
    lead: LeadAgent | None = None,
) -> dict[str, Any]:
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if pack is not None or instance_ids is not None:
        summary = _run_pack_audit(out_dir=out_dir, pack=pack, instance_ids=instance_ids)
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        (out_dir / "summary.md").write_text(_render_markdown(summary), encoding="utf-8")
        return summary

    repo_root = _repo_root()
    audit_lead = lead or LeadAgent(repo_root=repo_root)
    tracks = _family_tracks()
    selected_families = _selected_families(requested=families, canonical_only=canonical_only)
    rows: list[dict[str, Any]] = []
    invalid_layout_count = 0
    surface_failures = 0
    workbench_failures = 0
    seed_coverage: dict[str, list[int]] = {}

    for family in selected_families:
        track = tracks.get(family, "canonical")
        for level in list_levels(family):
            run_seed_samples = _selected_seed_samples(
                family=family,
                level=level,
                smoke=smoke,
                requested=seed_samples,
            )
            seed_coverage[f"{family}:L{level}"] = list(run_seed_samples)
            record = audit_lead.run(
                target=build_target(
                    family=family,
                    level=level,
                    stages=("viewport_readability",),
                    seed_samples=run_seed_samples,
                ),
                apply_changes=False,
            )
            passed = record.overall_status == "passed"
            stage_results = [result.to_dict() for result in record.stage_results]
            review_runs = []
            for result in record.stage_results:
                if result.stage != "viewport_readability":
                    continue
                review_runs.extend(result.metrics.get("review_runs", []))
                invalid_layout_count += sum(
                    1
                    for finding in result.findings
                    if "invalid layout" in finding.lower() or "layout error" in finding.lower()
                )
            surface_failures += sum(
                1 for review in review_runs if review.get("mode") == "surface_review" and review.get("returncode", 0) != 0
            )
            workbench_failures += sum(
                1
                for review in review_runs
                if review.get("mode") == "workbench_navigation" and review.get("returncode", 0) != 0
            )
            rows.append(
                {
                    "family": family,
                    "level": level,
                    "track": track,
                    "passed": passed,
                    "run_id": record.run_id,
                    "seeds": list(run_seed_samples),
                    "stage_results": stage_results,
                }
            )

    summary = {
        "mode": "smoke" if smoke else "strict",
        "canonical_only": canonical_only,
        "total_runs": len(rows),
        "passing_runs": sum(1 for row in rows if row["passed"]),
        "blocking_failures": sum(1 for row in rows if not row["passed"]),
        "invalid_layout_count": invalid_layout_count,
        "surface_failures": surface_failures,
        "workbench_failures": workbench_failures,
        "seed_coverage": seed_coverage,
        "runs": rows,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "summary.md").write_text(_render_markdown(summary), encoding="utf-8")
    return summary


def main() -> None:
    args = build_parser().parse_args()
    summary = run_audit(
        out=args.out,
        families=args.families,
        seed_samples=args.seed_samples,
        pack=args.pack,
        instance_ids=args.instance_ids,
        canonical_only=args.canonical_only,
        smoke=args.smoke,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    raise SystemExit(1 if summary["blocking_failures"] else 0)


if __name__ == "__main__":
    main()
