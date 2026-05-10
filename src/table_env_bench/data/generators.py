"""Public generator registry for canonical workbook episodes."""

from __future__ import annotations

from collections.abc import Callable

from table_env_bench.data.canonical_catalog import (
    CANONICAL_FAMILY_LABELS as _canonical_family_labels,
    benchmark_episode_records as _canonical_benchmark_episode_records,
    benchmark_split_manifest as _canonical_benchmark_split_manifest,
    benchmark_suite_manifest as _canonical_benchmark_suite_manifest,
    benchmark_suite_records as _canonical_benchmark_suite_records,
    canonical_episode_catalog as _canonical_episode_catalog,
    canonical_level_wrappers,
    canonical_seed_capacity as _canonical_seed_capacity,
    eval_hard_episode_catalog as _eval_hard_episode_catalog,
    generate_canonical_episode,
    list_templates as _canonical_list_templates,
)
from table_env_bench.data.instances import (
    instance_benchmark_records as _instance_benchmark_records,
    list_instance_packs as _list_instance_packs,
    list_instances as _list_instances,
    load_instance as _load_instance,
    load_instance_pack as _load_instance_pack,
)
from table_env_bench.data.models import EpisodeSpec

FAMILY_LABELS = dict(_canonical_family_labels)

CANONICAL_FAMILY_LEVELS: dict[str, dict[int, Callable[[int], EpisodeSpec]]] = canonical_level_wrappers()
FAMILY_LEVELS: dict[str, dict[int, Callable[[int], EpisodeSpec]]] = dict(CANONICAL_FAMILY_LEVELS)


def list_families() -> list[str]:
    return sorted(FAMILY_LEVELS)


def list_legacy_families() -> list[str]:
    return []


def list_pilot_families() -> list[str]:
    return []


def list_canonical_families() -> list[str]:
    return sorted(CANONICAL_FAMILY_LEVELS)


def list_levels(family: str) -> list[int]:
    if family not in FAMILY_LEVELS:
        raise KeyError(f"Unknown family: {family}")
    return sorted(FAMILY_LEVELS[family])


def list_templates(family: str, level: int) -> list[str]:
    return _canonical_list_templates(family, level)


def canonical_seed_capacity(family: str, level: int) -> int:
    return _canonical_seed_capacity(family, level)


def benchmark_split_manifest() -> dict[str, list[dict[str, object]]]:
    return _canonical_benchmark_split_manifest()


def benchmark_episode_records(*, split: str | None = None) -> list[dict[str, object]]:
    return _canonical_benchmark_episode_records(split=split)


def canonical_episode_catalog() -> list[dict[str, object]]:
    return _canonical_episode_catalog()


def eval_hard_episode_catalog() -> list[dict[str, object]]:
    return _eval_hard_episode_catalog()


def benchmark_suite_manifest() -> dict[str, list[dict[str, object]]]:
    manifest = _canonical_benchmark_suite_manifest()
    for pack in _list_instance_packs():
        manifest[pack.pack_id] = [instance.to_dict() for instance in pack.instances]
    return manifest


def benchmark_suite_records(*, suite: str | None = None) -> list[dict[str, object]]:
    if suite is None:
        records = _canonical_benchmark_suite_records(suite=None)
        for pack in _list_instance_packs():
            records.extend(_instance_benchmark_records(pack.pack_id))
        return records

    instance_pack_ids = {pack.pack_id for pack in _list_instance_packs()}
    if suite in instance_pack_ids:
        return _instance_benchmark_records(suite)
    return _canonical_benchmark_suite_records(suite=suite)


def list_instance_packs():
    return _list_instance_packs()


def load_instance_pack(pack_id: str):
    return _load_instance_pack(pack_id)


def list_instances(pack_id: str):
    return _list_instances(pack_id)


def load_instance(instance_id: str) -> EpisodeSpec:
    return _load_instance(instance_id)


def instance_benchmark_records(pack_id: str) -> list[dict[str, object]]:
    return _instance_benchmark_records(pack_id)


def generate_episode(family: str, level: int, seed: int = 0, *, template_id: str | None = None) -> EpisodeSpec:
    if family not in FAMILY_LEVELS:
        raise KeyError(f"Unknown family: {family}")
    if level not in FAMILY_LEVELS[family]:
        raise KeyError(f"Unknown level {level} for family {family}")
    return generate_canonical_episode(family, level, seed, template_id=template_id)
