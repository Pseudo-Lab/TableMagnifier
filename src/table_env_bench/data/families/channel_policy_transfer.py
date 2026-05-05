"""채널 집행 기준을 현재 표에 옮겨 적용하는 canonical family."""

from __future__ import annotations

from typing import Any

from table_env_bench.data.families.shared import (
    ChoiceCardSpec,
    TemplateManifest,
    cell,
    episode,
    note,
    page,
    query_choice_cards,
    query_header_blocks,
    rect,
    region,
    resolve_template_seed,
    rotate,
    sheet,
    table_from_cells,
    text_block,
)

FAMILY = "channel_policy_transfer"
FAMILY_LABEL = "채널 집행 기준 적용"

_LEVEL_REASONING_STEPS = {1: (2, 3), 2: (3, 4), 3: (4, 5)}
_LEVEL_RATIONALES = {
    1: "작은 집행 사례 표를 읽고 기준을 현재 표에 옮기는 2-3 step 문제다.",
    2: "두 달 사례를 비교해 묶음까지 함께 일반화해야 하는 3-4 step 문제다.",
    3: "두 달 사례와 기준 메모를 함께 반영해 최종 집행 대상을 고르는 4-5 step 문제다.",
}


def _manifest(level: int) -> TemplateManifest:
    required_sheet_ids = ("examples", "query")
    required_page_refs = ("examples:examples-p1", "query:query-p1")
    required_actions = ("must_switch_sheet",)
    required_evidence: tuple[dict[str, Any], ...] = (
        {"kind": "page", "sheet_id": "examples", "page_id": "examples-p1"},
        {"kind": "page", "sheet_id": "query", "page_id": "query-p1"},
    )
    cue_tags = ("band_scope", "icon_anchor")
    required_visual_cues = cue_tags
    if level >= 2:
        required_page_refs = (*required_page_refs, "examples:examples-p2")
        required_evidence = (*required_evidence, {"kind": "page", "sheet_id": "examples", "page_id": "examples-p2"})
        cue_tags = (*cue_tags, "row_group_band")
        required_visual_cues = cue_tags
    if level == 3:
        required_sheet_ids = ("examples", "appendix", "query")
        required_page_refs = (*required_page_refs, "appendix:appendix-p1")
        required_actions = (*required_actions, "must_open_note")
        required_evidence = (
            *required_evidence,
            {"kind": "page", "sheet_id": "appendix", "page_id": "appendix-p1"},
            {"kind": "note", "sheet_id": "appendix", "page_id": "appendix-p1", "note_id": "anchor-note"},
        )
        cue_tags = (*cue_tags, "note_scope")
        required_visual_cues = cue_tags
    return TemplateManifest(
        family=FAMILY,
        level=level,
        template_id="icon_scope_cell",
        template_label="아이콘 범위 셀 선택",
        latent_rule="사례 표에서 적용 밴드와 표식 위치를 읽고 현재 집행표에서 실제 반영 셀을 고른다.",
        operator_tags=("select_scope", "transfer"),
        cue_tags=cue_tags,
        answer_form="cell_choice",
        primary_operator="select_scope",
        support_operator="transfer",
        required_visual_cues=required_visual_cues,
        required_surfaces=("example_table_panel", "query_table_panel", "answer_choice_panel"),
        capability_axes=("visual_grounding", "scope_resolution", "rule_transfer"),
        task_archetype="review_verification",
        scenario_context="월간 집행 사례를 읽고 현재 채널 표에서 실제 반영 대상을 찾는 과업이다.",
        benchmark_track="canonical_real_tableqa",
        reasoning_archetype="induce_apply",
        abstraction_tier="abstract_worksheet",
        support_surface_policy="optional",
        qa_dependency="tableqa_transfer",
        generalization_group=f"{FAMILY}:icon_scope_cell:l{level}",
        required_sheet_ids=required_sheet_ids,
        required_page_refs=required_page_refs,
        allowed_cue_variants=("band_scope", "icon_anchor", "row_group_band", "note_scope"),
        distractor_policy="같은 표식이 다른 band나 다른 group에도 반복되게 두고, 잘못된 방향도 함께 배치한다.",
        level_rationale=_LEVEL_RATIONALES[level],
        text_only_failure_modes=(
            "현재 표만 읽으면 적용 밴드와 채널 묶음을 놓친 채 같은 표식이 있는 다른 셀을 고르게 된다.",
            "Level 3에서는 기준 메모 없이 어느 방향 표식이 실제 대상인지 고정되지 않는다.",
        ),
        distractor_failure_modes=(
            "같은 채널이지만 다른 집행 구간 셀을 고르는 오답",
            "같은 집행 구간이지만 다른 채널 묶음이나 다른 방향을 고르는 오답",
        ),
        level_knobs={"level": level, "template": "icon_scope_cell"},
        max_actions=7 + level,
        required_actions=required_actions,
        required_evidence=required_evidence,
        expected_min_steps=_LEVEL_REASONING_STEPS[level][0],
        expected_reasoning_steps=_LEVEL_REASONING_STEPS[level],
        shortcut_probes=("single_sheet_only", "text_scrape_only", "no_examples_page2" if level >= 2 else "single_page"),
    )


TEMPLATES_BY_LEVEL: dict[int, tuple[TemplateManifest, ...]] = {level: (_manifest(level),) for level in (1, 2, 3)}


def list_manifests(level: int) -> tuple[TemplateManifest, ...]:
    return TEMPLATES_BY_LEVEL[level]


def _triangle(anchor: str, *, color: str = "#0f766e") -> dict[str, Any]:
    return {"icon": {"kind": "triangle", "anchor": anchor, "color": color}}


def _frame(*, color: str = "#0f766e") -> dict[str, Any]:
    return {"frame": {"kind": "selection", "color": color}}


def _simple_scope_table(
    *,
    element_id: str,
    title: str,
    box,
    rows: list[tuple[str, str | None, str | None, str | None, str | None]],
    selected_target: tuple[int, int] | None = None,
    subtitle: str,
):
    cells = [
        cell(0, 0, "행", row_span=2, style="header"),
        cell(0, 1, "계획", col_span=2, style="header"),
        cell(0, 3, "집행", col_span=2, style="header"),
        cell(1, 1, "상태", style="header"),
        cell(1, 2, "조치", style="header"),
        cell(1, 3, "상태", style="header"),
        cell(1, 4, "조치", style="header"),
    ]
    for row_index, (label, basic_status, basic_action, review_status, review_action) in enumerate(rows, start=2):
        cells.append(cell(row_index, 0, label, style="row_label", align="left"))
        for col_index, marker in enumerate((basic_status, basic_action, review_status, review_action), start=1):
            metadata: dict[str, Any] = {}
            if marker is not None:
                metadata.update(_triangle(marker))
            if selected_target == (row_index, col_index):
                metadata.update(_frame())
            cells.append(cell(row_index, col_index, "", metadata=metadata))
    return table_from_cells(
        element_id,
        title,
        box,
        n_rows=2 + len(rows),
        n_cols=5,
        cells=cells,
        column_weights=(0.18, 0.205, 0.205, 0.205, 0.205),
        row_heights=(38, 36) + tuple(48 for _ in rows),
        subtitle=subtitle,
        worksheet_name=element_id.upper().replace("-", "_"),
    )


def _group_scope_table(
    *,
    element_id: str,
    title: str,
    box,
    groups: list[tuple[str, list[tuple[str, str | None, str | None, str | None, str | None]]]],
    selected_target: tuple[str, int] | None = None,
    subtitle: str,
):
    cells = [
        cell(0, 0, "묶음", row_span=2, style="header"),
        cell(0, 1, "행", row_span=2, style="header"),
        cell(0, 2, "계획", col_span=2, style="header"),
        cell(0, 4, "집행", col_span=2, style="header"),
        cell(1, 2, "상태", style="header"),
        cell(1, 3, "조치", style="header"),
        cell(1, 4, "상태", style="header"),
        cell(1, 5, "조치", style="header"),
    ]
    row_index = 2
    for group_label, rows in groups:
        cells.append(cell(row_index, 0, group_label, style="total_label", align="left"))
        cells.append(cell(row_index, 1, "", style="muted"))
        for col_index in range(2, 6):
            cells.append(cell(row_index, col_index, "", style="muted"))
        row_index += 1
        for row_label, basic_status, basic_action, review_status, review_action in rows:
            cells.append(cell(row_index, 0, "", style="muted"))
            cells.append(cell(row_index, 1, f"  {row_label}", style="row_label", align="left"))
            for col_index, marker in enumerate((basic_status, basic_action, review_status, review_action), start=2):
                metadata: dict[str, Any] = {}
                if marker is not None:
                    metadata.update(_triangle(marker))
                if selected_target == (row_label, col_index):
                    metadata.update(_frame())
                cells.append(cell(row_index, col_index, "", metadata=metadata))
            row_index += 1
    row_count = row_index
    return table_from_cells(
        element_id,
        title,
        box,
        n_rows=row_count,
        n_cols=6,
        cells=cells,
        column_weights=(0.18, 0.18, 0.16, 0.16, 0.16, 0.16),
        row_heights=(38, 34) + tuple(42 for _ in range(row_count - 2)),
        subtitle=subtitle,
        worksheet_name=element_id.upper().replace("-", "_"),
    )


def _target_cell_choice_cards(
    *,
    row_band_pairs: list[tuple[str, str]],
    seed_slot: int,
    columns: int = 4,
    width: float = 250.0,
    height: float = 118.0,
    gap_x: float = 18.0,
    gap_y: float = 18.0,
    x0: float = 92.0,
    y: float = 610.0,
) -> tuple[tuple[Any, ...], tuple[Any, ...], str]:
    letters = rotate(("A", "B", "C", "D"), seed_slot)
    cards = tuple(
        ChoiceCardSpec(choice_id=choice_id, title=f"{row_label} / {band_label}", lines=("선택 후보",))
        for choice_id, (row_label, band_label) in zip(letters, row_band_pairs)
    )
    elements, regions = query_choice_cards(
        prefix="transfer-choice",
        answer_form="cell_choice",
        cards=cards,
        y=y,
        columns=columns,
        width=width,
        height=height,
        gap_x=gap_x,
        gap_y=gap_y,
        x0=x0,
    )
    return elements, regions, letters[0]


def _query_header(
    *,
    target_lines: tuple[str, ...],
    guidance_lines: tuple[str, ...],
) -> tuple[tuple[Any, Any], float]:
    return query_header_blocks(
        target_title="집행 대상",
        target_lines=target_lines,
        guidance_title="집행 메모",
        guidance_lines=guidance_lines,
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
    row_names = rotate(("온라인", "오프라인", "도매", "제휴"), seed_slot)[:4]
    active_band = "집행" if seed_slot % 2 == 0 else "계획"
    target_col = 4 if active_band == "집행" else 2
    other_band_col = 1 if active_band == "집행" else 4

    example_1_rows = [
        (row_names[0], "bottom_left", None, None, "top_right"),
        (row_names[1], None, None, "bottom_left", None),
        (row_names[2], "top_right", None, None, None),
    ]
    example_2_rows = [
        (row_names[0], None, "top_right", None, None),
        (row_names[1], "bottom_left", None, None, None),
        (row_names[2], None, None, "top_right", "bottom_left"),
    ]
    query_rows = [
        (row_names[0], "top_right", None, None, None),
        (row_names[1], None, "bottom_left", None, None),
        (row_names[2], None, None, "bottom_left", None),
        (row_names[3], None, None, None, "top_right"),
    ]
    correct_row = row_names[3] if active_band == "집행" else row_names[0]
    distractors = [
        (row_names[1], "계획-조치"),
        (row_names[2], "집행-상태"),
        (row_names[0], "계획-상태"),
    ]
    if active_band == "계획":
        distractors = [
            (row_names[3], "집행-조치"),
            (row_names[1], "계획-조치"),
            (row_names[2], "집행-상태"),
        ]
    choices, choice_regions, answer_choice = _target_cell_choice_cards(
        row_band_pairs=[(correct_row, f"{active_band}-{'조치' if target_col in (2, 4) and target_col % 2 == 0 else '상태'}"), *distractors],
        seed_slot=seed_slot % 4,
        columns=2,
        width=440,
        height=104,
        gap_x=24,
        gap_y=14,
        x0=84,
        y=592,
    )
    example_1 = _simple_scope_table(
        element_id="transfer-l1-example-1",
        title="선행 사례 1",
        box=rect(84, 306, 512, 294),
        rows=example_1_rows,
        selected_target=(2, 4),
        subtitle="집행 완료 표에서 처리 위치를 함께 확인한다",
    )
    example_2 = _simple_scope_table(
        element_id="transfer-l1-example-2",
        title="선행 사례 2",
        box=rect(646, 306, 512, 294),
        rows=example_2_rows,
        selected_target=(4, 2),
        subtitle="같은 표식이라도 위치가 다르면 대상이 아니다",
    )
    query_table = _simple_scope_table(
        element_id="transfer-l1-query",
        title="",
        box=rect(84, 286, 720, 278),
        rows=query_rows,
        subtitle="",
    )
    query_blocks, _ = _query_header(
        target_lines=(f"{active_band} band 집행 행에서 실제 반영 위치를 확인합니다.",),
        guidance_lines=("선행 사례에서 확인된 기준만 유효하며 같은 band 안의 조치 셀만 대상으로 봅니다.",),
    )
    return episode(
        manifest=manifest,
        family_display_name=FAMILY_LABEL,
        question="선행 집행 사례를 반영했을 때 현재 표에서 반영 대상으로 맞는 위치는 어느 선택지인가?",
        workbook_title="집행 기준 워크북",
        sheets=[
            sheet(
                "examples",
                "사례",
                [
                    page(
                        "examples-p1",
                        "사례",
                        elements=[
                            text_block("transfer-l1-focus-1", "집행 밴드", rect(84, 150, 220, 74), (active_band,), style="callout", subtitle="사례 1"),
                            text_block("transfer-l1-focus-2", "집행 밴드", rect(646, 150, 220, 74), ("계획" if active_band == "집행" else "집행",), style="callout", subtitle="사례 2"),
                            example_1,
                            example_2,
                            text_block(
                                "transfer-l1-hint",
                                "집행 메모",
                                rect(84, 604, 1074, 140),
                                ("반영 위치는 얇은 프레임으로 표시됩니다.", "band와 표식 위치를 함께 읽어야 합니다."),
                                style="note",
                                subtitle="적용 기준",
                            ),
                        ],
                    )
                ],
            ),
            sheet(
                "query",
                "확인",
                [
                    page(
                        "query-p1",
                        "확인 시트",
                        elements=[
                            *query_blocks,
                            _simple_scope_table(
                                element_id="transfer-l1-query",
                                title="",
                                box=rect(84, 286, 720, 278),
                                rows=query_rows,
                                subtitle="",
                            ),
                            *choices,
                        ],
                        regions=choice_regions,
                    )
                ],
            ),
        ],
        answer=answer_choice,
        seed_slot=seed_slot,
        metadata_extra={"relevant_region_ids": tuple(region_spec.public_id for region_spec in choice_regions)},
    )


def _build_level_2(manifest: TemplateManifest, seed_slot: int):
    row_names = rotate(("가람", "나래", "다온", "라온", "마루", "바다"), seed_slot)
    groups = ("분석 묶음", "운영 묶음")
    active_band = "집행" if seed_slot % 2 == 0 else "계획"
    active_group = groups[seed_slot % 2]
    other_group = groups[1] if active_group == groups[0] else groups[0]
    target_col = 5 if active_band == "집행" else 3
    target_label = f"{active_band}-조치"

    examples_page_1_groups = [
        (
            groups[0],
            [
                (row_names[0], None, "top_right", None, None),
                (row_names[1], "bottom_left", None, None, None),
            ],
        ),
        (
            groups[1],
            [
                (row_names[2], None, None, None, "top_right"),
                (row_names[3], None, None, "bottom_left", None),
            ],
        ),
    ]
    examples_page_2_groups = [
        (
            groups[0],
            [
                (row_names[0], None, "bottom_left", None, None),
                (row_names[1], None, "top_right", None, None),
            ],
        ),
        (
            groups[1],
            [
                (row_names[2], None, None, "bottom_left", None),
                (row_names[3], None, None, None, "top_right"),
            ],
        ),
    ]
    query_groups = [
        (
            groups[0],
            [
                (row_names[0], "top_right", None, None, None),
                (row_names[1], None, "top_right" if active_group == groups[0] and active_band == "계획" else "bottom_left", None, None),
            ],
        ),
        (
            groups[1],
            [
                (row_names[2], None, None, "top_right" if active_group == groups[1] and active_band == "집행" else "bottom_left", None),
                (row_names[3], None, None, None, "top_right" if active_group == groups[1] and active_band == "집행" else "bottom_left"),
            ],
        ),
    ]
    correct_row = row_names[1] if active_group == groups[0] and active_band == "계획" else row_names[3] if active_group == groups[1] and active_band == "집행" else row_names[0] if active_group == groups[0] else row_names[2]
    if active_group == groups[0] and active_band == "집행":
        query_groups[0][1][0] = (row_names[0], None, None, None, "top_right")
    if active_group == groups[1] and active_band == "계획":
        query_groups[1][1][0] = (row_names[2], None, "top_right", None, None)
    distractors = [
        (row_names[0] if correct_row != row_names[0] else row_names[2], target_label),
        (correct_row, "계획-조치" if active_band == "집행" else "집행-조치"),
        (row_names[2] if active_group == groups[0] else row_names[1], target_label),
    ]
    choices, choice_regions, answer_choice = _target_cell_choice_cards(
        row_band_pairs=[(correct_row, target_label), *distractors],
        seed_slot=seed_slot % 4,
        columns=2,
        width=440,
        height=104,
        gap_x=24,
        gap_y=14,
        x0=84,
        y=592,
    )
    example_page_1 = _group_scope_table(
        element_id="transfer-l2-example-1",
        title="집행 사례 비교",
        box=rect(84, 276, 1074, 308),
        groups=examples_page_1_groups,
        selected_target=(row_names[2], 5),
        subtitle="첫 사례에서는 운영 묶음의 집행 셀이 실제 대상으로 확정된다",
    )
    example_page_2 = _group_scope_table(
        element_id="transfer-l2-example-2",
        title="보강 사례",
        box=rect(84, 286, 1074, 308),
        groups=examples_page_2_groups,
        selected_target=(row_names[1], 3),
        subtitle="보강 사례는 묶음 경계와 집행 밴드를 함께 고정한다",
    )
    query_table = _group_scope_table(
        element_id="transfer-l2-query",
        title="",
        box=rect(84, 286, 720, 294),
        groups=query_groups,
        subtitle="",
    )
    query_blocks, _ = _query_header(
        target_lines=(f"{active_band} band · {active_group}",),
        guidance_lines=("보강 사례를 반영해 같은 묶음 안의 후보만 남깁니다.",),
    )
    return episode(
        manifest=manifest,
        family_display_name=FAMILY_LABEL,
        question="집행 사례 두 페이지를 모두 반영했을 때 현재 표에서 반영 대상으로 맞는 위치는 어느 선택지인가?",
        workbook_title="집행 기준 워크북",
        sheets=[
            sheet(
                "examples",
                "사례",
                [
                    page(
                        "examples-p1",
                        "사례",
                        elements=[
                            text_block("transfer-l2-band-chip", "집행 밴드", rect(84, 154, 220, 52), (active_band,), style="callout"),
                            text_block("transfer-l2-group-chip", "집행 묶음", rect(330, 154, 220, 52), (active_group,), style="callout"),
                            example_page_1,
                        ],
                    ),
                    page(
                        "examples-p2",
                        "보강 사례",
                        elements=[
                            text_block("transfer-l2-band-chip-2", "집행 밴드", rect(84, 154, 220, 52), ("계획" if active_band == "집행" else "집행",), style="callout"),
                            text_block("transfer-l2-group-chip-2", "집행 묶음", rect(330, 154, 220, 52), (other_group,), style="callout"),
                            example_page_2,
                            text_block(
                                "transfer-l2-note",
                                "집행 메모",
                                rect(84, 612, 1074, 132),
                                ("묶음 머리글 아래 있는 행만 같은 후보군이다.", "같은 표식이라도 묶음이 다르면 대상이 아니다."),
                                style="note",
                            ),
                        ],
                    ),
                ],
            ),
            sheet(
                "query",
                "확인",
                [
                    page(
                        "query-p1",
                        "확인 시트",
                        elements=[
                            *query_blocks,
                            query_table,
                            *choices,
                        ],
                        regions=choice_regions,
                    )
                ],
            ),
        ],
        answer=answer_choice,
        seed_slot=seed_slot,
        metadata_extra={"relevant_region_ids": tuple(region_spec.public_id for region_spec in choice_regions)},
    )


def _build_level_3(manifest: TemplateManifest, seed_slot: int):
    row_names = rotate(("가람", "나래", "다온", "라온", "마루", "바다"), seed_slot)
    groups = ("분석 묶음", "운영 묶음")
    active_band = "집행" if seed_slot % 2 == 0 else "계획"
    active_group = groups[0] if seed_slot % 3 else groups[1]
    required_anchor = "top_right" if seed_slot % 2 == 0 else "bottom_left"
    other_anchor = "bottom_left" if required_anchor == "top_right" else "top_right"
    target_col = 5 if active_band == "집행" else 3
    target_label = f"{active_band}-조치"

    examples_page_1 = _group_scope_table(
        element_id="transfer-l3-example-1",
        title="선행 사례 1",
        box=rect(84, 272, 1074, 292),
        groups=[
            (groups[0], [(row_names[0], None, "top_right", None, None), (row_names[1], None, other_anchor, None, None)]),
            (groups[1], [(row_names[2], None, None, None, "top_right"), (row_names[3], None, None, None, other_anchor)]),
        ],
        selected_target=(row_names[0], 3),
        subtitle="첫 사례만 보면 방향이 아직 완전히 고정되지 않는다",
    )
    examples_page_2 = _group_scope_table(
        element_id="transfer-l3-example-2",
        title="보강 사례",
        box=rect(84, 272, 1074, 292),
        groups=[
            (groups[0], [(row_names[0], None, required_anchor, None, None), (row_names[1], None, other_anchor, None, None)]),
            (groups[1], [(row_names[2], None, None, None, required_anchor), (row_names[3], None, None, None, other_anchor)]),
        ],
        selected_target=(row_names[2], 5),
        subtitle="보강 사례는 묶음을 다시 보여 주지만 기준 메모 확인 전에는 방향 확정이 부족하다",
    )
    correct_row = row_names[0] if active_group == groups[0] else row_names[2]
    query_groups = [
        (groups[0], [(row_names[0], None, required_anchor if active_band == "계획" else None, None, required_anchor if active_band == "집행" else None), (row_names[1], None, other_anchor if active_band == "계획" else None, None, other_anchor if active_band == "집행" else None)]),
        (groups[1], [(row_names[2], None, required_anchor if active_band == "계획" else None, None, required_anchor if active_band == "집행" else None), (row_names[3], None, other_anchor if active_band == "계획" else None, None, other_anchor if active_band == "집행" else None)]),
    ]
    if active_group == groups[1]:
        correct_row = row_names[2]
    distractors = [
        (row_names[1] if active_group == groups[0] else row_names[3], target_label),
        (correct_row, "계획-조치" if active_band == "집행" else "집행-조치"),
        (row_names[2] if active_group == groups[0] else row_names[0], target_label),
    ]
    choices, choice_regions, answer_choice = _target_cell_choice_cards(
        row_band_pairs=[(correct_row, target_label), *distractors],
        seed_slot=seed_slot % 4,
        columns=2,
        width=440,
        height=104,
        gap_x=24,
        gap_y=14,
        x0=84,
        y=592,
    )
    appendix_note = text_block(
        "transfer-l3-appendix-block",
        "집행 기준 메모",
        rect(140, 176, 980, 236),
        (
            f"{active_band} band에서는 {required_anchor} 방향 삼각형만 실제 후보다.",
            f"같은 묶음 안의 {other_anchor} 방향 삼각형은 제외한다.",
            f"현재 묶음이 {active_group}일 때도 기준은 그대로다.",
        ),
        style="note",
        subtitle="적용 기준",
    )
    appendix_checklist = text_block(
        "transfer-l3-appendix-checklist",
        "확인 절차",
        rect(140, 438, 980, 152),
        (
            "1. 사례 두 페이지에서 band와 묶음을 먼저 고정한다.",
            f"2. 기준 메모에서는 {required_anchor} 방향만 유효한 삼각형으로 인정한다.",
            f"3. 확인 표에서 같은 묶음 안의 {other_anchor} 방향 후보는 버린다.",
        ),
        style="note",
        subtitle="적용 순서",
    )
    query_table = _group_scope_table(
        element_id="transfer-l3-query",
        title="",
        box=rect(84, 286, 720, 280),
        groups=query_groups,
        subtitle="",
    )
    query_blocks, _ = _query_header(
        target_lines=(f"{active_band} band · {active_group}",),
        guidance_lines=(f"기준 메모를 반영해 {required_anchor} 방향만 실제 후보로 인정합니다.",),
    )
    return episode(
        manifest=manifest,
        family_display_name=FAMILY_LABEL,
        question="보강 사례와 기준 메모까지 반영했을 때 현재 표에서 반영 대상으로 맞는 위치는 어느 선택지인가?",
        workbook_title="집행 기준 워크북",
        sheets=[
            sheet(
                "examples",
                "사례",
                [
                    page(
                        "examples-p1",
                        "사례",
                        elements=[
                            text_block("transfer-l3-band-chip", "집행 밴드", rect(84, 150, 220, 52), (active_band,), style="callout"),
                            text_block("transfer-l3-group-chip", "집행 묶음", rect(330, 150, 220, 52), (active_group,), style="callout"),
                            examples_page_1,
                        ],
                    ),
                    page(
                        "examples-p2",
                        "보강 사례",
                        elements=[
                            text_block("transfer-l3-band-chip-2", "집행 밴드", rect(84, 150, 220, 52), (active_band,), style="callout"),
                            text_block("transfer-l3-group-chip-2", "집행 묶음", rect(330, 150, 220, 52), (active_group,), style="callout"),
                            examples_page_2,
                        ],
                    ),
                ],
            ),
            sheet(
                "appendix",
                "기준 메모",
                [
                    page(
                        "appendix-p1",
                        "기준 메모",
                        elements=[appendix_note, appendix_checklist],
                        notes=(note("anchor-note", "기준 메모", f"{active_band} band에서는 {required_anchor} 방향만 실제 대상으로 본다."),),
                        regions=(region("appendix-note-region", "note_marker", "기준 메모", appendix_note.rect, linked_note_id="anchor-note"),),
                    )
                ],
            ),
            sheet(
                "query",
                "확인",
                [
                    page(
                        "query-p1",
                        "확인 시트",
                        elements=[
                            *query_blocks,
                            query_table,
                            *choices,
                        ],
                        regions=choice_regions,
                    )
                ],
            ),
        ],
        answer=answer_choice,
        seed_slot=seed_slot,
        metadata_extra={
            "relevant_region_ids": ("appendix-note-region", *tuple(region_spec.public_id for region_spec in choice_regions)),
        },
    )
