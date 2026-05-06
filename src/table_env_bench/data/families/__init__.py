"""Canonical family registry."""

from table_env_bench.data.families.adapters import FamilyAdapter
from table_env_bench.data.families.marker_position_rule_transfer import (
    FAMILY as MARKER_POSITION_FAMILY,
    FAMILY_LABEL as MARKER_POSITION_LABEL,
    build_episode as build_marker_position_episode,
    list_manifests as list_marker_position_manifests,
)
from table_env_bench.data.families.excel_viewport_sheet_navigation import (
    FAMILY as EXCEL_VIEWPORT_FAMILY,
    FAMILY_LABEL as EXCEL_VIEWPORT_LABEL,
    build_episode as build_excel_viewport_episode,
    list_manifests as list_excel_viewport_manifests,
)
from table_env_bench.data.families.shared import CANONICAL_SEEDS_PER_TEMPLATE, TemplateManifest

CANONICAL_FAMILY_ADAPTERS = (
    FamilyAdapter(
        family=EXCEL_VIEWPORT_FAMILY,
        label=EXCEL_VIEWPORT_LABEL,
        build_episode=build_excel_viewport_episode,
        list_manifests=list_excel_viewport_manifests,
    ),
    FamilyAdapter(
        family=MARKER_POSITION_FAMILY,
        label=MARKER_POSITION_LABEL,
        build_episode=build_marker_position_episode,
        list_manifests=list_marker_position_manifests,
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
