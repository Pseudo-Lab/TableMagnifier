"""Canonical family catalogs, manifests, and split definitions."""

from __future__ import annotations

from typing import Any

from table_env_bench.data.eval_hard import build_hard_episode, list_hard_manifests
from table_env_bench.data.families import (
    CANONICAL_BUILDERS,
    CANONICAL_FAMILY_LABELS,
    CANONICAL_SEEDS_PER_TEMPLATE,
    TemplateManifest,
    list_canonical_families,
    list_manifests,
)


def generate_canonical_episode(family: str, level: int, seed: int = 0, *, template_id: str | None = None):
    if family not in CANONICAL_BUILDERS:
        raise KeyError(f"Unknown canonical family: {family}")
    if template_id is not None:
        hard_templates = {manifest.template_id for manifest in list_hard_manifests(family, level)}
        if template_id in hard_templates:
            return build_hard_episode(family, level, seed, template_id)
    return CANONICAL_BUILDERS[family](level, seed, template_id=template_id)


def list_templates(family: str, level: int) -> list[str]:
    return [manifest.template_id for manifest in list_manifests(family, level)]


def template_manifest(family: str, level: int, template_id: str) -> TemplateManifest:
    for manifest in list_manifests(family, level):
        if manifest.template_id == template_id:
            return manifest
    raise KeyError(f"Unknown template {template_id} for {family} level {level}")


def canonical_seed_capacity(family: str, level: int) -> int:
    return len(list_manifests(family, level)) * CANONICAL_SEEDS_PER_TEMPLATE


def canonical_episode_catalog() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for family in list_canonical_families():
        for level in (1, 2, 3):
            for manifest in list_manifests(family, level):
                for seed_slot in range(CANONICAL_SEEDS_PER_TEMPLATE):
                    records.append(
                        {
                            "family": family,
                            "family_display_name": CANONICAL_FAMILY_LABELS[family],
                            "level": level,
                            "template_id": manifest.template_id,
                            "template_label": manifest.template_label,
                            "seed": seed_slot,
                            "episode_id": f"{family}_{manifest.template_id}_l{level}_s{seed_slot}",
                            "track": manifest.benchmark_track,
                            "benchmark_track": manifest.benchmark_track,
                            "answer_form": manifest.answer_form,
                            "primary_operator": manifest.primary_operator,
                            "support_operator": manifest.support_operator,
                            "operator_tags": list(manifest.operator_tags),
                            "cue_tags": list(manifest.cue_tags),
                            "required_visual_cues": list(manifest.required_visual_cues),
                            "task_archetype": manifest.task_archetype,
                            "scenario_context": manifest.scenario_context,
                            "reasoning_archetype": manifest.reasoning_archetype,
                            "abstraction_tier": manifest.abstraction_tier,
                            "support_surface_policy": manifest.support_surface_policy,
                            "qa_dependency": manifest.qa_dependency,
                            "generalization_group": manifest.generalization_group or f"{manifest.family}:{manifest.template_id}:l{level}",
                            "required_navigation": dict(manifest.required_navigation),
                            "required_sheet_ids": list(manifest.required_sheet_ids),
                            "required_page_refs": list(manifest.required_page_refs),
                            "required_actions": list(manifest.required_actions),
                            "required_evidence": [dict(item) for item in manifest.required_evidence],
                            "difficulty_tier": manifest.difficulty_tier,
                            "level_rationale": manifest.level_rationale,
                            "expected_reasoning_steps": list(manifest.expected_reasoning_steps),
                        }
                    )
    return records


def eval_hard_episode_catalog() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for family in list_canonical_families():
        for level in (2, 3):
            for manifest in list_hard_manifests(family, level):
                for seed_slot in range(CANONICAL_SEEDS_PER_TEMPLATE):
                    records.append(
                        {
                            "family": family,
                            "family_display_name": CANONICAL_FAMILY_LABELS[family],
                            "level": level,
                            "template_id": manifest.template_id,
                            "template_label": manifest.template_label,
                            "seed": seed_slot,
                            "episode_id": f"{family}_{manifest.template_id}_l{level}_s{seed_slot}",
                            "track": manifest.benchmark_track,
                            "benchmark_track": manifest.benchmark_track,
                            "difficulty_tier": "eval_hard",
                            "answer_form": manifest.answer_form,
                            "primary_operator": manifest.primary_operator,
                            "support_operator": manifest.support_operator,
                            "operator_tags": list(manifest.operator_tags),
                            "cue_tags": list(manifest.cue_tags),
                            "required_visual_cues": list(manifest.required_visual_cues),
                            "task_archetype": manifest.task_archetype,
                            "scenario_context": manifest.scenario_context,
                            "reasoning_archetype": manifest.reasoning_archetype,
                            "abstraction_tier": manifest.abstraction_tier,
                            "support_surface_policy": manifest.support_surface_policy,
                            "qa_dependency": manifest.qa_dependency,
                            "generalization_group": manifest.generalization_group or f"{manifest.family}:{manifest.template_id}:l{level}",
                            "required_navigation": dict(manifest.required_navigation),
                            "required_sheet_ids": list(manifest.required_sheet_ids),
                            "required_page_refs": list(manifest.required_page_refs),
                            "required_actions": list(manifest.required_actions),
                            "required_evidence": [dict(item) for item in manifest.required_evidence],
                            "required_capabilities": list(manifest.required_capabilities or manifest.capability_axes),
                            "level_rationale": manifest.level_rationale,
                            "expected_reasoning_steps": list(manifest.expected_reasoning_steps),
                            "shortcut_probes": list(manifest.shortcut_probes),
                            "holdout_group": manifest.holdout_group,
                            "pair_group": manifest.pair_group,
                            "variant": manifest.variant,
                        }
                    )
    return records


def benchmark_split_manifest() -> dict[str, list[dict[str, Any]]]:
    splits = {"dev_public": [], "test_holdout": []}
    for family in list_canonical_families():
        for level in (1, 2, 3):
            manifests = list_manifests(family, level)
            for index, manifest in enumerate(manifests):
                split_name = "dev_public" if index < 2 else "test_holdout"
                splits[split_name].append(
                    {
                        "family": family,
                        "level": level,
                        "template_id": manifest.template_id,
                        "template_label": manifest.template_label,
                        "seed_slots": list(range(CANONICAL_SEEDS_PER_TEMPLATE)),
                        "answer_form": manifest.answer_form,
                        "primary_operator": manifest.primary_operator,
                        "support_operator": manifest.support_operator,
                        "operator_tags": list(manifest.operator_tags),
                        "cue_tags": list(manifest.cue_tags),
                        "required_visual_cues": list(manifest.required_visual_cues),
                        "task_archetype": manifest.task_archetype,
                        "scenario_context": manifest.scenario_context,
                        "benchmark_track": manifest.benchmark_track,
                        "reasoning_archetype": manifest.reasoning_archetype,
                        "abstraction_tier": manifest.abstraction_tier,
                        "support_surface_policy": manifest.support_surface_policy,
                        "qa_dependency": manifest.qa_dependency,
                        "generalization_group": manifest.generalization_group or f"{manifest.family}:{manifest.template_id}:l{level}",
                        "required_navigation": dict(manifest.required_navigation),
                        "required_sheet_ids": list(manifest.required_sheet_ids),
                        "required_page_refs": list(manifest.required_page_refs),
                        "required_actions": list(manifest.required_actions),
                        "required_evidence": [dict(item) for item in manifest.required_evidence],
                        "difficulty_tier": manifest.difficulty_tier,
                        "level_rationale": manifest.level_rationale,
                        "expected_reasoning_steps": list(manifest.expected_reasoning_steps),
                    }
                )
    return splits


def benchmark_suite_manifest() -> dict[str, list[dict[str, Any]]]:
    suites = {
        "canonical_dev": benchmark_split_manifest()["dev_public"],
        "eval_hard_dev": [],
        "eval_hard_holdout": [],
    }
    for family in list_canonical_families():
        for level in (2, 3):
            target_suite = "eval_hard_dev" if level == 2 else "eval_hard_holdout"
            for manifest in list_hard_manifests(family, level):
                suites[target_suite].append(
                    {
                        "family": family,
                        "level": level,
                        "template_id": manifest.template_id,
                        "template_label": manifest.template_label,
                        "seed_slots": list(range(CANONICAL_SEEDS_PER_TEMPLATE)),
                        "difficulty_tier": manifest.difficulty_tier,
                        "answer_form": manifest.answer_form,
                        "primary_operator": manifest.primary_operator,
                        "support_operator": manifest.support_operator,
                        "operator_tags": list(manifest.operator_tags),
                        "cue_tags": list(manifest.cue_tags),
                        "required_visual_cues": list(manifest.required_visual_cues),
                        "task_archetype": manifest.task_archetype,
                        "scenario_context": manifest.scenario_context,
                        "benchmark_track": manifest.benchmark_track,
                        "reasoning_archetype": manifest.reasoning_archetype,
                        "abstraction_tier": manifest.abstraction_tier,
                        "support_surface_policy": manifest.support_surface_policy,
                        "qa_dependency": manifest.qa_dependency,
                        "generalization_group": manifest.generalization_group or f"{manifest.family}:{manifest.template_id}:l{level}",
                        "required_navigation": dict(manifest.required_navigation),
                        "required_sheet_ids": list(manifest.required_sheet_ids),
                        "required_page_refs": list(manifest.required_page_refs),
                        "required_actions": list(manifest.required_actions),
                        "required_evidence": [dict(item) for item in manifest.required_evidence],
                        "level_rationale": manifest.level_rationale,
                        "expected_reasoning_steps": list(manifest.expected_reasoning_steps),
                        "holdout_group": manifest.holdout_group,
                        "pair_group": manifest.pair_group,
                        "variant": manifest.variant,
                    }
                )
    return suites


def benchmark_episode_records(*, split: str | None = None) -> list[dict[str, Any]]:
    split_manifest = benchmark_split_manifest()
    selected_refs: list[dict[str, Any]]
    if split is None:
        selected_refs = [*split_manifest["dev_public"], *split_manifest["test_holdout"]]
    else:
        if split not in split_manifest:
            raise KeyError(f"Unknown split: {split}")
        selected_refs = split_manifest[split]
    records: list[dict[str, Any]] = []
    for ref in selected_refs:
        manifest = template_manifest(ref["family"], ref["level"], ref["template_id"])
        for seed_slot in ref["seed_slots"]:
            records.append(
                {
                    "family": ref["family"],
                    "level": ref["level"],
                    "template_id": ref["template_id"],
                    "seed": seed_slot,
                    "episode_id": f"{ref['family']}_{ref['template_id']}_l{ref['level']}_s{seed_slot}",
                    "answer_form": manifest.answer_form,
                    "primary_operator": manifest.primary_operator,
                    "support_operator": manifest.support_operator,
                    "operator_tags": list(manifest.operator_tags),
                    "cue_tags": list(manifest.cue_tags),
                    "required_visual_cues": list(manifest.required_visual_cues),
                    "task_archetype": manifest.task_archetype,
                    "scenario_context": manifest.scenario_context,
                    "benchmark_track": manifest.benchmark_track,
                    "reasoning_archetype": manifest.reasoning_archetype,
                    "abstraction_tier": manifest.abstraction_tier,
                    "support_surface_policy": manifest.support_surface_policy,
                    "qa_dependency": manifest.qa_dependency,
                    "generalization_group": manifest.generalization_group or f"{manifest.family}:{manifest.template_id}:l{ref['level']}",
                    "required_navigation": dict(manifest.required_navigation),
                    "required_sheet_ids": list(manifest.required_sheet_ids),
                    "required_page_refs": list(manifest.required_page_refs),
                    "required_actions": list(manifest.required_actions),
                    "required_evidence": [dict(item) for item in manifest.required_evidence],
                    "difficulty_tier": manifest.difficulty_tier,
                    "level_rationale": manifest.level_rationale,
                    "expected_reasoning_steps": list(manifest.expected_reasoning_steps),
                }
            )
    return records


def benchmark_suite_records(*, suite: str | None = None) -> list[dict[str, Any]]:
    suite_manifest = benchmark_suite_manifest()
    if suite is None:
        selected_refs = [*suite_manifest["canonical_dev"], *suite_manifest["eval_hard_dev"], *suite_manifest["eval_hard_holdout"]]
    else:
        if suite not in suite_manifest:
            raise KeyError(f"Unknown suite: {suite}")
        selected_refs = suite_manifest[suite]
    records: list[dict[str, Any]] = []
    for ref in selected_refs:
        manifest = None
        hard_manifest_map = {item.template_id: item for item in list_hard_manifests(ref["family"], ref["level"])}
        if ref["template_id"] in hard_manifest_map:
            manifest = hard_manifest_map[ref["template_id"]]
        else:
            manifest = template_manifest(ref["family"], ref["level"], ref["template_id"])
        for seed_slot in ref["seed_slots"]:
            records.append(
                {
                    "family": ref["family"],
                    "level": ref["level"],
                    "template_id": ref["template_id"],
                    "seed": seed_slot,
                    "episode_id": f"{ref['family']}_{ref['template_id']}_l{ref['level']}_s{seed_slot}",
                    "track": manifest.benchmark_track,
                    "benchmark_track": manifest.benchmark_track,
                    "difficulty_tier": manifest.difficulty_tier,
                    "answer_form": manifest.answer_form,
                    "primary_operator": manifest.primary_operator,
                    "support_operator": manifest.support_operator,
                    "operator_tags": list(manifest.operator_tags),
                    "cue_tags": list(manifest.cue_tags),
                    "required_visual_cues": list(manifest.required_visual_cues),
                    "task_archetype": manifest.task_archetype,
                    "scenario_context": manifest.scenario_context,
                    "reasoning_archetype": manifest.reasoning_archetype,
                    "abstraction_tier": manifest.abstraction_tier,
                    "support_surface_policy": manifest.support_surface_policy,
                    "qa_dependency": manifest.qa_dependency,
                    "generalization_group": manifest.generalization_group or f"{manifest.family}:{manifest.template_id}:l{ref['level']}",
                    "required_navigation": dict(manifest.required_navigation),
                    "required_sheet_ids": list(manifest.required_sheet_ids),
                    "required_page_refs": list(manifest.required_page_refs),
                    "required_actions": list(manifest.required_actions),
                    "required_evidence": [dict(item) for item in manifest.required_evidence],
                    "required_capabilities": list(manifest.required_capabilities or manifest.capability_axes),
                    "level_rationale": manifest.level_rationale,
                    "expected_reasoning_steps": list(manifest.expected_reasoning_steps),
                    "shortcut_probes": list(manifest.shortcut_probes),
                    "holdout_group": manifest.holdout_group,
                    "pair_group": manifest.pair_group,
                    "variant": manifest.variant,
                }
            )
    return records


def canonical_level_wrappers() -> dict[str, dict[int, Any]]:
    return {
        family: {
            level: (lambda seed, *, _family=family, _level=level: generate_canonical_episode(_family, _level, seed))
            for level in (1, 2, 3)
        }
        for family in list_canonical_families()
    }
