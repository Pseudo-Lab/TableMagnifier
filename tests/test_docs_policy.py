from pathlib import Path

from table_env_bench.data.generators import list_families
from table_env_bench.server.app import PREFERRED_GENERATOR_FAMILY


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs"


def _read_doc(name: str) -> str:
    return (DOCS / name).read_text(encoding="utf-8")


def test_task_family_docs_match_current_release_posture() -> None:
    doc = _read_doc("task_families.md")

    assert PREFERRED_GENERATOR_FAMILY == "k_vis_table_arc"
    assert list_families() == ["k_vis_table_arc"]
    assert "## Active Family" in doc
    assert "- `k_vis_table_arc`" in doc
    assert "`family_status == preferred`" in doc
    assert "`is_preferred == true`" in doc
    assert "frozen `public_*` instance pack을 포함하지 않는다" in doc
    assert "deprecated generator family는 canonical registry에서 제거했다" in doc


def test_navigation_contract_is_documented_as_authoring_policy() -> None:
    rulebook = _read_doc("episode_rulebook.md")
    checklist = _read_doc("episode_validation_checklist.md")
    cue_inventory = _read_doc("visual_cue_inventory.md")
    operators = _read_doc("operator_taxonomy.md")

    assert "### 3.9 `viewport_pan_to_target_column`" in rulebook
    assert "`required_navigation.required_viewport_states`" in rulebook
    assert "`required_navigation.forbidden_shortcuts`" in rulebook

    assert "## 12. navigation contract check" in checklist
    assert "`required_navigation.required_sheet_ids`" in checklist
    assert "`viewbox_intersects_target`" in checklist
    assert "`target_center_in_viewbox`" in checklist
    assert "## 13B. viewport-navigation probe 기준" in checklist

    assert "### 2.9 viewport window / pan-to-target position" in cue_inventory
    assert "`required_viewport_states`" in cue_inventory
    assert "`viewbox_intersects_target`" in cue_inventory
    assert "`target_center_in_viewbox`" in cue_inventory

    assert "### 2.9 `match_column_offset`" in operators
    assert "`rule_transfer`" in operators
    assert "`match_column_offset`" in operators
