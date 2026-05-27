from __future__ import annotations

from typing import Any

from table_agi_bench.core.types import Cell, TaskSpec

FORBIDDEN_VISIBLE_TERMS = {
    "answer",
    "gold",
    "target answer",
    "distractor",
    "rationale",
    "debug",
    "generation",
    "정답",
    "오답",
    "후보",
    "검산",
    "숨김",
    "단서 적용 후보",
}

_TIER_RANGES = {
    "A": (5, 12),
    "B": (13, 25),
    "C": (26, 60),
    "D": (61, 10_000),
}

_MIN_TRAPS_BY_LEVEL = {1: 2, 2: 3, 3: 4}


def visible_text(table: list[list[Cell]]) -> str:
    return " ".join(cell.text for row in table for cell in row)


def evidence_cell(
    row: int,
    col: int,
    role: str,
    sheet_id: str = "main",
    page_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"sheet_id": sheet_id, "row": row, "col": col, "role": role}
    if page_id is not None:
        payload["page_id"] = page_id
    return payload


def action_contract(
    nav_tier: str,
    estimated_action_floor: int,
    required_evidence_cells: list[dict[str, Any]],
    *,
    action_model: str = "mixed",
    required_page_sequence: list[str] | None = None,
    estimated_human_mean_actions: float | None = None,
    estimated_human_second_best_actions: float | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "nav_tier": nav_tier,
        "estimated_action_floor": estimated_action_floor,
        "required_evidence_cells": required_evidence_cells,
        "action_model": action_model,
    }
    if required_page_sequence:
        payload["required_page_sequence"] = required_page_sequence
    if estimated_human_mean_actions is not None:
        payload["estimated_human_mean_actions"] = estimated_human_mean_actions
    if estimated_human_second_best_actions is not None:
        payload["estimated_human_second_best_actions"] = estimated_human_second_best_actions
    return payload


def v3_metadata(
    *,
    template_id: str,
    skill_ids: list[str],
    level: int,
    nav_tier: str,
    answer_form: str,
    visual_extensions_used: list[str],
    action_contract: dict[str, Any],
    gold_evidence_path: list[dict[str, Any]],
    shortcut_traps: list[str],
    distractor_derivations: list[dict[str, Any]],
    primary_failure_modes: list[str],
    required_visible_evidence: list[str],
    hidden_program_shape: str,
    diagnostics_extra: dict[str, Any] | None = None,
    assumptions: list[str] | None = None,
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {
        "reasoning_level": level,
        "nav_tier": nav_tier,
        "primary_failure_modes": primary_failure_modes,
    }
    if diagnostics_extra:
        diagnostics.update(diagnostics_extra)

    metadata: dict[str, Any] = {
        "template_id": template_id,
        "family_id": "k_vis_table_arc",
        "skill_ids": skill_ids,
        "visual_extensions_used": visual_extensions_used,
        "action_contract": action_contract,
        "gold_evidence_path": gold_evidence_path,
        "shortcut_traps": shortcut_traps,
        "distractor_derivations": distractor_derivations,
        "diagnostics": diagnostics,
        "required_visible_evidence": required_visible_evidence,
        "hidden_program_shape": hidden_program_shape,
        "minimum_trap_count": _MIN_TRAPS_BY_LEVEL[level],
        "skill_plan": {
            "selected_skill_ids": skill_ids,
            "primary_template_id": template_id,
            "level": level,
            "nav_tier": nav_tier,
            "answer_form": answer_form,
            "assumptions": assumptions or [],
        },
    }
    if extras:
        metadata.update(extras)
    return metadata


def finalize_v3_task(task: TaskSpec) -> TaskSpec:
    validation = validate_v3_task(task)
    task.private_metadata["leakage_checks"] = {
        "visible_forbidden_terms_found": validation["checks"]["visible_forbidden_terms_found"]
    }
    task.private_metadata["validation"] = validation
    return task


def validate_v3_task(task: TaskSpec) -> dict[str, Any]:
    metadata = task.private_metadata
    action = metadata.get("action_contract", {})
    distractors = metadata.get("distractor_derivations", [])
    visible = visible_text(task.table)
    visible_forbidden = [term for term in FORBIDDEN_VISIBLE_TERMS if term.lower() in visible.lower()]
    nav_tier = action.get("nav_tier")
    floor = action.get("estimated_action_floor")
    tier_range = _TIER_RANGES.get(nav_tier)

    checks: dict[str, Any] = {
        "metadata_extra_shape": all(
            key in metadata
            for key in [
                "skill_ids",
                "visual_extensions_used",
                "action_contract",
                "gold_evidence_path",
                "shortcut_traps",
                "distractor_derivations",
                "diagnostics",
            ]
        ),
        "gold_unique": str(task.answer) not in {str(item.get("value")) for item in distractors},
        "distractors_unique": len({str(item.get("value")) for item in distractors}) == len(distractors),
        "required_evidence_visible": all(needle in visible for needle in metadata.get("required_visible_evidence", [])),
        "trap_coverage": len(metadata.get("shortcut_traps", [])) >= metadata.get("minimum_trap_count", 0),
        "visible_forbidden_terms_found": visible_forbidden,
        "action_contract_present": all(
            key in action for key in ["nav_tier", "estimated_action_floor", "required_evidence_cells", "action_model"]
        ),
        "action_floor_matches_nav_tier": bool(
            isinstance(floor, int) and tier_range and tier_range[0] <= floor <= tier_range[1]
        ),
        "evidence_cells_present": len(action.get("required_evidence_cells", [])) > 0,
        "diagnostics_present": all(
            key in metadata.get("diagnostics", {}) for key in ["reasoning_level", "nav_tier", "primary_failure_modes"]
        ),
    }
    status = "pass" if all(value is True or value == [] for value in checks.values()) else "fail"
    return {"status": status, "checks": checks}


def unique_distractors(answer: Any, candidates: list[tuple[str, Any]]) -> list[dict[str, Any]]:
    used = {str(answer)}
    distractors: list[dict[str, Any]] = []
    for trap_id, raw_value in candidates:
        value = raw_value
        if isinstance(value, int):
            while str(value) in used:
                value += len(used) + 1
        else:
            suffix = 1
            base = str(value)
            while str(value) in used:
                value = f"{base}-{suffix}"
                suffix += 1
        used.add(str(value))
        distractors.append({"trap_id": trap_id, "value": value, "display_value": str(value)})
    return distractors
