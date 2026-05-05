"""예외를 통해 규칙을 구분하는 canonical family."""

from __future__ import annotations

from typing import Any

from table_env_bench.data.families.shared import (
    TemplateManifest,
    cell,
    episode,
    note,
    page,
    query_header_blocks,
    rect,
    region,
    resolve_template_seed,
    rotate,
    sheet,
    table_from_cells,
)

FAMILY = "inventory_exception_disambiguation"
FAMILY_LABEL = "재고 예외 판정"
_FOLLOWUP_TABLE_Y = 640
_QUERY_CHOICE_TABLE_Y = 628
_TABLE_HEADING_HEIGHT = 44
_CHOICE_ROW_GAP = 20

_LEVEL_REASONING_STEPS = {1: (3, 4), 2: (3, 4), 3: (4, 5)}
_LEVEL_RATIONALES = {
    1: "초안과 예외 확인표를 비교해 잘못된 기준을 버리는 3-4단계 문제다.",
    2: "예외 확인표와 적용 메모를 함께 읽어 실제 범위를 고정해야 하는 3-4단계 문제다.",
    3: "예외 확인표와 메모를 반영한 뒤 선택 결과까지 맞춰야 하는 4-5단계 문제다.",
}


def _manifest(level: int) -> TemplateManifest:
    required_page_refs = ("examples:examples-p1", "exception:exception-p1", "query:query-p1")
    required_actions = ("must_switch_sheet", "must_visit_exception")
    required_evidence: tuple[dict[str, Any], ...] = (
        {"kind": "page", "sheet_id": "examples", "page_id": "examples-p1"},
        {"kind": "page", "sheet_id": "exception", "page_id": "exception-p1"},
        {"kind": "page", "sheet_id": "query", "page_id": "query-p1"},
    )
    cue_tags = ("pattern_marker", "icon_anchor")
    operator_tags = ("verify_statement", "disambiguate_by_exception")
    required_visual_cues = cue_tags
    if level >= 2:
        required_page_refs = (*required_page_refs, "exception:exception-p2")
        required_actions = (*required_actions, "must_open_note")
        required_evidence = (
            *required_evidence,
            {"kind": "page", "sheet_id": "exception", "page_id": "exception-p2"},
            {"kind": "note", "sheet_id": "exception", "page_id": "exception-p2", "note_id": "scope-note"},
        )
        cue_tags = (*cue_tags, "row_group_band", "note_scope")
        operator_tags = (*operator_tags, "scope_resolution")
        required_visual_cues = cue_tags
    shortcut_probes = ("single_page", "text_scrape_only", "no_exception")
    if level >= 2:
        shortcut_probes = (*shortcut_probes, "no_exception_note")
    return TemplateManifest(
        family=FAMILY,
        level=level,
        template_id="pattern_vs_icon_statement",
        template_label="사선 표시와 삼각 표식 판정",
        latent_rule="초안만 보면 사선 표시와 삼각 표식이 함께 맞아 보이지만, 예외 확인표가 실제 규칙이 삼각 표식임을 고정한다.",
        operator_tags=operator_tags,
        cue_tags=cue_tags,
        answer_form="statement_choice",
        primary_operator="verify_statement",
        support_operator="disambiguate_by_exception",
        required_visual_cues=required_visual_cues,
        required_surfaces=("example_table_panel", "exception_card", "query_table_panel", "answer_choice_panel"),
        capability_axes=("visual_grounding", "disambiguation", "scope_resolution"),
        task_archetype="exception_audit",
        scenario_context="초안과 예외 확인표를 비교해 실제 적용 기준과 제외 범위를 확정하는 과업이다.",
        benchmark_track="canonical_real_tableqa",
        reasoning_archetype="disambiguate_apply",
        abstraction_tier="abstract_worksheet",
        support_surface_policy="optional",
        qa_dependency="hybrid_induction_tableqa",
        generalization_group=f"{FAMILY}:pattern_vs_icon_statement:l{level}",
        required_sheet_ids=("examples", "exception", "query"),
        required_page_refs=required_page_refs,
        allowed_cue_variants=("pattern_marker", "icon_anchor", "row_group_band", "note_scope"),
        distractor_policy="초안만 보면 그럴듯한 사선 표시 기준과 예외까지 봐야 맞는 삼각 표식 기준을 함께 남기고, 범위를 넓게 잡는 오답도 함께 둔다.",
        level_rationale=_LEVEL_RATIONALES[level],
        text_only_failure_modes=(
            "사선 표시와 삼각 표식이 같은 행에 함께 보이는 예시만 읽으면 잘못된 기준을 버릴 근거가 없다.",
            "Level 2 이상에서는 메모가 고정하는 적용 묶음을 무시하면 다른 묶음의 행을 정답으로 끌어온다.",
        ),
        distractor_failure_modes=(
            "예외를 무시하고 사선 표시 행을 그대로 정답으로 고르는 오답",
            "메모가 고정하는 적용 묶음을 무시하고 삼각 표식 행 범위를 너무 넓게 잡는 오답",
        ),
        level_knobs={"level": level, "template": "pattern_vs_icon_statement"},
        max_actions=8 + level,
        required_actions=required_actions,
        required_evidence=required_evidence,
        expected_min_steps=_LEVEL_REASONING_STEPS[level][0],
        expected_reasoning_steps=_LEVEL_REASONING_STEPS[level],
        shortcut_probes=shortcut_probes,
    )


TEMPLATES_BY_LEVEL: dict[int, tuple[TemplateManifest, ...]] = {level: (_manifest(level),) for level in (1, 2, 3)}


def list_manifests(level: int) -> tuple[TemplateManifest, ...]:
    return TEMPLATES_BY_LEVEL[level]


def _triangle(*, anchor: str = "top_right", color: str = "#0f766e") -> dict[str, Any]:
    return {"icon": {"kind": "triangle", "anchor": anchor, "color": color}}


def _stripe(*, color: str = "#f97316") -> dict[str, Any]:
    return {"pattern": {"kind": "diagonal_stripe", "color": color, "opacity": 0.82}}


def _frame(*, color: str = "#2563eb") -> dict[str, Any]:
    return {"frame": {"kind": "selection", "color": color}}


def _merge(*items: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for item in items:
        merged.update(item)
    return merged


def _사선표시_icon_table(
    *,
    element_id: str,
    title: str,
    box,
    rows: list[tuple[str, bool, bool, bool]],
    subtitle: str,
    show_result: bool = True,
):
    headers = ("품목", "사선 표시", "삼각 표식", "결과") if show_result else ("품목", "사선 표시", "삼각 표식")
    cells = [cell(0, index, header, style="header") for index, header in enumerate(headers)]
    for row_index, (label, has_사선표시, has_icon, selected) in enumerate(rows, start=1):
        cells.append(cell(row_index, 0, label, style="row_label", align="left"))
        사선표시_metadata = _stripe() if has_사선표시 else {}
        icon_metadata = _triangle() if has_icon else {}
        cells.append(cell(row_index, 1, "", metadata=사선표시_metadata))
        cells.append(cell(row_index, 2, "", metadata=icon_metadata))
        if show_result:
            result_metadata = _frame() if selected else {}
            cells.append(cell(row_index, 3, "", metadata=result_metadata))
    column_weights = (0.34, 0.22, 0.22, 0.22) if show_result else (0.42, 0.29, 0.29)
    return table_from_cells(
        element_id,
        title,
        box,
        n_rows=1 + len(rows),
        n_cols=len(headers),
        cells=cells,
        column_weights=column_weights,
        row_heights=(42,) + tuple(54 for _ in rows),
        subtitle=subtitle,
    )


def _grouped_사선표시_icon_table(
    *,
    element_id: str,
    title: str,
    box,
    groups: list[tuple[str, list[tuple[str, bool, bool, bool]]]],
    subtitle: str,
    show_result: bool = True,
):
    headers = ("구분", "품목", "사선 표시", "삼각 표식", "결과") if show_result else ("구분", "품목", "사선 표시", "삼각 표식")
    cells = [cell(0, index, header, style="header") for index, header in enumerate(headers)]
    row_heights = [42]
    row_index = 1
    for group_label, rows in groups:
        cells.append(cell(row_index, 0, group_label, style="total_label", align="left"))
        cells.append(cell(row_index, 1, "", style="muted"))
        cells.append(cell(row_index, 2, "", style="muted"))
        cells.append(cell(row_index, 3, "", style="muted"))
        if show_result:
            cells.append(cell(row_index, 4, "", style="muted"))
        row_heights.append(38)
        row_index += 1
        for label, has_사선표시, has_icon, selected in rows:
            cells.append(cell(row_index, 0, "", style="muted"))
            cells.append(cell(row_index, 1, f"  {label}", style="row_label", align="left"))
            cells.append(cell(row_index, 2, "", metadata=_stripe() if has_사선표시 else {}))
            cells.append(cell(row_index, 3, "", metadata=_triangle() if has_icon else {}))
            if show_result:
                cells.append(cell(row_index, 4, "", metadata=_frame() if selected else {}))
            row_heights.append(44)
            row_index += 1
    column_weights = (0.22, 0.28, 0.17, 0.17, 0.16) if show_result else (0.24, 0.36, 0.20, 0.20)
    return table_from_cells(
        element_id,
        title,
        box,
        n_rows=row_index,
        n_cols=len(headers),
        cells=cells,
        column_weights=column_weights,
        row_heights=tuple(row_heights),
        subtitle=subtitle,
    )


def _choice_preview_tables(
    *,
    prefix: str,
    row_labels: tuple[str, ...],
    choice_rows: list[tuple[str, tuple[str, ...], str]],
    y: float,
    subtitle: str | None = None,
    row_height: int = 15,
) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    elements: list[Any] = []
    regions: list[Any] = []
    x_positions = (84.0, 624.0)
    widths = 514.0
    header_height = 20
    height = header_height + (len(row_labels) * row_height)
    row_pitch = height + _TABLE_HEADING_HEIGHT + _CHOICE_ROW_GAP
    for index, (choice_id, selected_rows, label) in enumerate(choice_rows):
        row_slot, col_slot = divmod(index, 2)
        box = rect(x_positions[col_slot], y + (row_pitch * row_slot), widths, height)
        cells = [
            cell(0, 0, "품목", style="header"),
            cell(0, 1, "선택", style="header"),
        ]
        for data_row, row_label in enumerate(row_labels, start=1):
            cells.append(cell(data_row, 0, row_label, style="row_label", align="left"))
            cells.append(cell(data_row, 1, "", metadata=_frame() if row_label in selected_rows else {}))
        elements.append(
            table_from_cells(
                f"{prefix}-{choice_id.lower()}",
                f"선택지 {choice_id}",
                box,
                n_rows=1 + len(row_labels),
                n_cols=2,
                cells=cells,
                column_weights=(0.68, 0.32),
                row_heights=(header_height,) + tuple(row_height for _ in row_labels),
                subtitle=subtitle or label,
            )
        )
        regions.append(
            region(
                f"{prefix}-{choice_id.lower()}",
                "answer_choice",
                f"선택지 {choice_id}",
                box,
                metadata={"choice_id": choice_id, "answer_form": "statement_choice"},
            )
        )
    return tuple(elements), tuple(regions)


def _query_header(*, target: tuple[str, ...], guidance: tuple[str, ...]) -> tuple[tuple[Any, Any], float]:
    return query_header_blocks(
        target_title="확인 대상",
        target_lines=target,
        guidance_title="판정 메모",
        guidance_lines=guidance,
        mode="compact",
    )


def build_episode(level: int, seed: int, *, template_id: str | None = None):
    manifest, seed_slot = resolve_template_seed(TEMPLATES_BY_LEVEL[level], seed, template_id=template_id)
    if level == 1:
        return _build_level_1(manifest, seed_slot)
    if level == 2:
        return _build_level_2(manifest, seed_slot)
    return _build_level_3(manifest, seed_slot)


def _build_level_1(manifest: TemplateManifest, seed_slot: int):
    row_names = rotate(("A창고", "B창고", "C창고", "D창고"), seed_slot)
    examples = [
        _사선표시_icon_table(
            element_id="counter-l1-example-1",
            title="초기 판정안 1",
            box=rect(84, 236, 512, 336),
            rows=[
                (row_names[0], True, True, True),
                (row_names[1], False, False, False),
                (row_names[2], True, True, True),
                (row_names[3], False, False, False),
            ],
            subtitle="초기 표만 보면 사선 표시 행과 삼각 표식 행이 함께 맞아 보인다",
        ),
        _사선표시_icon_table(
            element_id="counter-l1-example-2",
            title="초기 판정안 2",
            box=rect(646, 236, 512, 336),
            rows=[
                (row_names[0], False, False, False),
                (row_names[1], True, True, True),
                (row_names[2], False, False, False),
                (row_names[3], True, True, True),
            ],
            subtitle="초기 자료만으로는 사선 표시 기준도 계속 살아 있다",
        ),
    ]
    exception_table = _사선표시_icon_table(
        element_id="counter-l1-exception",
        title="예외 확인 자료",
            box=rect(84, 224, 720, 360),
        rows=[
            (row_names[0], True, False, False),
            (row_names[1], False, True, True),
            (row_names[2], True, True, True),
            (row_names[3], False, False, False),
        ],
        subtitle="예외 확인 자료에서 사선 표시 행과 삼각 표식 행이 갈라진다",
    )
    query_blocks, _ = _query_header(
        target=("현재 판정 표에서 실제 선택 행 묶음을 확정합니다.",),
        guidance=("예외 확인 자료를 반영하면 사선 표시가 아니라 삼각 표식 행이 실제 기준입니다.",),
    )
    query_table = _사선표시_icon_table(
        element_id="counter-l1-query",
        title="",
        box=rect(84, 286, 720, 278),
        rows=[
            (row_names[0], True, False, False),
            (row_names[1], False, True, False),
            (row_names[2], False, False, False),
            (row_names[3], True, True, False),
        ],
        subtitle="",
        show_result=False,
    )
    choices, choice_regions = _choice_preview_tables(
        prefix="counter-l1-choice",
        row_labels=tuple(row_names),
        choice_rows=[
            ("A", (row_names[0], row_names[3]), "사선 표시 행"),
            ("B", (row_names[1], row_names[3]), "삼각 표식 행"),
            ("C", (row_names[3],), "겹치는 행만 선택"),
            ("D", (row_names[0], row_names[1], row_names[3]), "표식이 하나라도 있는 행"),
        ],
        y=_QUERY_CHOICE_TABLE_Y,
    )
    return episode(
        manifest=manifest,
        family_display_name=FAMILY_LABEL,
        question="예외 확인 자료까지 반영했을 때 현재 표에 대한 올바른 판정 설명은 어느 선택지인가?",
        workbook_title="예외 확인 검토표",
        sheets=[
            sheet(
                "examples",
                "예시",
                [
                    page(
                        "examples-p1",
                        "예시 시트",
                        elements=[
                            *examples,
                            _사선표시_icon_table(
                                element_id="counter-l1-example-hint",
                                title="판정 메모",
                                box=rect(84, _FOLLOWUP_TABLE_Y, 1074, 108),
                                rows=[
                                    ("줄무늬", True, False, False),
                                    ("삼각 표식", False, True, False),
                                ],
                                subtitle="어느 표식이 실제 결과를 결정하는지는 초기 자료만으로 고정되지 않음",
                                show_result=False,
                            ),
                        ],
                    )
                ],
            ),
            sheet(
                "exception",
                "반례",
                [
                    page(
                        "exception-p1",
                        "예외 확인 시트",
                        elements=[exception_table],
                    )
                ],
            ),
            sheet(
                "query",
                "선택",
                [
                    page(
                        "query-p1",
                        "선택 시트",
                        elements=[*query_blocks, query_table, *choices],
                        regions=choice_regions,
                    )
                ],
            ),
        ],
        answer="B",
        seed_slot=seed_slot,
        metadata_extra={"relevant_region_ids": tuple(region_spec.public_id for region_spec in choice_regions)},
    )


def _build_level_2(manifest: TemplateManifest, seed_slot: int):
    row_names = rotate(("가람", "나래", "다온", "라온"), seed_slot)
    groups = ("분석 묶음", "운영 묶음")
    active_group = groups[seed_slot % 2]
    inactive_group = groups[1] if active_group == groups[0] else groups[0]
    examples_groups = [
        (groups[0], [(row_names[0], True, True, True), (row_names[1], False, False, False)]),
        (groups[1], [(row_names[2], True, True, True), (row_names[3], False, False, False)]),
    ]
    flipped_examples_groups = [
        (groups[0], [(row_names[0], False, False, False), (row_names[1], True, True, True)]),
        (groups[1], [(row_names[2], False, False, False), (row_names[3], True, True, True)]),
    ]
    exception_groups = [
        (groups[0], [(row_names[0], True, False, False), (row_names[1], False, True, True)]),
        (groups[1], [(row_names[2], True, True, True), (row_names[3], False, False, False)]),
    ]
    query_groups = [
        (groups[0], [(row_names[0], True, True, False), (row_names[1], False, True, False)]),
        (groups[1], [(row_names[2], False, True, False), (row_names[3], True, False, False)]),
    ]
    correct_rows = (row_names[1],) if active_group == groups[0] else (row_names[2],)
    stripe_rows = (row_names[0],) if active_group == groups[0] else (row_names[3],)
    all_icon_rows = (row_names[0], row_names[1], row_names[2])
    choices, choice_regions = _choice_preview_tables(
        prefix="counter-l2-choice",
        row_labels=tuple(row_names),
        choice_rows=[
            ("A", stripe_rows, "적용 묶음의 사선 표시 행"),
            ("B", correct_rows, "적용 묶음의 삼각 표식 행"),
            ("C", all_icon_rows, "적용 묶음을 무시한 삼각 표식 행"),
            ("D", (row_names[0], row_names[3]), "초안만 따른 행"),
        ],
        y=_QUERY_CHOICE_TABLE_Y,
        subtitle=active_group,
    )
    query_blocks, _ = _query_header(
        target=(f"현재 판정 묶음: {active_group}",),
        guidance=("예외 확인 자료는 삼각 표식 기준을 고정하고 메모는 적용 묶음만 남깁니다.",),
    )
    scope_note = note("scope-note", "적용 범위", f"현재 판정 표에서는 {active_group} 아래 행만 선택 대상으로 본다.")
    note_block = _grouped_사선표시_icon_table(
        element_id="counter-l2-note",
        title="예외 확인 범위 메모",
        box=rect(124, 212, 1032, 240),
        groups=[
            (active_group, [(correct_rows[0], False, True, True)]),
            (inactive_group, [((row_names[2] if active_group == groups[0] else row_names[1]), False, True, False)]),
        ],
        subtitle="예외 확인 메모가 적용 묶음 범위를 고정한다",
    )
    return episode(
        manifest=manifest,
        family_display_name=FAMILY_LABEL,
        question="예외 확인 자료와 메모를 모두 반영했을 때 현재 표에 대한 올바른 판정 설명은 어느 선택지인가?",
        workbook_title="예외 확인 검토표",
        sheets=[
            sheet(
                "examples",
                "예시",
                [
                    page(
                        "examples-p1",
                        "예시 시트",
                        elements=[
                            _grouped_사선표시_icon_table(
                                element_id="counter-l2-example-1",
                                title="초기 판정안 1",
                                box=rect(84, 218, 512, 356),
                                groups=examples_groups,
                                subtitle="초기 자료에서는 사선 표시와 삼각 표식이 같은 묶음 안에서 함께 움직인다",
                            ),
                            _grouped_사선표시_icon_table(
                                element_id="counter-l2-example-2",
                                title="초기 판정안 2",
                                box=rect(646, 218, 512, 356),
                                groups=flipped_examples_groups,
                                subtitle="초기 자료만으로는 잘못된 기준을 버릴 수 없다",
                            ),
                        ],
                    )
                ],
            ),
            sheet(
                "exception",
                "반례",
                [
                    page(
                        "exception-p1",
                        "예외 확인 표",
                        elements=[
                            _grouped_사선표시_icon_table(
                                element_id="counter-l2-exception",
                                title="결정적 예외 확인 자료",
                                box=rect(84, 204, 1074, 334),
                                groups=exception_groups,
                                subtitle="예외 확인 표에서 사선 표시와 삼각 표식이 같은 묶음 안에서 갈라진다",
                            )
                        ],
                    ),
                    page(
                        "exception-p2",
                        "적용 범위",
                        elements=[note_block],
                        notes=(scope_note,),
                        regions=(region("counter-l2-note-region", "note_marker", "예외 확인 범위 메모", note_block.rect, linked_note_id="scope-note"),),
                    ),
                ],
            ),
            sheet(
                "query",
                "선택",
                [
                    page(
                        "query-p1",
                        "선택 시트",
                        elements=[
                            *query_blocks,
                            _grouped_사선표시_icon_table(
                                element_id="counter-l2-query",
                                title="",
                                box=rect(84, 286, 720, 278),
                                groups=query_groups,
                                subtitle="",
                                show_result=False,
                            ),
                            *choices,
                        ],
                        regions=choice_regions,
                    )
                ],
            ),
        ],
        answer="B",
        seed_slot=seed_slot,
        metadata_extra={
            "relevant_region_ids": ("counter-l2-note-region", *tuple(region_spec.public_id for region_spec in choice_regions)),
        },
    )


def _build_level_3(manifest: TemplateManifest, seed_slot: int):
    query_table_y = 291
    choice_table_y = 633
    row_names = rotate(("하나", "둘", "셋", "넷"), seed_slot)
    groups = ("분석 묶음", "운영 묶음")
    active_group = groups[0] if seed_slot % 3 else groups[1]
    inactive_group = groups[1] if active_group == groups[0] else groups[0]
    examples_groups = [
        (groups[0], [(row_names[0], True, True, True), (row_names[1], False, False, False)]),
        (groups[1], [(row_names[2], True, True, True), (row_names[3], False, False, False)]),
    ]
    exception_groups = [
        (groups[0], [(row_names[0], True, False, False), (row_names[1], False, True, True)]),
        (groups[1], [(row_names[2], False, True, True), (row_names[3], True, False, False)]),
    ]
    query_groups = [
        (groups[0], [(row_names[0], True, True, False), (row_names[1], False, True, False)]),
        (groups[1], [(row_names[2], False, True, False), (row_names[3], True, False, False)]),
    ]
    correct_rows = (row_names[1],) if active_group == groups[0] else (row_names[2],)
    stripe_rows = (row_names[0],) if active_group == groups[0] else (row_names[3],)
    broad_icon_rows = (row_names[1], row_names[2])
    choices, choice_regions = _choice_preview_tables(
        prefix="counter-l3-choice",
        row_labels=tuple(row_names),
        choice_rows=[
            ("A", stripe_rows, "사선 표시만 따른 선택"),
            ("B", broad_icon_rows, "묶음 범위를 무시한 삼각 표식 선택"),
            ("C", correct_rows, "exception과 note를 모두 반영한 선택"),
            ("D", (row_names[0], row_names[1], row_names[2]), "초안 행을 전부 선택"),
        ],
        y=choice_table_y,
        subtitle="미리보기",
        row_height=14,
    )
    query_blocks, _ = _query_header(
        target=(f"현재 적용 묶음: {active_group}", "현재 표에는 결과 열이 직접 주어지지 않습니다."),
        guidance=("예외 확인 자료가 사선 표시 기준을 버리게 만들고 메모가 적용 묶음을 고정합니다.",),
    )
    scope_note = note("scope-note", "적용 범위", f"현재 판정 표에서는 {active_group} 아래 삼각 표식 행만 실제 선택 대상이다.")
    note_block = _사선표시_icon_table(
        element_id="counter-l3-note",
        title="예외 확인 해석 메모",
        box=rect(162, 208, 964, 218),
        rows=[
            (active_group, False, True, True),
            (inactive_group, False, True, False),
            ("사선 표시 행", True, False, False),
        ],
        subtitle="예외 확인 자료는 삼각 표식 기준을, 메모는 적용 묶음 범위를 확정한다",
    )
    return episode(
        manifest=manifest,
        family_display_name=FAMILY_LABEL,
        question="예외 확인 표와 메모를 모두 반영했을 때 현재 표와 일치하는 선택 미리보기는 어느 것인가?",
        workbook_title="예외 확인 검토표",
        sheets=[
            sheet(
                "examples",
                "예시",
                [
                    page(
                        "examples-p1",
                        "예시 시트",
                        elements=[
                            _grouped_사선표시_icon_table(
                                element_id="counter-l3-example-1",
                                title="초기 판정안 1",
                                box=rect(84, 218, 512, 338),
                                groups=examples_groups,
                                subtitle="초기 자료만 보면 사선 표시 행과 삼각 표식 행이 계속 같이 보인다",
                            ),
                            _grouped_사선표시_icon_table(
                                element_id="counter-l3-example-2",
                                title="초기 판정안 2",
                                box=rect(646, 218, 512, 338),
                                groups=list(reversed(examples_groups)),
                                subtitle="잘못된 기준을 버리려면 예외 확인 자료 확인이 필요하다",
                            ),
                        ],
                    )
                ],
            ),
            sheet(
                "exception",
                "반례",
                [
                    page(
                        "exception-p1",
                        "예외 확인 표",
                        elements=[
                            _grouped_사선표시_icon_table(
                                element_id="counter-l3-exception",
                                title="결정적 예외 확인 자료",
                                box=rect(84, 204, 1074, 334),
                                groups=exception_groups,
                                subtitle="삼각 표식 기준은 유지되지만 적용 묶음은 메모가 고정한다",
                            )
                        ],
                    ),
                    page(
                        "exception-p2",
                        "적용 메모",
                        elements=[note_block],
                        notes=(scope_note,),
                        regions=(region("counter-l3-note-region", "note_marker", "예외 확인 해석 메모", note_block.rect, linked_note_id="scope-note"),),
                    ),
                ],
            ),
            sheet(
                "query",
                "선택",
                [
                    page(
                        "query-p1",
                        "선택 시트",
                        elements=[
                            *query_blocks,
                            _grouped_사선표시_icon_table(
                                element_id="counter-l3-query",
                                title="",
                                box=rect(84, query_table_y, 720, 278),
                                groups=query_groups,
                                subtitle="",
                                show_result=False,
                            ),
                            *choices,
                        ],
                        regions=choice_regions,
                    )
                ],
            ),
        ],
        answer="C",
        seed_slot=seed_slot,
        metadata_extra={
            "relevant_region_ids": ("counter-l3-note-region", *tuple(region_spec.public_id for region_spec in choice_regions)),
        },
    )
