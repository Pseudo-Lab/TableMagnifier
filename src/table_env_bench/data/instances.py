"""Frozen benchmark instance packs and loaders."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from table_env_bench.data.loader import load_episode_spec
from table_env_bench.data.models import EpisodeSpec

PRIVATE_DATA_ENV = "TABLE_BENCH_PRIVATE_DATA_DIR"


def _default_benchmark_track(pack_id: str) -> str:
    return "canonical_real_tableqa"


def _default_pack_role(pack_id: str) -> str:
    if pack_id.startswith("public_"):
        return "public"
    if pack_id.startswith("hidden_"):
        return "hidden_holdout"
    return "public"


@dataclass(frozen=True)
class InstanceRecord:
    instance_id: str
    instance_label: str
    pack_id: str
    family: str
    family_display_name: str
    level: int
    source_template_id: str
    source_seed: int
    source_episode_id: str
    task_summary: str
    decisive_evidence_surfaces: tuple[str, ...]
    expected_failure_mode: str
    question: str
    workbook_title: str
    max_actions: int
    sheet_count: int
    page_count: int
    spec_path: str
    benchmark_track: str
    reasoning_archetype: str | None
    abstraction_tier: str | None
    support_surface_policy: str | None
    qa_dependency: str | None
    generalization_group: str | None
    pack_role: str
    required_navigation: dict[str, Any]

    @classmethod
    def from_dict(cls, payload: dict[str, Any], *, pack_id: str) -> "InstanceRecord":
        return cls(
            instance_id=str(payload["instance_id"]),
            instance_label=str(payload["instance_label"]),
            pack_id=pack_id,
            family=str(payload["family"]),
            family_display_name=str(payload["family_display_name"]),
            level=int(payload["level"]),
            source_template_id=str(payload["source_template_id"]),
            source_seed=int(payload["source_seed"]),
            source_episode_id=str(payload["source_episode_id"]),
            task_summary=str(payload.get("task_summary", "")),
            decisive_evidence_surfaces=tuple(str(item) for item in payload.get("decisive_evidence_surfaces", [])),
            expected_failure_mode=str(payload["expected_failure_mode"]),
            question=str(payload["question"]),
            workbook_title=str(payload["workbook_title"]),
            max_actions=int(payload["max_actions"]),
            sheet_count=int(payload["sheet_count"]),
            page_count=int(payload["page_count"]),
            spec_path=str(payload["spec_path"]),
            benchmark_track=str(payload.get("benchmark_track", _default_benchmark_track(pack_id))),
            reasoning_archetype=str(payload["reasoning_archetype"]) if payload.get("reasoning_archetype") is not None else None,
            abstraction_tier=str(payload["abstraction_tier"]) if payload.get("abstraction_tier") is not None else None,
            support_surface_policy=str(payload["support_surface_policy"]) if payload.get("support_surface_policy") is not None else None,
            qa_dependency=str(payload["qa_dependency"]) if payload.get("qa_dependency") is not None else None,
            generalization_group=str(payload["generalization_group"]) if payload.get("generalization_group") is not None else None,
            pack_role=str(payload.get("pack_role", _default_pack_role(pack_id))),
            required_navigation=dict(payload.get("required_navigation", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "instance_label": self.instance_label,
            "pack_id": self.pack_id,
            "family": self.family,
            "family_display_name": self.family_display_name,
            "level": self.level,
            "source_template_id": self.source_template_id,
            "source_seed": self.source_seed,
            "source_episode_id": self.source_episode_id,
            "task_summary": self.task_summary,
            "decisive_evidence_surfaces": list(self.decisive_evidence_surfaces),
            "expected_failure_mode": self.expected_failure_mode,
            "question": self.question,
            "workbook_title": self.workbook_title,
            "max_actions": self.max_actions,
            "sheet_count": self.sheet_count,
            "page_count": self.page_count,
            "spec_path": self.spec_path,
            "benchmark_track": self.benchmark_track,
            "reasoning_archetype": self.reasoning_archetype,
            "abstraction_tier": self.abstraction_tier,
            "support_surface_policy": self.support_surface_policy,
            "qa_dependency": self.qa_dependency,
            "generalization_group": self.generalization_group,
            "pack_role": self.pack_role,
            "required_navigation": self.required_navigation,
        }


@dataclass(frozen=True)
class InstancePackManifest:
    pack_id: str
    pack_label: str
    version: str
    locale: str
    instances: tuple[InstanceRecord, ...]
    benchmark_track: str
    pack_role: str

    @property
    def instance_count(self) -> int:
        return len(self.instances)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "InstancePackManifest":
        pack_id = str(payload["pack_id"])
        return cls(
            pack_id=pack_id,
            pack_label=str(payload["pack_label"]),
            version=str(payload["version"]),
            locale=str(payload.get("locale", "ko-KR")),
            instances=tuple(InstanceRecord.from_dict(item, pack_id=pack_id) for item in payload.get("instances", [])),
            benchmark_track=str(payload.get("benchmark_track", _default_benchmark_track(pack_id))),
            pack_role=str(payload.get("pack_role", _default_pack_role(pack_id))),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "pack_label": self.pack_label,
            "version": self.version,
            "locale": self.locale,
            "instance_count": self.instance_count,
            "benchmark_track": self.benchmark_track,
            "pack_role": self.pack_role,
            "instances": [instance.to_dict() for instance in self.instances],
        }


def _repo_instances_root() -> Path:
    return Path(__file__).resolve().parent / "specs" / "instances"


def _private_instances_root() -> Path | None:
    raw = os.environ.get(PRIVATE_DATA_ENV)
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def _instance_roots() -> tuple[Path, ...]:
    roots: list[Path] = []
    repo_root = _repo_instances_root()
    if repo_root.exists():
        roots.append(repo_root)
    private_root = _private_instances_root()
    if private_root is not None and private_root.exists():
        roots.append(private_root)
    return tuple(roots)


def _pack_manifest_path(pack_id: str) -> Path:
    for root in _instance_roots():
        candidate = root / pack_id / "manifest.json"
        if candidate.exists():
            return candidate
    raise KeyError(f"Unknown instance pack: {pack_id}")


def load_instance_pack(pack_id: str) -> InstancePackManifest:
    manifest_path = _pack_manifest_path(pack_id)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    return InstancePackManifest.from_dict(payload)


def list_instance_packs() -> tuple[InstancePackManifest, ...]:
    manifests_by_id: dict[str, InstancePackManifest] = {}
    for root in _instance_roots():
        for manifest_path in sorted(root.glob("*/manifest.json")):
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest = InstancePackManifest.from_dict(payload)
            manifests_by_id.setdefault(manifest.pack_id, manifest)
    def _sort_key(manifest: InstancePackManifest) -> tuple[int, str]:
        public_rank = 0 if manifest.pack_role == "public" else 1
        return (public_rank, manifest.pack_id)

    return tuple(sorted(manifests_by_id.values(), key=_sort_key))


def list_instances(pack_id: str) -> tuple[InstanceRecord, ...]:
    return load_instance_pack(pack_id).instances


def _find_instance_record(instance_id: str) -> tuple[InstancePackManifest, InstanceRecord]:
    for pack in list_instance_packs():
        for instance in pack.instances:
            if instance.instance_id == instance_id:
                return pack, instance
    raise KeyError(f"Unknown benchmark instance: {instance_id}")


def _apply_metadata_defaults(spec: EpisodeSpec, *, pack: InstancePackManifest, instance: InstanceRecord) -> EpisodeSpec:
    metadata = dict(spec.metadata)
    metadata.setdefault("pack_id", pack.pack_id)
    metadata.setdefault("instance_id", instance.instance_id)
    metadata.setdefault("instance_label", instance.instance_label)
    metadata.setdefault("benchmark_track", pack.benchmark_track)
    metadata.setdefault("track", pack.benchmark_track)
    metadata.setdefault("reasoning_archetype", instance.reasoning_archetype)
    metadata.setdefault("abstraction_tier", instance.abstraction_tier)
    metadata.setdefault("support_surface_policy", instance.support_surface_policy)
    metadata.setdefault("qa_dependency", instance.qa_dependency)
    metadata.setdefault("generalization_group", instance.generalization_group or f"{spec.family}:{metadata.get('template_id')}:l{spec.level}")
    metadata.setdefault("pack_role", pack.pack_role)
    metadata.setdefault("task_summary", instance.task_summary)
    workbook_metadata = dict(spec.workbook.metadata)
    workbook_metadata.setdefault("track", metadata["track"])
    workbook_metadata.setdefault("benchmark_track", metadata["benchmark_track"])
    workbook = replace(spec.workbook, metadata=workbook_metadata)
    return replace(spec, workbook=workbook, metadata=metadata)


def load_instance(instance_id: str) -> EpisodeSpec:
    pack, instance = _find_instance_record(instance_id)
    spec_path = _pack_manifest_path(pack.pack_id).parent / instance.spec_path
    spec = load_episode_spec(spec_path)
    return _apply_metadata_defaults(spec, pack=pack, instance=instance)


def instance_benchmark_records(pack_id: str) -> list[dict[str, object]]:
    pack = load_instance_pack(pack_id)
    records: list[dict[str, object]] = []
    for instance in pack.instances:
        spec = load_instance(instance.instance_id)
        generalization_group = instance.generalization_group or spec.metadata.get("generalization_group")
        required_navigation = dict(spec.metadata.get("required_navigation", {}))
        records.append(
            {
                "suite": pack.pack_id,
                "pack_id": pack.pack_id,
                "pack_label": pack.pack_label,
                "pack_role": pack.pack_role,
                "instance_id": instance.instance_id,
                "instance_label": instance.instance_label,
                "episode_id": spec.episode_id,
                "family": spec.family,
                "family_display_name": spec.family_display_name,
                "level": spec.level,
                "seed": spec.seed,
                "template_id": spec.metadata.get("template_id"),
                "source_episode_id": instance.source_episode_id,
                "source_template_id": instance.source_template_id,
                "source_seed": instance.source_seed,
                "question": spec.question,
                "workbook_title": spec.workbook.title,
                "task_summary": instance.task_summary,
                "decisive_evidence_surfaces": list(instance.decisive_evidence_surfaces),
                "expected_failure_mode": instance.expected_failure_mode,
                "answer_form": spec.metadata.get("answer_form"),
                "primary_operator": spec.metadata.get("primary_operator"),
                "support_operator": spec.metadata.get("support_operator"),
                "operator_tags": list(spec.metadata.get("operator_tags", [])),
                "cue_tags": list(spec.metadata.get("cue_tags", [])),
                "required_visual_cues": list(spec.metadata.get("required_visual_cues", [])),
                "task_archetype": spec.metadata.get("task_archetype"),
                "scenario_context": spec.metadata.get("scenario_context"),
                "required_navigation": required_navigation,
                "required_sheet_ids": list(spec.metadata.get("required_sheet_ids", required_navigation.get("required_sheet_ids", []))),
                "required_page_refs": list(spec.metadata.get("required_page_refs", required_navigation.get("required_page_refs", []))),
                "required_actions": list(spec.metadata.get("required_actions", [])),
                "required_evidence": [dict(item) for item in spec.metadata.get("required_evidence", [])],
                "difficulty_tier": spec.metadata.get("difficulty_tier"),
                "level_rationale": spec.metadata.get("level_rationale"),
                "expected_reasoning_steps": list(spec.metadata.get("expected_reasoning_steps", [])),
                "shortcut_probes": list(spec.metadata.get("shortcut_probes", [])),
                "track": spec.metadata.get("track"),
                "benchmark_track": spec.metadata.get("benchmark_track"),
                "reasoning_archetype": spec.metadata.get("reasoning_archetype"),
                "abstraction_tier": spec.metadata.get("abstraction_tier"),
                "support_surface_policy": spec.metadata.get("support_surface_policy"),
                "qa_dependency": spec.metadata.get("qa_dependency"),
                "generalization_group": generalization_group,
            }
        )
    return records
