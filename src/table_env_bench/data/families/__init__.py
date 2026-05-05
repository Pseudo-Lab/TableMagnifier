"""Canonical family registry."""

from table_env_bench.data.families.inventory_exception_disambiguation import (
    FAMILY as INVENTORY_EXCEPTION_FAMILY,
    FAMILY_LABEL as INVENTORY_EXCEPTION_LABEL,
    build_episode as build_inventory_exception_episode,
    list_manifests as list_inventory_exception_manifests,
)
from table_env_bench.data.families.channel_policy_transfer import (
    FAMILY as CHANNEL_POLICY_FAMILY,
    FAMILY_LABEL as CHANNEL_POLICY_LABEL,
    build_episode as build_channel_policy_transfer_episode,
    list_manifests as list_channel_policy_transfer_manifests,
)
from table_env_bench.data.families.report_scope_reconciliation import (
    FAMILY as REPORT_SCOPE_FAMILY,
    FAMILY_LABEL as REPORT_SCOPE_LABEL,
    build_episode as build_report_scope_episode,
    list_manifests as list_report_scope_manifests,
)
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

CANONICAL_FAMILY_LABELS = {
    INVENTORY_EXCEPTION_FAMILY: INVENTORY_EXCEPTION_LABEL,
    CHANNEL_POLICY_FAMILY: CHANNEL_POLICY_LABEL,
    EXCEL_VIEWPORT_FAMILY: EXCEL_VIEWPORT_LABEL,
    MARKER_POSITION_FAMILY: MARKER_POSITION_LABEL,
    REPORT_SCOPE_FAMILY: REPORT_SCOPE_LABEL,
}

CANONICAL_MANIFEST_LISTERS = {
    INVENTORY_EXCEPTION_FAMILY: list_inventory_exception_manifests,
    CHANNEL_POLICY_FAMILY: list_channel_policy_transfer_manifests,
    EXCEL_VIEWPORT_FAMILY: list_excel_viewport_manifests,
    MARKER_POSITION_FAMILY: list_marker_position_manifests,
    REPORT_SCOPE_FAMILY: list_report_scope_manifests,
}

CANONICAL_BUILDERS = {
    INVENTORY_EXCEPTION_FAMILY: build_inventory_exception_episode,
    CHANNEL_POLICY_FAMILY: build_channel_policy_transfer_episode,
    EXCEL_VIEWPORT_FAMILY: build_excel_viewport_episode,
    MARKER_POSITION_FAMILY: build_marker_position_episode,
    REPORT_SCOPE_FAMILY: build_report_scope_episode,
}


def list_canonical_families() -> list[str]:
    return sorted(CANONICAL_BUILDERS)


def list_manifests(family: str, level: int) -> tuple[TemplateManifest, ...]:
    if family not in CANONICAL_MANIFEST_LISTERS:
        raise KeyError(f"Unknown canonical family: {family}")
    return CANONICAL_MANIFEST_LISTERS[family](level)


__all__ = [
    "CANONICAL_BUILDERS",
    "CANONICAL_FAMILY_LABELS",
    "CANONICAL_MANIFEST_LISTERS",
    "CANONICAL_SEEDS_PER_TEMPLATE",
    "TemplateManifest",
    "list_canonical_families",
    "list_manifests",
]
