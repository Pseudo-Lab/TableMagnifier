"""Excel-like viewport and sheet navigation canonical family."""

from __future__ import annotations

from typing import Any

from table_env_bench.data.families.shared import (
    ChoiceCardSpec,
    TemplateManifest,
    cell,
    episode,
    page,
    query_choice_cards,
    query_header_blocks,
    rect,
    resolve_template_seed,
    rotate,
    sheet,
    table_from_cells,
    text_block,
)

FAMILY = "excel_viewport_sheet_navigation"
FAMILY_LABEL = "스프레드시트 뷰포트 탐색"
TEMPLATE_ID = "wide_sheet_rule_transfer"

_LEVEL_REASONING_STEPS = {1: (3, 4), 2: (4, 5), 3: (5, 5)}
_LEVEL_RATIONALES = {
    1: "넓은 질의표의 오른쪽 target column을 확대 후 이동해 확인하는 3-4단계 과업이다.",
    2: "두 번째 사례 페이지까지 확인한 뒤 같은 열 이동 규칙을 적용하는 4-5단계 과업이다.",
    3: "연산자 시트의 예외 규칙과 넓은 질의표의 오른쪽 target column을 결합하는 5단계 과업이다.",
}


def _required_navigation(level: int) -> dict[str, Any]:
    sheet_ids = ["examples", "query"] if level < 3 else ["examples", "operators", "query"]
    page_refs = ["examples:examples-p1", "query:query-p1"]
    if level >= 2:
        page_refs.insert(1, "examples:examples-p2")
    if level == 3:
        page_refs.insert(-1, "operators:operators-p1")
    return {
        "required_sheet_ids": sheet_ids,
        "required_page_refs": page_refs,
        "required_viewport_states": [
            {
                "state_id": "query-right-target",
                "sheet_id": "query",
                "page_id": "query-p1",
                "min_zoom_index": 1,
                "required_action_types": ["zoom_in", "pan_right"],
                "match": "target_center_in_viewbox",
                "target_rects": [
                    {
                        "target_id": "query-target-column",
                        "kind": "element",
                        "rect": {"x": 1088, "y": 310, "width": 112, "height": 154},
                    }
                ],
            }
        ],
        "forbidden_shortcuts": ["initial_viewport_only", "no_pan_zoom", "sheet_skip"],
    }


def _manifest(level: int) -> TemplateManifest:
    required_evidence: tuple[dict[str, Any], ...] = (
        {"kind": "page", "sheet_id": "examples", "page_id": "examples-p1"},
        {"kind": "page", "sheet_id": "query", "page_id": "query-p1"},
    )
    cue_tags = ("wide_grid", "column_offset", "viewport_pan")
    if level >= 2:
        required_evidence = (
            *required_evidence,
            {"kind": "page", "sheet_id": "examples", "page_id": "examples-p2"},
        )
        cue_tags = (*cue_tags, "second_example")
    if level == 3:
        required_evidence = (
            *required_evidence,
            {"kind": "page", "sheet_id": "operators", "page_id": "operators-p1"},
        )
        cue_tags = (*cue_tags, "operator_sheet")
    return TemplateManifest(
        family=FAMILY,
        level=level,
        template_id=TEMPLATE_ID,
        template_label="넓은 시트 열 이동 규칙",
        latent_rule="사례 시트의 기준 열에서 오른쪽으로 이동한 target 열 값을 읽고 질의 시트에 같은 이동 규칙을 적용한다.",
        operator_tags=("match_column_offset", "rule_transfer", "select_choice"),
        cue_tags=cue_tags,
        answer_form="statement_choice",
        primary_operator="match_column_offset",
        support_operator="rule_transfer",
        required_visual_cues=cue_tags,
        required_surfaces=("example_wide_table", "query_wide_table", "answer_choice_panel"),
        capability_axes=("visual_grounding", "navigation", "rule_transfer"),
        task_archetype="excel_viewport_transfer",
        scenario_context="넓은 업무 시트에서 열이 화면 밖으로 이어지는 상황을 확대와 가로 이동으로 확인한다.",
        benchmark_track="canonical_real_tableqa",
        reasoning_archetype="induce_apply",
        abstraction_tier="abstract_worksheet",
        support_surface_policy="required",
        qa_dependency="hybrid_induction_tableqa",
        generalization_group=f"{FAMILY}:{TEMPLATE_ID}:l{level}",
        required_sheet_ids=(),
        required_page_refs=(),
        required_navigation=_required_navigation(level),
        allowed_cue_variants=("right_offset", "wide_table", "operator_sheet"),
        distractor_policy="초기 뷰포트에 보이는 값과 오른쪽 target 열 값을 다르게 두어 pan/zoom 없이 고르면 틀리게 만든다.",
        level_rationale=_LEVEL_RATIONALES[level],
        text_only_failure_modes=(
            "초기 화면의 왼쪽 열만 보면 target 열까지 이동해야 한다는 근거를 놓친다.",
            "시트 전환 없이 질의표만 보면 사례의 열 이동 규칙을 확인할 수 없다.",
        ),
        distractor_failure_modes=(
            "초기 뷰포트에 보이는 점검 열 값을 정답으로 고르는 오답",
            "사례 시트의 기준 열만 읽고 오른쪽 target 열까지 이동하지 않는 오답",
        ),
        level_knobs={"level": level, "template": TEMPLATE_ID, "page_size": "1280x900"},
        max_actions=9 + level,
        required_evidence=required_evidence,
        expected_min_steps=_LEVEL_REASONING_STEPS[level][0],
        expected_reasoning_steps=_LEVEL_REASONING_STEPS[level],
        shortcut_probes=("query_only", "initial_viewport_only", "no_pan_zoom", "sheet_skip"),
    )


TEMPLATES_BY_LEVEL: dict[int, tuple[TemplateManifest, ...]] = {level: (_manifest(level),) for level in (1, 2, 3)}


def list_manifests(level: int) -> tuple[TemplateManifest, ...]:
    return TEMPLATES_BY_LEVEL[level]


def _wide_table(
    *,
    element_id: str,
    title: str,
    box,
    rows: tuple[tuple[str, str, str, str], ...],
    target_label: str,
    subtitle: str,
):
    headers = ("행", "항목", "점검", "보류", "참조", "target")
    cells = [cell(0, col, header, style="header", align="center") for col, header in enumerate(headers)]
    for row_index, (row_id, item, check, target) in enumerate(rows, start=1):
        cells.extend(
            [
                cell(row_index, 0, row_id, style="index"),
                cell(row_index, 1, item, style="row_label", align="left"),
                cell(row_index, 2, check, style="numeric", align="right"),
                cell(row_index, 3, "-", style="muted"),
                cell(row_index, 4, "규칙", style="muted"),
                cell(row_index, 5, target, style="highlight" if item == target_label else "numeric", align="right"),
            ]
        )
    return table_from_cells(
        element_id,
        title,
        box,
        n_rows=len(rows) + 1,
        n_cols=len(headers),
        cells=cells,
        column_weights=(0.08, 0.22, 0.14, 0.16, 0.16, 0.24),
        row_heights=(42,) + tuple(46 for _ in rows),
        subtitle=subtitle,
        worksheet_name=element_id.upper().replace("-", "_"),
    )


def _choice_cards(answer: str, *, seed_slot: int):
    labels = rotate(("A", "B", "C", "D"), seed_slot)
    card_specs = [
        ChoiceCardSpec(labels[0], f"{answer}", ("target 열의 값",), "body"),
        ChoiceCardSpec(labels[1], "118", ("초기 점검 열 값",), "body"),
        ChoiceCardSpec(labels[2], "126", ("보류 열을 읽은 값",), "body"),
        ChoiceCardSpec(labels[3], "143", ("다른 행 target 값",), "body"),
    ]
    elements, regions = query_choice_cards(
        prefix="excel-choice",
        cards=card_specs,
        answer_form="statement_choice",
        y=594,
        width=430,
        height=104,
        gap_x=24,
        gap_y=14,
    )
    return elements, regions, labels[0]


def _operator_table():
    cells = [
        cell(0, 0, "단계", style="header", align="center"),
        cell(0, 1, "동작", style="header", align="center"),
        cell(0, 2, "적용 근거", style="header", align="center"),
        cell(1, 0, "1", style="index"),
        cell(1, 1, "같은 행 라벨 선택", style="row_label", align="left"),
        cell(1, 2, "항목명이 같은 행만 비교한다", align="left"),
        cell(2, 0, "2", style="index"),
        cell(2, 1, "점검 열 건너뜀", style="row_label", align="left"),
        cell(2, 2, "점검 값은 후보 확인용이다", align="left"),
        cell(3, 0, "3", style="index"),
        cell(3, 1, "target 열로 이동", style="highlight", align="left"),
        cell(3, 2, "오른쪽 target 값이 최종 답이다", style="highlight", align="left"),
    ]
    return table_from_cells(
        "excel-operator-table",
        "연산자 적용 순서",
        rect(84, 420, 720, 190),
        n_rows=4,
        n_cols=3,
        cells=cells,
        column_weights=(0.14, 0.34, 0.52),
        row_heights=(40, 44, 44, 44),
        subtitle="오른쪽 열 이동은 질의 시트에서도 그대로 적용한다",
    )


def build_episode(level: int, seed: int, *, template_id: str | None = None):
    manifest, seed_slot = resolve_template_seed(TEMPLATES_BY_LEVEL[level], seed, template_id=template_id)
    products = rotate(("가람", "나래", "다온", "라온"), seed_slot)
    target_item = products[1]
    target_value = str(130 + seed_slot)
    rows = (
        ("17", products[0], "118", "121"),
        ("18", target_item, "119", target_value),
        ("19", products[2], "120", "143"),
    )
    examples = [
        page(
            "examples-p1",
            "사례 시트",
            elements=[
                text_block(
                    "excel-rule-hint",
                    "사례 규칙",
                    rect(84, 150, 520, 82),
                    ("점검 열이 아니라 오른쪽 target 열을 최종 값으로 읽는다.",),
                    style="callout",
                ),
                _wide_table(
                    element_id="excel-example-table-1",
                    title="3월 처리 사례",
                    box=rect(84, 300, 1116, 214),
                    rows=rows,
                    target_label=target_item,
                    subtitle="오른쪽 target 열이 최종 판정값이다",
                ),
            ],
        )
    ]
    if level >= 2:
        examples.append(
            page(
                "examples-p2",
                "추가 사례",
                elements=[
                    _wide_table(
                        element_id="excel-example-table-2",
                        title="4월 처리 사례",
                        box=rect(84, 240, 1116, 214),
                        rows=rows,
                        target_label=target_item,
                        subtitle="다른 월에도 target 열만 최종 값으로 쓰인다",
                    )
                ],
            )
        )
    query_blocks, _ = query_header_blocks(
        target_title="질의 행",
        target_lines=(f"{target_item} 행의 최종 값을 고릅니다.",),
        guidance_title="탐색 규칙",
        guidance_lines=("사례와 같은 열 이동 규칙을 적용하고, 질의 시트 오른쪽 target 열까지 이동합니다.",),
    )
    choices, choice_regions, answer_choice = _choice_cards(target_value, seed_slot=seed_slot)
    query_sheet = sheet(
        "query",
        "질의",
        [
            page(
                "query-p1",
                "질의 시트",
                elements=[
                    *query_blocks,
                    _wide_table(
                        element_id="excel-query-table",
                        title="현재 처리 시트",
                        box=rect(84, 310, 1116, 214),
                        rows=rows,
                        target_label=target_item,
                        subtitle="target 열은 초기 뷰포트 오른쪽에 있다",
                    ),
                    *choices,
                ],
                regions=choice_regions,
            )
        ],
    )
    sheets = [sheet("examples", "사례", examples), query_sheet]
    if level == 3:
        sheets.insert(
            1,
            sheet(
                "operators",
                "연산자",
                [
                    page(
                        "operators-p1",
                        "연산자 시트",
                        elements=[
                            text_block(
                                "excel-operator-note",
                                "열 이동 규칙",
                                rect(84, 220, 780, 130),
                                ("점검 열은 후보 확인용이며, 최종 답은 같은 행의 target 열이다.", "행 라벨이 같아야 하며 다른 행 target 값은 제외한다."),
                                style="note",
                            ),
                            _operator_table(),
                        ],
                    )
                ],
            ),
        )
    return episode(
        manifest=manifest,
        family_display_name=FAMILY_LABEL,
        question="사례 시트의 열 이동 규칙을 현재 시트에 적용했을 때 최종 값은 어느 선택지인가?",
        workbook_title="넓은 스프레드시트 탐색 워크북",
        sheets=sheets,
        answer=answer_choice,
        seed_slot=seed_slot,
    )
