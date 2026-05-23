"""Audit generated Visual TableQA surfaces for the normalized sample viewer."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from table_env_bench.data.generators import list_families, list_levels, list_templates
from table_env_bench.env.environment import TableEnv

FORBIDDEN_VISIBLE_STRINGS = (
    "검산 후보",
    "표 단서 적용 후보",
    "문서 단서 적용 후보",
    "단위 확인 후보",
    "candidate",
    "distractor",
    "rationale",
    "debug",
    "generation",
    "source_hint",
    "answer_type",
    "candidate_type",
    "distractor_type",
    "rationale_type",
)

RULE_INDUCTION_TEMPLATES = {"symbol_rule_induction", "color_condition_rule_induction"}
DOCUMENT_TABLE_TEMPLATES = {"abbrev_doc_reference", "legend_color_exception_scope"}
WIDE_TABLE_TEMPLATES = {"wide_table_navigation", "wide_table_viewport_trace", "merged_header_pan_scope"}
STRUCTURED_TABLE_TEMPLATES = {"merged_header_scope", "zoom_micro_marker_exception"}


@dataclass(frozen=True)
class SurfaceAudit:
    family: str
    level: int
    template_id: str
    sheet_id: str
    page_id: str
    adapter: str
    table_count: int
    document_count: int
    choice_count: int
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    forbidden: tuple[str, ...]


def _adapter_name(template_id: str) -> str:
    if template_id in RULE_INDUCTION_TEMPLATES:
        return "rule_induction_adapter"
    if template_id in DOCUMENT_TABLE_TEMPLATES:
        return "document_table_adapter"
    if template_id in WIDE_TABLE_TEMPLATES:
        return "wide_table_adapter"
    if template_id in STRUCTURED_TABLE_TEMPLATES:
        return "structured_table_adapter"
    return "generic_scene_adapter"


def _is_choice(element: dict[str, Any]) -> bool:
    element_id = str(element.get("element_id") or "")
    title = str(element.get("title") or "")
    return element_id.startswith("answer-") or title.startswith("선택지 ")


def _visible_text(element: dict[str, Any]) -> str:
    parts = [str(element.get("title") or "")]
    lines = element.get("lines")
    if isinstance(lines, list):
        parts.extend(str(line) for line in lines)
    cells = element.get("cells")
    if isinstance(cells, list):
        for cell in cells:
            if isinstance(cell, dict):
                parts.append(str(cell.get("text") or ""))
    return " ".join(parts)


def _contains_forbidden(text: str) -> tuple[str, ...]:
    lower = text.lower()
    return tuple(token for token in FORBIDDEN_VISIBLE_STRINGS if token.lower() in lower)


def _question_requires_completed(question: str) -> bool:
    needles = ("완성 행", "완성 예시", "규칙을 유도", "유도했을 때", "예시의", "completed rows", "example rows", "derive the rule", "rule induction")
    lowered = question.lower()
    return any(needle.lower() in lowered for needle in needles)


def _has_completed_table(elements: list[dict[str, Any]]) -> bool:
    for element in elements:
        if element.get("type") != "table":
            continue
        key = f"{element.get('element_id', '')} {element.get('title', '')}".lower()
        if any(token in key for token in ("완성", "예시", "example", "examples", "completed", "offset", "marker")):
            return True
    return False


def _surface_audit(env: TableEnv, family: str, level: int, template_id: str) -> SurfaceAudit:
    observation = env._observation()  # noqa: SLF001 - audit script intentionally inspects the current rendered surface.
    info = env._info()  # noqa: SLF001
    page = observation.get("viewport_scene", {}).get("page", {})
    raw_elements = page.get("elements", [])
    elements = [element for element in raw_elements if isinstance(element, dict)]
    tables = [element for element in elements if element.get("type") == "table"]
    documents = [
        element
        for element in elements
        if element.get("type") == "text_block" and not _is_choice(element) and element.get("element_id") not in {"query-target", "query-guidance"}
    ]
    choices = [element for element in elements if _is_choice(element)]
    warnings: list[str] = []
    errors: list[str] = []
    forbidden: list[str] = []

    if not str(observation.get("question") or "").strip():
        errors.append("question_missing")
    if not tables and not documents:
        errors.append("evidence_missing")
    for table in tables:
        if not table.get("n_cols") or not table.get("n_rows"):
            errors.append(f"table_empty:{table.get('element_id')}")
    if choices and any(not str(choice.get("title") or "").strip() for choice in choices):
        errors.append("choice_id_missing")
    if not choices:
        warnings.append("choices_missing_on_surface")
    if _question_requires_completed(str(observation.get("question") or "")) and not _has_completed_table(elements):
        errors.append("completed_rows_missing_on_surface")

    for element in elements:
        forbidden.extend(_contains_forbidden(_visible_text(element)))

    return SurfaceAudit(
        family=family,
        level=level,
        template_id=template_id,
        sheet_id=str(info.get("active_sheet_id") or ""),
        page_id=str(info.get("current_page_id") or ""),
        adapter=_adapter_name(template_id),
        table_count=len(tables),
        document_count=len(documents),
        choice_count=len(choices),
        warnings=tuple(sorted(set(warnings))),
        errors=tuple(sorted(set(errors))),
        forbidden=tuple(sorted(set(forbidden))),
    )


def _all_surfaces(family: str, level: int, template_id: str) -> list[SurfaceAudit]:
    env = TableEnv(family=family, level=level, seed=0, template_id=template_id, mode="human")
    _, info = env.reset()
    audits: list[SurfaceAudit] = []
    for sheet_index in range(len(info["sheet_tabs"])):
        if env._state.sheet_index != sheet_index:  # noqa: SLF001
            env.step({"type": "select_sheet", "sheet": sheet_index})
        page_count = len(env._current_sheet().pages)  # noqa: SLF001
        for page_index in range(page_count):
            while env._state.page_index < page_index:  # noqa: SLF001
                env.step({"type": "next_page"})
            audits.append(_surface_audit(env, family, level, template_id))
    return audits


def _aggregate_sample_audit(family: str, level: int, template_id: str) -> SurfaceAudit:
    env = TableEnv(family=family, level=level, seed=0, template_id=template_id, mode="human")
    observation, info = env.reset()
    surfaces = observation.get("sample_surfaces", [])
    elements: list[dict[str, Any]] = []
    if isinstance(surfaces, list):
        for surface in surfaces:
            if isinstance(surface, dict) and isinstance(surface.get("elements"), list):
                elements.extend(element for element in surface["elements"] if isinstance(element, dict))

    tables = [element for element in elements if element.get("type") == "table"]
    documents = [
        element
        for element in elements
        if element.get("type") == "text_block" and not _is_choice(element) and element.get("element_id") not in {"query-target", "query-guidance"}
    ]
    choices = [element for element in elements if _is_choice(element)]
    warnings: list[str] = []
    errors: list[str] = []
    forbidden: list[str] = []

    if not str(observation.get("question") or "").strip():
        errors.append("question_missing")
    if not tables and not documents:
        errors.append("evidence_missing")
    for table in tables:
        if not table.get("n_cols") or not table.get("n_rows"):
            errors.append(f"table_empty:{table.get('element_id')}")
    if not choices:
        warnings.append("choices_missing")
    if _question_requires_completed(str(observation.get("question") or "")) and not _has_completed_table(elements):
        errors.append("completed_rows_missing")
    for element in elements:
        forbidden.extend(_contains_forbidden(_visible_text(element)))

    return SurfaceAudit(
        family=family,
        level=level,
        template_id=template_id,
        sheet_id="all",
        page_id=f"{len(surfaces) if isinstance(surfaces, list) else 0}_surfaces",
        adapter=_adapter_name(template_id),
        table_count=len(tables),
        document_count=len(documents),
        choice_count=len(choices),
        warnings=tuple(sorted(set(warnings))),
        errors=tuple(sorted(set(errors))),
        forbidden=tuple(sorted(set(forbidden))),
    )


def main() -> int:
    audits: list[SurfaceAudit] = []
    template_counts: Counter[str] = Counter()
    for family in list_families():
        for level in list_levels(family):
            for template_id in list_templates(family, level):
                template_counts[template_id] += 1
                audits.append(_aggregate_sample_audit(family, level, template_id))

    adapter_by_template: dict[str, str] = {}
    status_by_template: dict[str, Counter[str]] = defaultdict(Counter)
    for audit in audits:
        adapter_by_template[audit.template_id] = audit.adapter
        if audit.forbidden:
            status_by_template[audit.template_id]["forbidden"] += 1
        elif audit.errors:
            status_by_template[audit.template_id]["validation_error"] += 1
        elif audit.warnings:
            status_by_template[audit.template_id]["warning"] += 1
        else:
            status_by_template[audit.template_id]["ok"] += 1

    total_errors = sum(1 for audit in audits if audit.errors)
    total_warnings = sum(1 for audit in audits if audit.warnings)
    total_forbidden = sum(1 for audit in audits if audit.forbidden)

    print("Visual TableQA sample viewer audit")
    print(f"total samples checked: {len(audits)}")
    print(f"templates discovered: {len(template_counts)}")
    print(f"samples normalized without issues: {sum(1 for audit in audits if not audit.errors and not audit.warnings and not audit.forbidden)}")
    print(f"samples with validation warnings: {total_warnings}")
    print(f"samples with validation errors: {total_errors}")
    print(f"samples with forbidden visible metadata: {total_forbidden}")
    print()
    print("Template handling:")
    for template_id in sorted(template_counts):
        statuses = status_by_template[template_id]
        status = ", ".join(f"{key}={value}" for key, value in sorted(statuses.items())) or "none"
        print(f"- {template_id}: {adapter_by_template[template_id]} ({status})")

    if total_forbidden:
        print()
        print("Forbidden metadata leaks:")
        for audit in audits:
            if audit.forbidden:
                print(f"- {audit.family} L{audit.level} {audit.template_id} {audit.sheet_id}:{audit.page_id}: {', '.join(audit.forbidden)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
