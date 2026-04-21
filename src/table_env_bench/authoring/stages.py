"""Built-in authoring stages."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from table_env_bench.authoring.models import DEFAULT_SEED_SAMPLES, AuthoringAgent, FileMutation, PipelineContext, StageResult
from table_env_bench.baselines import GreedySubmitAgent, NoNoteAgent, SinglePageAgent, TextScrapeHeuristicAgent, run_episode
from table_env_bench.data.canonical_catalog import template_manifest
from table_env_bench.data.generators import FAMILY_LABELS, canonical_seed_capacity, generate_episode, list_levels, list_templates
from table_env_bench.env.actions import WorkbookAction
from table_env_bench.env.environment import WorkbookEnv
from table_env_bench.scripts.export_preview_gallery import export_preview_gallery


def _selected_levels(context: PipelineContext) -> list[int]:
    if context.target.level is not None:
        return [context.target.level]
    return list_levels(context.target.family)


def _selected_seed_samples(context: PipelineContext, level: int) -> list[int]:
    capacity = canonical_seed_capacity(context.target.family, level)
    return [seed for seed in context.target.seed_samples if seed < capacity]


def _selected_readability_seed_samples(context: PipelineContext, level: int) -> list[int]:
    capacity = canonical_seed_capacity(context.target.family, level)
    if tuple(context.target.seed_samples) == DEFAULT_SEED_SAMPLES:
        return list(range(capacity))
    return [seed for seed in context.target.seed_samples if seed < capacity]


def _selected_templates(context: PipelineContext, level: int) -> list[str]:
    if context.target.template_id is not None:
        return [context.target.template_id]
    return list_templates(context.target.family, level)


def _ensure_family(context: PipelineContext) -> None:
    levels = list_levels(context.target.family)
    if not levels:
        raise KeyError(f"Unknown family: {context.target.family}")


def _sheet_ids(workbook: Any) -> list[str]:
    return [sheet.sheet_id for sheet in workbook.sheets]


def _find_sheet(workbook: Any, sheet_id: str) -> Any | None:
    for sheet in workbook.sheets:
        if sheet.sheet_id == sheet_id:
            return sheet
    return None


def _find_page(sheet: Any, page_id: str) -> Any | None:
    for page in sheet.pages:
        if page.page_id == page_id:
            return page
    return None


def _normalized_evidence(items: Any) -> set[tuple[Any, ...]]:
    normalized: set[tuple[Any, ...]] = set()
    for item in items or []:
        normalized.add(
            (
                item.get("kind"),
                item.get("sheet_id"),
                item.get("page_id"),
                item.get("note_id"),
            )
        )
    return normalized


def _json_mutation(path: str, payload: dict[str, Any]) -> FileMutation:
    import json

    return FileMutation(path=path, content=json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _stage_attempt_dir(context: PipelineContext, stage: str, attempt: int) -> Path:
    path = context.artifact_root / stage / f"attempt_{attempt}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _relpath(context: PipelineContext, path: Path) -> str:
    return str(path.relative_to(context.repo_root))


@dataclass
class QueryOnlyAgent:
    name: str = "query_only"

    def reset(self, observation: dict[str, Any], info: dict[str, Any]) -> None:
        return None

    def act(self, observation: dict[str, Any], info: dict[str, Any]) -> WorkbookAction:
        last_sheet = info["sheet_tabs"][-1]
        if observation["current_sheet_name"] != last_sheet:
            return WorkbookAction(type="select_sheet", sheet=last_sheet)
        return WorkbookAction(type="submit_answer", text="A")


@dataclass
class NoExamplesPage2Agent:
    name: str = "no_examples_page2"

    def reset(self, observation: dict[str, Any], info: dict[str, Any]) -> None:
        return None

    def act(self, observation: dict[str, Any], info: dict[str, Any]) -> WorkbookAction:
        current_sheet = observation["current_sheet_name"]
        if current_sheet == "examples":
            return WorkbookAction(type="select_sheet", sheet=info["sheet_tabs"][-1])
        return WorkbookAction(type="submit_answer", text="A")


@dataclass
class NoAppendixAgent:
    name: str = "no_appendix"

    def reset(self, observation: dict[str, Any], info: dict[str, Any]) -> None:
        return None

    def act(self, observation: dict[str, Any], info: dict[str, Any]) -> WorkbookAction:
        sheet_tabs = list(info["sheet_tabs"])
        current_sheet = observation["current_sheet_name"]
        if current_sheet == "examples" and observation["current_page_index"] < observation["page_count_in_sheet"] - 1:
            return WorkbookAction(type="next_page")
        if "query" in sheet_tabs and current_sheet != "query":
            return WorkbookAction(type="select_sheet", sheet="query")
        return WorkbookAction(type="submit_answer", text="A")


@dataclass
class NoExceptionAgent:
    name: str = "no_exception"

    def reset(self, observation: dict[str, Any], info: dict[str, Any]) -> None:
        return None

    def act(self, observation: dict[str, Any], info: dict[str, Any]) -> WorkbookAction:
        current_sheet = observation["current_sheet_name"]
        if current_sheet != "query":
            return WorkbookAction(type="select_sheet", sheet="query")
        return WorkbookAction(type="submit_answer", text="A")


@dataclass
class NoExceptionNoteAgent:
    name: str = "no_exception_note"

    def reset(self, observation: dict[str, Any], info: dict[str, Any]) -> None:
        return None

    def act(self, observation: dict[str, Any], info: dict[str, Any]) -> WorkbookAction:
        current_sheet = observation["current_sheet_name"]
        current_page = int(observation["current_page_index"])
        page_count = int(observation["page_count_in_sheet"])
        if current_sheet == "examples":
            return WorkbookAction(type="select_sheet", sheet="exception")
        if current_sheet == "exception" and current_page < page_count - 1:
            return WorkbookAction(type="next_page")
        if current_sheet != "query":
            return WorkbookAction(type="select_sheet", sheet="query")
        return WorkbookAction(type="submit_answer", text="A")


@dataclass
class RulebookAgent:
    name: str = "rulebook"
    stage: str = "rulebook"
    allowed_prefixes: tuple[str, ...] = ("docs",)

    def run(self, context: PipelineContext, *, attempt: int = 1) -> tuple[StageResult, list[FileMutation]]:
        _ensure_family(context)
        docs = [
            "PLANS.md",
            "docs/visual_cue_inventory.md",
            "docs/operator_taxonomy.md",
            "docs/answer_form_policy.md",
            "docs/level_design_policy.md",
            "docs/episode_validation_checklist.md",
        ]
        missing_docs = [path for path in docs if not (context.repo_root / path).exists()]
        levels = _selected_levels(context)
        manifests: list[dict[str, Any]] = []
        for level in levels:
            for template_id in _selected_templates(context, level):
                manifest = template_manifest(context.target.family, level, template_id)
                manifests.append(
                    {
                        "level": level,
                        "template_id": template_id,
                        "answer_form": manifest.answer_form,
                        "primary_operator": manifest.primary_operator,
                        "support_operator": manifest.support_operator,
                        "operator_tags": list(manifest.operator_tags),
                        "cue_tags": list(manifest.cue_tags),
                        "required_visual_cues": list(manifest.required_visual_cues),
                    }
                )
        contract = {
            "family": context.target.family,
            "family_display_name": FAMILY_LABELS.get(context.target.family, context.target.family),
            "levels": levels,
            "template_id": context.target.template_id,
            "seed_samples": list(context.target.seed_samples),
            "referenced_docs": docs,
            "missing_docs": missing_docs,
            "manifests": manifests,
            "repair_round": context.repair_round,
            "repair_reason": context.repair_reason,
        }
        result = StageResult(
            stage=self.stage,
            status="failed" if missing_docs else "passed",
            summary="Rule contract refreshed from active docs and manifest metadata.",
            findings=[f"Missing document: {path}" for path in missing_docs],
            metrics={"manifest_count": len(manifests), "doc_count": len(docs)},
            attempt=attempt,
        )
        return result, [_json_mutation(f"docs/authoring/rule_contracts/{context.target.family}.json", contract)]


@dataclass
class FamilyBuilderAgent:
    name: str = "family_builder"
    stage: str = "family_builder"
    allowed_prefixes: tuple[str, ...] = ("src/table_env_bench/data/families/contracts",)

    def run(self, context: PipelineContext, *, attempt: int = 1) -> tuple[StageResult, list[FileMutation]]:
        _ensure_family(context)
        levels = _selected_levels(context)
        implementation_records: list[dict[str, Any]] = []
        for level in levels:
            templates = _selected_templates(context, level)
            implementation_records.append(
                {
                    "level": level,
                    "templates": templates,
                    "seed_samples": _selected_seed_samples(context, level),
                    "seed_capacity": canonical_seed_capacity(context.target.family, level),
                }
            )
        build_contract = {
            "family": context.target.family,
            "level": context.target.level,
            "template_id": context.target.template_id,
            "implementation_records": implementation_records,
            "repair_round": context.repair_round,
            "repair_reason": context.repair_reason,
        }
        result = StageResult(
            stage=self.stage,
            status="passed",
            summary="Family build contract generated for the requested target.",
            findings=[],
            metrics={"record_count": len(implementation_records)},
            attempt=attempt,
        )
        return result, [_json_mutation(f"src/table_env_bench/data/families/contracts/{context.target.family}.json", build_contract)]


@dataclass
class VisualQAAgent:
    name: str = "visual_qa"
    stage: str = "visual_qa"
    allowed_prefixes: tuple[str, ...] = ()

    def run(self, context: PipelineContext, *, attempt: int = 1) -> tuple[StageResult, list[FileMutation]]:
        _ensure_family(context)
        findings: list[str] = []
        checked = 0
        scene_region_counts: list[int] = []
        for level in _selected_levels(context):
            for seed in _selected_seed_samples(context, level):
                env = WorkbookEnv(
                    family=context.target.family,
                    level=level,
                    seed=seed,
                    template_id=context.target.template_id,
                )
                observation, info = env.reset()
                checked += 1
                scene_page = observation["viewport_scene"]["page"]
                if not observation["viewport_image_png_base64"]:
                    findings.append(f"Missing viewport image for level {level} seed {seed}.")
                if not scene_page.get("elements"):
                    findings.append(f"Missing rendered elements for level {level} seed {seed}.")
                if not scene_page.get("regions"):
                    findings.append(f"Missing public regions for level {level} seed {seed}.")
                if info.get("family") != context.target.family:
                    findings.append(f"Family mismatch in info for level {level} seed {seed}.")
                if context.target.family == "channel_policy_transfer":
                    page_ids = [page.page_id for page in env.spec.workbook.sheets[0].pages]
                    if level == 1 and page_ids != ["examples-p1"]:
                        findings.append("Level 1 should expose only one examples page.")
                    if level == 2 and page_ids != ["examples-p1", "examples-p2"]:
                        findings.append("Level 2 should expose two examples pages.")
                    if level == 3:
                        sheet_ids = [sheet.sheet_id for sheet in env.spec.workbook.sheets]
                        if sheet_ids != ["examples", "appendix", "query"]:
                            findings.append("Level 3 should expose examples, appendix, and query sheets.")
                        appendix_page = env.spec.workbook.sheets[1].pages[0]
                        if not appendix_page.notes:
                            findings.append("Level 3 appendix page should expose an openable note.")
                if context.target.family == "inventory_exception_disambiguation":
                    expected_sheet_ids = ["examples", "exception", "query"]
                    actual_sheet_ids = _sheet_ids(env.spec.workbook)
                    if actual_sheet_ids != expected_sheet_ids:
                        findings.append(
                            f"Inventory exception family should expose sheets {expected_sheet_ids}, found {actual_sheet_ids}."
                        )
                    exception_sheet = _find_sheet(env.spec.workbook, "exception")
                    if exception_sheet is None:
                        findings.append("Exception sheet is missing.")
                    else:
                        page_ids = [page.page_id for page in exception_sheet.pages]
                        expected_exception_pages = ["exception-p1"]
                        if level >= 2:
                            expected_exception_pages.append("exception-p2")
                        if page_ids != expected_exception_pages:
                            findings.append(
                                f"Exception pages should be {expected_exception_pages}, found {page_ids}."
                            )
                        metadata_actions = list(env.spec.metadata.get("required_actions", []))
                        expected_actions = ["must_switch_sheet", "must_visit_exception"]
                        if level >= 2:
                            expected_actions.append("must_open_note")
                        if metadata_actions != expected_actions:
                            findings.append(
                                f"Required actions should be {expected_actions}, found {metadata_actions}."
                            )
                        metadata_sheet_ids = list(env.spec.metadata.get("required_sheet_ids", []))
                        if metadata_sheet_ids != expected_sheet_ids:
                            findings.append(
                                f"Required sheet ids should be {expected_sheet_ids}, found {metadata_sheet_ids}."
                            )
                        expected_page_refs = [
                            "examples:examples-p1",
                            "exception:exception-p1",
                            "query:query-p1",
                        ]
                        if level >= 2:
                            expected_page_refs.append("exception:exception-p2")
                        metadata_page_refs = list(env.spec.metadata.get("required_page_refs", []))
                        if metadata_page_refs != expected_page_refs:
                            findings.append(
                                f"Required page refs should be {expected_page_refs}, found {metadata_page_refs}."
                            )
                        expected_evidence = {
                            ("page", "examples", "examples-p1", None),
                            ("page", "exception", "exception-p1", None),
                            ("page", "query", "query-p1", None),
                        }
                        if level >= 2:
                            expected_evidence.add(("page", "exception", "exception-p2", None))
                            expected_evidence.add(("note", "exception", "exception-p2", "scope-note"))
                        metadata_evidence = _normalized_evidence(env.spec.metadata.get("required_evidence", []))
                        if metadata_evidence != expected_evidence:
                            findings.append(
                                "Required evidence should match the workbook topology for the inventory exception family."
                            )
                        if level == 1 and "must_open_note" in metadata_actions:
                            findings.append("Level 1 should not require opening a note.")
                        if level >= 2:
                            exception_p2 = _find_page(exception_sheet, "exception-p2")
                            if exception_p2 is None:
                                findings.append("Level 2/3 should expose exception-p2.")
                            else:
                                note_ids = [note.id for note in exception_p2.notes]
                                if not note_ids:
                                    findings.append("Level 2/3 exception-p2 should expose a note.")
                                if "scope-note" not in note_ids:
                                    findings.append("Level 2/3 exception-p2 should expose scope-note.")
                                note_marker_regions = [region for region in exception_p2.regions if region.role == "note_marker"]
                                if not note_marker_regions:
                                    findings.append("Level 2/3 exception-p2 should expose a note_marker region.")
                                elif all(region.linked_note_id != "scope-note" for region in note_marker_regions):
                                    findings.append("Level 2/3 note_marker region should link to scope-note.")
                        elif "must_open_note" in metadata_actions:
                            findings.append("Level 1 should not advertise must_open_note.")
                scene_region_counts.append(len(scene_page.get("regions", [])))
        result = StageResult(
            stage=self.stage,
            status="failed" if findings else "passed",
            summary="Viewport, scene, and region smoke checks completed.",
            findings=findings,
            metrics={"episodes_checked": checked, "avg_region_count": mean(scene_region_counts) if scene_region_counts else 0.0},
            attempt=attempt,
        )
        return result, []


@dataclass
class ViewportReadabilityAgent:
    name: str = "viewport_readability"
    stage: str = "viewport_readability"
    allowed_prefixes: tuple[str, ...] = ()

    def run(self, context: PipelineContext, *, attempt: int = 1) -> tuple[StageResult, list[FileMutation]]:
        _ensure_family(context)
        frontend_root = context.repo_root / "frontend"
        if not frontend_root.exists():
            result = StageResult(
                stage=self.stage,
                status="blocked",
                summary="Frontend workspace is missing; Playwright readability gate could not run.",
                findings=["Missing frontend directory for Playwright readability review."],
                attempt=attempt,
            )
            return result, []
        if shutil.which("npm") is None:
            result = StageResult(
                stage=self.stage,
                status="blocked",
                summary="npm is unavailable; Playwright readability gate could not run.",
                findings=["npm was not found in PATH."],
                attempt=attempt,
            )
            return result, []

        selected_levels = _selected_levels(context)
        seed_map = {level: _selected_readability_seed_samples(context, level) for level in selected_levels}
        review_targets = [(level, seed) for level in selected_levels for seed in seed_map[level]]
        if not review_targets:
            result = StageResult(
                stage=self.stage,
                status="failed",
                summary="No valid seeds remained for the viewport readability review.",
                findings=["No valid seeds remained after applying canonical seed capacity."],
                attempt=attempt,
            )
            return result, []

        stage_dir = _stage_attempt_dir(context, self.stage, attempt)
        playwright_artifact_root = stage_dir / "playwright"
        findings: list[str] = []
        artifact_paths: list[str] = []
        review_runs: list[dict[str, Any]] = []

        for level, seed in review_targets:
            review_dir = stage_dir / f"review_l{level}_seed_{seed}"
            export_result = export_preview_gallery(
                review_dir,
                seed=seed,
                families=[context.target.family],
                levels=[level],
                template_id=context.target.template_id,
            )
            manifest_path = review_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            filtered_previews = [
                preview
                for preview in manifest["previews"]
                if preview["family"] == context.target.family and int(preview["level"]) == level
            ]
            manifest["previews"] = filtered_previews
            manifest["selected_family"] = context.target.family
            manifest["selected_levels"] = [level]
            manifest["seed"] = seed
            manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

            stdout_path = stage_dir / f"playwright_l{level}_seed_{seed}.stdout.log"
            stderr_path = stage_dir / f"playwright_l{level}_seed_{seed}.stderr.log"
            port = 8781 + ((level * 10 + seed) % 10)
            env = os.environ.copy()
            env.update(
                {
                    "PLAYWRIGHT_ENABLE_WORKBENCH": "0",
                    "PLAYWRIGHT_REVIEW_DIR": os.path.relpath(review_dir, frontend_root),
                    "PLAYWRIGHT_BASE_URL": f"http://127.0.0.1:{port}",
                    "PLAYWRIGHT_STATIC_PORT": str(port),
                    "PLAYWRIGHT_ARTIFACT_ROOT": os.path.relpath(playwright_artifact_root, frontend_root),
                }
            )
            command = [
                "npm",
                "exec",
                "--",
                "playwright",
                "test",
                "playwright/surface-readability.spec.ts",
                "--project=chromium-fullhd",
            ]
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
            artifact_paths.extend(
                [
                    _relpath(context, manifest_path),
                    _relpath(context, stdout_path),
                    _relpath(context, stderr_path),
                ]
            )
            if playwright_artifact_root.exists():
                artifact_paths.append(_relpath(context, playwright_artifact_root))
            review_runs.append(
                {
                    "level": level,
                    "seed": seed,
                    "mode": "surface_review",
                    "surface_count": len(filtered_previews),
                    "returncode": completed.returncode,
                    "review_dir": _relpath(context, review_dir),
                    "export_count": export_result["count"],
                }
            )
            if not filtered_previews:
                findings.append(f"Level {level} seed {seed} produced no review surfaces for {context.target.family}.")
            elif completed.returncode != 0:
                findings.append(f"Level {level} seed {seed} failed the Playwright viewport readability gate.")

            workbench_stdout_path = stage_dir / f"workbench_l{level}_seed_{seed}.stdout.log"
            workbench_stderr_path = stage_dir / f"workbench_l{level}_seed_{seed}.stderr.log"
            workbench_summary_path = stage_dir / f"workbench_l{level}_seed_{seed}.summary.json"
            workbench_artifact_root = stage_dir / "playwright_workbench"
            workbench_env = os.environ.copy()
            workbench_env.update(
                {
                    "PLAYWRIGHT_ENABLE_WORKBENCH": "1",
                    "PLAYWRIGHT_TARGET_FAMILY": context.target.family,
                    "PLAYWRIGHT_TARGET_LEVEL": str(level),
                    "PLAYWRIGHT_TARGET_SEED": str(seed),
                    "PLAYWRIGHT_WORKBENCH_SUMMARY_PATH": str(workbench_summary_path),
                    "PLAYWRIGHT_ARTIFACT_ROOT": os.path.relpath(workbench_artifact_root, frontend_root),
                }
            )
            workbench_command = [
                "npm",
                "exec",
                "--",
                "playwright",
                "test",
                "playwright/workbench-navigation-readability.spec.ts",
                "--project=chromium-fullhd",
            ]
            workbench_completed = subprocess.run(
                workbench_command,
                cwd=frontend_root,
                env=workbench_env,
                capture_output=True,
                text=True,
                check=False,
            )
            workbench_stdout_path.write_text(workbench_completed.stdout, encoding="utf-8")
            workbench_stderr_path.write_text(workbench_completed.stderr, encoding="utf-8")
            artifact_paths.extend(
                [
                    _relpath(context, workbench_stdout_path),
                    _relpath(context, workbench_stderr_path),
                ]
            )
            if workbench_artifact_root.exists():
                artifact_paths.append(_relpath(context, workbench_artifact_root))
            workbench_summary: dict[str, Any] | None = None
            if workbench_summary_path.exists():
                artifact_paths.append(_relpath(context, workbench_summary_path))
                workbench_summary = json.loads(workbench_summary_path.read_text(encoding="utf-8"))
                if context.target.family == "inventory_exception_disambiguation" and level >= 2:
                    opened_notes = list(workbench_summary.get("opened_notes", []))
                    if "scope-note" not in opened_notes:
                        findings.append(
                            f"Level {level} seed {seed} did not open scope-note during workbench readability traversal."
                        )
            elif context.target.family == "inventory_exception_disambiguation" and level >= 2:
                findings.append(f"Level {level} seed {seed} did not produce a workbench readability summary.")
            review_runs.append(
                {
                    "level": level,
                    "seed": seed,
                    "mode": "workbench_navigation",
                    "returncode": workbench_completed.returncode,
                    "summary": workbench_summary,
                }
            )
            if workbench_completed.returncode != 0:
                findings.append(f"Level {level} seed {seed} failed the workbench page traversal readability gate.")

        result = StageResult(
            stage=self.stage,
            status="failed" if findings else "passed",
            summary="Playwright viewport readability sweep completed.",
            findings=findings,
            artifact_paths=artifact_paths,
            metrics={
                "review_runs": review_runs,
                "review_target_count": len(review_targets),
                "seed_map": {f"l{level}": seeds for level, seeds in seed_map.items()},
                "full_seed_mode": tuple(context.target.seed_samples) == DEFAULT_SEED_SAMPLES,
            },
            attempt=attempt,
        )
        return result, []


@dataclass
class RedTeamSolverAgent:
    name: str = "red_team_solver"
    stage: str = "red_team_solver"
    allowed_prefixes: tuple[str, ...] = ()

    def run(self, context: PipelineContext, *, attempt: int = 1) -> tuple[StageResult, list[FileMutation]]:
        _ensure_family(context)
        if context.target.template_id is not None:
            findings = ["Template-specific red-team sweep is not yet supported; using requested template only."]
        else:
            findings = []
        agent_builders = {
            "single_page": SinglePageAgent,
            "no_note": NoNoteAgent,
            "text_scrape": TextScrapeHeuristicAgent,
            "greedy_submit": GreedySubmitAgent,
        }
        if context.target.family == "channel_policy_transfer":
            agent_builders.update(
                {
                    "query_only": QueryOnlyAgent,
                    "no_examples_page2": NoExamplesPage2Agent,
                    "no_appendix": NoAppendixAgent,
                }
            )
        if context.target.family == "inventory_exception_disambiguation":
            agent_builders["no_exception"] = NoExceptionAgent
            if any(level >= 2 for level in _selected_levels(context)):
                agent_builders["no_exception_note"] = NoExceptionNoteAgent
        selected_levels = _selected_levels(context)
        scores: dict[int, dict[str, list[float]]] = {level: {name: [] for name in agent_builders} for level in selected_levels}
        for level in selected_levels:
            for seed in _selected_seed_samples(context, level):
                for name, builder in agent_builders.items():
                    env = WorkbookEnv(
                        family=context.target.family,
                        level=level,
                        seed=seed,
                        template_id=context.target.template_id,
                    )
                    result = run_episode(env, builder())
                    scores[level][name].append(float(result.evaluation.correctness.value))
        level_scores = {
            f"l{level}": {name: (mean(values) if values else 0.0) for name, values in probe_scores.items()}
            for level, probe_scores in scores.items()
        }
        summary_scores = {
            name: mean([level_scores[f"l{level}"].get(name, 0.0) for level in selected_levels])
            for name in agent_builders
        }
        if any(level_scores[f"l{level}"].get("text_scrape", 0.0) >= 0.75 for level in selected_levels):
            findings.append("Text scrape baseline remains highly successful on at least one checked level; shortcut risk is still present.")
        if summary_scores.get("query_only", 0.0) >= 0.5:
            findings.append("Query-only probe still solves too many channel_policy_transfer episodes.")
        if summary_scores.get("no_appendix", 0.0) >= 0.5:
            findings.append("Appendix-skipping probe still solves too many channel_policy_transfer episodes.")
        if context.target.family == "inventory_exception_disambiguation":
            if any(level_scores[f"l{level}"].get("no_exception", 0.0) >= 0.25 for level in selected_levels):
                findings.append("No-exception probe still solves too many inventory_exception_disambiguation episodes.")
            if any(
                level_scores[f"l{level}"].get("no_exception_note", 0.0) >= 0.25
                for level in selected_levels
                if level >= 2
            ):
                findings.append("No-exception-note probe still solves too many inventory_exception_disambiguation episodes.")
        result = StageResult(
            stage=self.stage,
            status="failed" if findings else "passed",
            summary="Restricted baseline sweep completed.",
            findings=findings,
            metrics={"average_correctness": summary_scores, "level_average_correctness": level_scores},
            attempt=attempt,
        )
        return result, []


@dataclass
class RegressionGateAgent:
    name: str = "regression_gate"
    stage: str = "regression_gate"
    allowed_prefixes: tuple[str, ...] = ()

    def run(self, context: PipelineContext, *, attempt: int = 1) -> tuple[StageResult, list[FileMutation]]:
        _ensure_family(context)
        findings: list[str] = []
        smoke_records: list[dict[str, Any]] = []
        for level in _selected_levels(context):
            seed_samples = _selected_seed_samples(context, level)
            if not seed_samples:
                findings.append(f"No valid seeds remained for level {level}.")
                continue
            env = WorkbookEnv(
                family=context.target.family,
                level=level,
                seed=seed_samples[0],
                template_id=context.target.template_id,
            )
            observation, info = env.reset()
            smoke_records.append(
                {
                    "level": level,
                    "seed": seed_samples[0],
                    "sheet_tabs": info["sheet_tabs"],
                    "page_id": observation["viewport_scene"]["page"]["page_id"],
                }
            )
            if not info["sheet_tabs"]:
                findings.append(f"No sheet tabs for level {level}.")
        if context.backend == "openai" and not os.environ.get("OPENAI_API_KEY"):
            findings.append("OPENAI_API_KEY is not set; openai backend downgraded to advisory mode.")
        result = StageResult(
            stage=self.stage,
            status="failed" if [item for item in findings if "downgraded" not in item] else "passed",
            summary="Programmatic smoke gate completed.",
            findings=findings,
            metrics={"smoke_records": smoke_records},
            attempt=attempt,
        )
        return result, []


def default_stage_map() -> dict[str, AuthoringAgent]:
    agents: list[AuthoringAgent] = [
        RulebookAgent(),
        FamilyBuilderAgent(),
        VisualQAAgent(),
        ViewportReadabilityAgent(),
        RedTeamSolverAgent(),
        RegressionGateAgent(),
    ]
    return {agent.stage: agent for agent in agents}
