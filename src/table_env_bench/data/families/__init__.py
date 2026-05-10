"""Canonical family registry."""

from table_env_bench.data.families.adapters import FamilyAdapter
from table_env_bench.data.families.k_vis_table_arc import (
    FAMILY as K_VIS_TABLE_ARC_FAMILY,
    FAMILY_LABEL as K_VIS_TABLE_ARC_LABEL,
    build_episode as build_k_vis_table_arc_episode,
    list_manifests as list_k_vis_table_arc_manifests,
)
from table_env_bench.data.families.shared import CANONICAL_SEEDS_PER_TEMPLATE, TemplateManifest

CANONICAL_FAMILY_ADAPTERS = (
    FamilyAdapter(
        family=K_VIS_TABLE_ARC_FAMILY,
        label=K_VIS_TABLE_ARC_LABEL,
        build_episode=build_k_vis_table_arc_episode,
        list_manifests=list_k_vis_table_arc_manifests,
    ),
)

for _adapter in CANONICAL_FAMILY_ADAPTERS:
    _adapter.validate()

if len({adapter.family for adapter in CANONICAL_FAMILY_ADAPTERS}) != len(CANONICAL_FAMILY_ADAPTERS):
    raise ValueError("Canonical family adapters must have unique family ids")

CANONICAL_FAMILY_LABELS = {adapter.family: adapter.label for adapter in CANONICAL_FAMILY_ADAPTERS}
CANONICAL_MANIFEST_LISTERS = {adapter.family: adapter.list_manifests for adapter in CANONICAL_FAMILY_ADAPTERS}
CANONICAL_BUILDERS = {adapter.family: adapter.build_episode for adapter in CANONICAL_FAMILY_ADAPTERS}


def list_canonical_families() -> list[str]:
    return sorted(CANONICAL_BUILDERS)


def list_manifests(family: str, level: int) -> tuple[TemplateManifest, ...]:
    if family not in CANONICAL_MANIFEST_LISTERS:
        raise KeyError(f"Unknown canonical family: {family}")
    return CANONICAL_MANIFEST_LISTERS[family](level)


__all__ = [
    "CANONICAL_FAMILY_ADAPTERS",
    "CANONICAL_BUILDERS",
    "CANONICAL_FAMILY_LABELS",
    "CANONICAL_MANIFEST_LISTERS",
    "CANONICAL_SEEDS_PER_TEMPLATE",
    "TemplateManifest",
    "list_canonical_families",
    "list_manifests",
]
