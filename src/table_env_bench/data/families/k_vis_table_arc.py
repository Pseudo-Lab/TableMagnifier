"""Korean visual table agent reasoning pilot family."""

from __future__ import annotations

import random
from typing import Any

from table_env_bench.data.models import AnswerSpec, PageSpec
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
    sheet,
    table_from_cells,
    text_block,
)

FAMILY = "k_vis_table_arc"
FAMILY_LABEL = "K-VisTable-ARC 파일럿"
BENCHMARK_TRACK = "korean_visual_table_agent_reasoning"

TEMPLATE_SPECS = {
    "symbol_rule_induction": {
        "label": "특수 기호 규칙 유도",
        "answer_form": "number",
        "primary_operator": "induce_symbol_rule",
        "support_operator": "calculate",
        "cue_tags": ("symbol_position", "completed_example_rows"),
        "capabilities": ("visual_grounding", "rule_induction", "calculation"),
        "context": "완성된 행에서 특수 기호의 의미를 유도하고 미완성 행에 적용한다.",
    },
    "merged_header_scope": {
        "label": "병합 헤더 범위 상속",
        "answer_form": "number",
        "primary_operator": "resolve_header_scope",
        "support_operator": "compare_calculate",
        "cue_tags": ("merged_header", "column_group_scope"),
        "capabilities": ("layout_understanding", "scope_resolution", "calculation"),
        "context": "다단 병합 헤더가 지시하는 기간, 권역, 채널 범위를 따라간다.",
    },
    "abbrev_doc_reference": {
        "label": "합성 약어 문서 참조",
        "answer_form": "number",
        "primary_operator": "lookup_document_rule",
        "support_operator": "unit_conversion",
        "cue_tags": ("glossary_page", "unit_note", "abbrev_header"),
        "capabilities": ("document_reference", "table_lookup", "calculation"),
        "context": "메인 표의 합성 약어를 별도 약어 문서에서 해석한 뒤 계산한다.",
    },
    "wide_table_navigation": {
        "label": "넓은 테이블 탐색 계산",
        "answer_form": "number",
        "primary_operator": "navigate_wide_table",
        "support_operator": "subtract_convert_unit",
        "cue_tags": ("wide_column_index", "similar_header_distractor", "unit_header"),
        "capabilities": ("navigation", "memory", "table_lookup", "calculation"),
        "context": "많은 열 중 조건에 맞는 행과 유사한 열명을 구분해 필요한 값을 계산한다.",
    },
    "color_condition_rule_induction": {
        "label": "색상·패턴 조건 규칙 유도",
        "answer_form": "count",
        "primary_operator": "filter_members",
        "support_operator": "induce_condition_rule",
        "cue_tags": ("conditional_format_pattern", "cell_frame", "completed_example_rows"),
        "capabilities": ("visual_grounding", "rule_induction", "classification"),
        "context": "완성 예시에서 색/패턴/테두리 조합의 포함 규칙을 유도하고 질의 표에 적용한다.",
    },
    "legend_color_exception_scope": {
        "label": "범례 색상 예외 범위",
        "answer_form": "count",
        "primary_operator": "classify_state",
        "support_operator": "lookup_legend_rule",
        "cue_tags": ("legend_page", "conditional_format_pattern", "exception_frame"),
        "capabilities": ("document_reference", "visual_grounding", "exception_handling"),
        "context": "범례의 색상·패턴 의미와 질의 표의 예외 테두리를 함께 반영해 대상을 분류한다.",
    },
    "wide_table_viewport_trace": {
        "label": "넓은 표 뷰포트 추적",
        "answer_form": "number",
        "primary_operator": "match_column_offset",
        "support_operator": "navigate_wide_table",
        "cue_tags": ("viewport_window", "wide_column_index", "small_text_column"),
        "capabilities": ("navigation", "memory", "table_lookup", "calculation"),
        "context": "예시에서 학습한 열 오프셋을 넓은 질의 표의 같은 행에 적용하려면 pan/zoom이 필요하다.",
    },
    "merged_header_pan_scope": {
        "label": "병합 헤더 원거리 범위 추적",
        "answer_form": "number",
        "primary_operator": "resolve_header_scope",
        "support_operator": "navigate_wide_table",
        "cue_tags": ("merged_header", "column_group_scope", "viewport_window"),
        "capabilities": ("layout_understanding", "navigation", "scope_resolution"),
        "context": "병합 헤더가 정한 원거리 열 범위를 기억한 채 넓은 표를 이동해 값을 비교한다.",
    },
    "zoom_micro_marker_exception": {
        "label": "확대 필요 미세 마커 예외",
        "answer_form": "number",
        "primary_operator": "exception_by_icon_anchor",
        "support_operator": "zoom_inspect_marker",
        "cue_tags": ("icon_anchor_position", "micro_marker", "exception_rule"),
        "capabilities": ("zoom_inspection", "visual_grounding", "exception_handling"),
        "context": "작은 코너 마커의 위치가 예외 적용 범위를 바꾸므로 확대 관찰 후 계산한다.",
    },
}


def _manifest(level: int, template_id: str) -> TemplateManifest:
    spec = TEMPLATE_SPECS[template_id]
    required_sheet_ids = ("examples", "query")
    required_page_refs = ("examples:examples-p1", "query:query-p1")
    support_policy = "required"
    if template_id == "abbrev_doc_reference":
        required_sheet_ids = ("main", "glossary", "query")
        required_page_refs = ("main:main-p1", "glossary:glossary-p1", "query:query-p1")
    elif template_id == "wide_table_navigation":
        required_sheet_ids = ("directory", "wide", "query")
        required_page_refs = ("directory:directory-p1", "wide:wide-p1", "query:query-p1")
    elif template_id == "merged_header_scope":
        required_sheet_ids = ("examples", "notes", "query")
        required_page_refs = ("examples:examples-p1", "notes:notes-p1", "query:query-p1")
    elif template_id == "color_condition_rule_induction":
        required_sheet_ids = ("examples", "query")
        required_page_refs = ("examples:examples-p1", "query:query-p1")
    elif template_id == "legend_color_exception_scope":
        required_sheet_ids = ("legend", "query")
        required_page_refs = ("legend:legend-p1", "query:query-p1")
    elif template_id in {"wide_table_viewport_trace", "merged_header_pan_scope"}:
        required_sheet_ids = ("examples", "wide", "query")
        required_page_refs = ("examples:examples-p1", "wide:wide-p1", "query:query-p1")
    elif template_id == "zoom_micro_marker_exception":
        required_sheet_ids = ("examples", "query")
        required_page_refs = ("examples:examples-p1", "query:query-p1")
    if level >= 3:
        required_page_refs = (*required_page_refs, "query:query-p2")

    return TemplateManifest(
        family=FAMILY,
        level=level,
        template_id=template_id,
        template_label=str(spec["label"]),
        latent_rule=str(spec["context"]),
        operator_tags=(str(spec["primary_operator"]), "calculate", "verify"),
        cue_tags=tuple(spec["cue_tags"]),
        answer_form=str(spec["answer_form"]),
        primary_operator=str(spec["primary_operator"]),
        support_operator=str(spec["support_operator"]),
        required_visual_cues=tuple(spec["cue_tags"]),
        required_surfaces=("rendered_table", "support_document", "query_panel"),
        capability_axes=tuple(spec["capabilities"]),
        required_sheet_ids=required_sheet_ids,
        required_page_refs=required_page_refs,
        allowed_cue_variants=("symbol", "merged", "abbrev", "wide", "unit", "pattern", "frame", "icon", "viewport"),
        distractor_policy="유사한 헤더, 같은 숫자의 다른 단위, query-only로 고를 수 있는 오답을 포함한다.",
        level_rationale={
            1: "작은 표와 단일 규칙으로 2-3단계 탐색 후 계산한다.",
            2: "문서/헤더/기호 단서가 하나 더 추가되어 3-4단계가 필요하다.",
            3: "예외 또는 보조 페이지가 wrong rule을 제거해 4-5단계 추론이 필요하다.",
        }[level],
        text_only_failure_modes=(
            "표 구조와 병합/기호 위치를 버리면 적용 범위가 고정되지 않는다.",
            "약어와 단위가 에피소드별 합성이므로 사전지식만으로는 계산 규칙을 알 수 없다.",
        ),
        distractor_failure_modes=(
            "비슷한 열명 또는 같은 숫자의 다른 단위 선택",
            "지원 문서를 건너뛰고 메인 표 숫자만 조합",
            "Level 3 예외 페이지를 무시한 기본 규칙 적용",
        ),
        task_archetype=template_id,
        scenario_context=str(spec["context"]),
        benchmark_track=BENCHMARK_TRACK,
        reasoning_archetype="explore_induce_apply",
        abstraction_tier="interactive_episode",
        support_surface_policy=support_policy,
        qa_dependency="visual_layout_agentic_reasoning",
        generalization_group=f"{FAMILY}:{template_id}",
        max_actions=8 + level * 3,
        required_navigation={
            "required_sheet_ids": list(required_sheet_ids),
            "required_page_refs": list(required_page_refs),
            "forbidden_shortcuts": ["query_only", "hidden_grid_text", "oracle_metadata"],
        },
        required_evidence=tuple(
            {"kind": "page", "sheet_id": item.split(":")[0], "page_id": item.split(":")[1]}
            for item in required_page_refs
        ),
        expected_min_steps=level + 2,
        expected_reasoning_steps=(level + 1, level + 2),
        shortcut_probes=("query_only", "document_skip", "text_scrape", "unit_skip"),
        holdout_group=f"{template_id}_ood_level_{level}",
    )


TEMPLATES_BY_LEVEL: dict[int, tuple[TemplateManifest, ...]] = {
    level: tuple(_manifest(level, template_id) for template_id in TEMPLATE_SPECS)
    for level in (1, 2, 3)
}


def list_manifests(level: int) -> tuple[TemplateManifest, ...]:
    return TEMPLATES_BY_LEVEL[level]


CHOICE_IDS = ("A", "B", "C", "D")

SUPPLEMENTAL_NOTICE_BY_TEMPLATE = {
    "symbol_rule_induction": (
        "마킹 검수 보조 공지",
        "동일 문서 묶음의 미분류 레코드는 샘플 로그와 보조 공지를 함께 보관합니다.",
        "처리값은 원문 표기와 마커 토큰 상태를 기준으로 판독합니다.",
    ),
    "color_condition_rule_induction": (
        "조건부 서식 보조 공지",
        "서식이 남아 있는 감사 표는 텍스트 상태와 시각 표식을 함께 보관합니다.",
        "범위 판독은 같은 리포트 묶음의 표시 기준을 따릅니다.",
    ),
    "legend_color_exception_scope": (
        "상태 코드 예외 공지",
        "상태 코드 범례와 예외 bulletin은 같은 검토 묶음으로 관리됩니다.",
        "우선순위가 있는 표식은 문서 내 기준표를 기준으로 해석합니다.",
    ),
    "merged_header_scope": (
        "보고 기준 보조 메모",
        "운영 매트릭스는 상위 그룹 헤더와 하위 지표 열을 함께 보관합니다.",
        "단위 및 기간 표기는 리포팅 표준 문서의 정의를 따릅니다.",
    ),
    "wide_table_navigation": (
        "원장 탐색 보조 메모",
        "열 인덱스와 원장 표는 같은 데이터 추출 묶음으로 보관됩니다.",
        "가로 이동 상태에 따라 표시되는 열 범위가 달라질 수 있습니다.",
    ),
    "wide_table_viewport_trace": (
        "뷰포트 추적 보조 메모",
        "이전 화면 캡처 로그와 원장 표시는 같은 탐색 세션에 속합니다.",
        "표시 범위와 열 오프셋은 화면 기록을 기준으로 대조합니다.",
    ),
    "merged_header_pan_scope": (
        "원거리 매트릭스 보조 메모",
        "가로로 분리된 기간 밴드는 같은 행 식별자를 기준으로 이어집니다.",
        "고정 설명 열과 원거리 헤더 밴드는 한 리포트 표준 안에서 판독합니다.",
    ),
    "zoom_micro_marker_exception": (
        "미세 마커 예외 공지",
        "검수 표의 작은 코너 마커는 확대 상태에서 판독하는 주석입니다.",
        "마커 위치와 문서 내 기준은 inspection bundle 안에서 함께 보관합니다.",
    ),
}

SUPPLEMENTAL_TABLE_BY_TEMPLATE = {
    "symbol_rule_induction": (
        "마커 처리 기준",
        (
            ("마커 토큰", "원문 유지", "표기 위치와 값은 함께 보관"),
            ("미분류 행", "검수 대기", "완료 로그와 동일 문서군에서 판독"),
        ),
    ),
    "color_condition_rule_induction": (
        "서식 보존 기준",
        (
            ("패턴 셀", "보존", "시각 서식은 값과 분리해 기록"),
            ("테두리 셀", "보존", "색상 대비는 감사 원본 기준"),
        ),
    ),
    "legend_color_exception_scope": (
        "범례 적용 범위",
        (
            ("상태 범례", "유효", "우선순위 표식은 범례 문서 기준"),
            ("예외 bulletin", "동시 적용", "같은 검토 묶음 안에서만 적용"),
        ),
    ),
    "merged_header_scope": (
        "리포팅 표준",
        (
            ("상위 헤더", "유효", "기간/영역 그룹은 병합 영역 기준"),
            ("하위 지표", "유효", "교차 지점의 단위를 유지"),
        ),
    ),
    "wide_table_navigation": (
        "원장 대조 기준",
        (
            ("열 인덱스", "유효", "원장 열 묶음과 단위를 대조"),
            ("보정 열", "검토", "금액 열과 건수 열을 분리 보관"),
        ),
    ),
    "wide_table_viewport_trace": (
        "뷰포트 기록 기준",
        (
            ("캡처 로그", "유효", "표시 열 범위와 스크롤 상태 보관"),
            ("원장 화면", "대조", "현재 뷰포트와 이전 기록을 비교"),
        ),
    ),
    "merged_header_pan_scope": (
        "동결 밴드 기준",
        (
            ("고정 설명 열", "유효", "가로 이동 중 행 식별자 유지"),
            ("원거리 헤더", "대조", "같은 매트릭스의 기간 밴드로 관리"),
        ),
    ),
    "zoom_micro_marker_exception": (
        "마커 판독 기준",
        (
            ("코너 마커", "확대 판독", "작은 표식은 셀 내부 주석으로 보관"),
            ("예외 마커", "동시 검토", "위치와 색상은 inspection 기준"),
        ),
    ),
}


def _supplemental_table(template_id: str) -> tuple[str, tuple[tuple[str, str, str], tuple[str, str, str]]]:
    return SUPPLEMENTAL_TABLE_BY_TEMPLATE.get(
        template_id,
        (
            "보조 문서 기준",
            (
                ("기준 문서", "유효", "원문 표기 유지"),
                ("보조 문서", "대조", "같은 문서 묶음 기준"),
            ),
        ),
    )


def _choice_shuffle_seed(*, template_id: str, level: int, seed_slot: int) -> int:
    return 9100 + (level * 307) + (seed_slot * 53) + sum(ord(ch) for ch in template_id)


def _money_answer(value: int, *, unit_label: str = "원", choice_id: str | None = None) -> AnswerSpec:
    formatted = f"{value:,}"
    accepted = [formatted, f"{value}{unit_label}", f"{formatted}{unit_label}"]
    if choice_id is not None:
        accepted.append(choice_id)
    return AnswerSpec(
        canonical=str(value),
        accepted=tuple(accepted),
        normalizer="ko_answer",
    )


def _choice_display_value(value: int, unit_label: str) -> str:
    return f"{int(value):,}{unit_label}"


def _choice_cards_for_values(
    option_values: list[dict[str, Any]],
    *,
    unit_label: str,
) -> tuple[list[ChoiceCardSpec], str]:
    display_values = [_choice_display_value(int(item["value"]), unit_label) for item in option_values]
    if len(set(display_values)) != len(display_values):
        duplicates = sorted({value for value in display_values if display_values.count(value) > 1})
        raise ValueError(f"Answer choice display values must be unique: {duplicates}")

    correct_choice_id = next(CHOICE_IDS[index] for index, item in enumerate(option_values) if item["is_answer"])
    cards = [
        ChoiceCardSpec(choice_id, display_value, ())
        for choice_id, display_value in zip(CHOICE_IDS, display_values)
    ]
    return cards, correct_choice_id


def _unique_option_values(option_values: list[dict[str, Any]], *, unit_label: str) -> list[dict[str, Any]]:
    adjusted = [dict(item) for item in option_values]
    answer_item = next(item for item in adjusted if item["is_answer"])
    protected = {_choice_display_value(int(answer_item["value"]), unit_label)}
    used = set(protected)
    step = max(1, int(round(abs(int(answer_item["value"])) * 0.07)))

    for index, item in enumerate(adjusted):
        if item["is_answer"]:
            continue
        value = int(item["value"])
        direction = -1 if index % 2 else 1
        attempt = 0
        while _choice_display_value(value, unit_label) in used:
            attempt += 1
            value = int(item["value"]) + (direction * step * attempt)
            if value < 0:
                value = int(item["value"]) + (step * attempt)
        item["value"] = value
        used.add(_choice_display_value(value, unit_label))
    return adjusted


def _supplemental_notice(template_id: str) -> tuple[str, str, str]:
    return SUPPLEMENTAL_NOTICE_BY_TEMPLATE.get(
        template_id,
        (
            "보조 규정 공지",
            "이 문서 묶음에는 기본 문서와 함께 관리되는 보조 공지가 포함됩니다.",
            "판독 기준은 화면에 표시된 원문 문서 묶음을 따릅니다.",
        ),
    )


def _query_page(
    question: str,
    answer: int,
    distractors: tuple[int, int, int],
    *,
    level: int,
    template_id: str,
    seed_slot: int,
    lead_elements: tuple[Any, ...] = (),
    unit_label: str = "원",
):
    option_values = [
        {"value": distractors[0], "is_answer": False},
        {"value": answer, "is_answer": True},
        {"value": distractors[1], "is_answer": False},
        {"value": distractors[2], "is_answer": False},
    ]
    option_values = _unique_option_values(option_values, unit_label=unit_label)
    random.Random(_choice_shuffle_seed(template_id=template_id, level=level, seed_slot=seed_slot)).shuffle(option_values)
    cards, correct_choice_id = _choice_cards_for_values(option_values, unit_label=unit_label)
    headers, y = query_header_blocks(
        target_title="분석 요청",
        target_lines=(question,),
        guidance_title="접수 정보",
        guidance_lines=(
            f"제출 형식: {unit_label} 단위 값 또는 선택지 ID",
            "관련 문서의 표시 단위와 보정 기준을 원문 기준으로 해석합니다.",
        ),
    )
    lead_bottom = max((getattr(getattr(element, "rect", None), "y", 0.0) + getattr(getattr(element, "rect", None), "height", 0.0) for element in lead_elements), default=0.0)
    context_elements: tuple[Any, ...] = ()
    context_y = max(320.0, y + 24.0)
    context_bottom = context_y + 160.0
    if not lead_elements:
        context_elements = (
            text_block(
                "query-case-register",
                "요청 등록 정보",
                rect(84, context_y, 500, 124),
                (
                    f"요청 유형: {TEMPLATE_SPECS[template_id]['label']}",
                    "문서 묶음: 원본 표, 기준 문서, 보조 공지",
                    "응답 상태: 분석 대기",
                ),
                style="body",
                subtitle="접수 티켓",
            ),
            table_from_cells(
                "query-bundle-register",
                "문서 묶음 현황",
                rect(620, context_y, 500, 160),
                n_rows=4,
                n_cols=3,
                cells=[
                    cell(0, 0, "분류", style="header"),
                    cell(0, 1, "문서", style="header"),
                    cell(0, 2, "상태", style="header"),
                    cell(1, 0, "Primary", style="row_label", align="left"),
                    cell(1, 1, "원본 표"),
                    cell(1, 2, "활성"),
                    cell(2, 0, "Reference", style="row_label", align="left"),
                    cell(2, 1, "기준 문서"),
                    cell(2, 2, "활성"),
                    cell(3, 0, "Notice", style="row_label", align="left"),
                    cell(3, 1, "보조 공지"),
                    cell(3, 2, "검토"),
                ],
                column_weights=(0.9, 1.2, 0.8),
                row_heights=(34, 38, 38, 38),
                subtitle="요청과 함께 접수된 문서 유형만 요약합니다.",
            ),
        )
    lead_right = max(
        (
            getattr(getattr(element, "rect", None), "x", 0.0)
            + getattr(getattr(element, "rect", None), "width", 0.0)
            for element in lead_elements
        ),
        default=0.0,
    )
    query_side_panel: tuple[Any, ...] = ()
    if lead_elements and lead_right <= 850:
        query_side_panel = (
            text_block(
                "query-source-panel",
                "첨부 문서",
                rect(884, 318, 256, 150),
                (
                    f"요청 유형: {TEMPLATE_SPECS[template_id]['label']}",
                    "원본 화면과 기준 문서를 함께 검토",
                    "상태: 응답 대기",
                ),
                style="note",
            ),
        )
        choice_elements, regions = query_choice_cards(
            prefix="answer",
            cards=cards,
            answer_form="number",
            columns=1,
            width=256,
            height=54,
            gap_y=8,
            x0=884,
            y=500,
        )
    else:
        choice_y = max(y, 560.0, context_bottom + 28.0, lead_bottom + 18.0 if lead_elements else 560.0)
        choice_elements, regions = query_choice_cards(
            prefix="answer",
            cards=cards,
            answer_form="number",
            columns=4,
            width=244 if lead_elements else 258,
            height=58 if lead_elements else 102,
            gap_x=14,
            x0=84,
            y=choice_y,
        )
    pages = [page("query-p1", "질의", elements=(*headers, *context_elements, *lead_elements, *query_side_panel, *choice_elements), regions=regions)]
    if level >= 3:
        notice_title, notice_line_1, notice_line_2 = _supplemental_notice(template_id)
        table_title, rows = _supplemental_table(template_id)
        pages.append(
            page(
                "query-p2",
                notice_title,
                elements=[
                    text_block(
                        "exception-check",
                        notice_title,
                        rect(84, 176, 1080, 150),
                        (notice_line_1, notice_line_2),
                        style="note",
                    ),
                    table_from_cells(
                        "exception-application",
                        table_title,
                        rect(84, 386, 900, 170),
                        n_rows=3,
                        n_cols=3,
                        cells=[
                            cell(0, 0, "문서군", style="header"),
                            cell(0, 1, "상태", style="header"),
                            cell(0, 2, "비고", style="header"),
                            cell(1, 0, rows[0][0], style="row_label", align="left"),
                            cell(1, 1, rows[0][1]),
                            cell(1, 2, rows[0][2]),
                            cell(2, 0, rows[1][0], style="row_label", align="left"),
                            cell(2, 1, rows[1][1]),
                            cell(2, 2, rows[1][2]),
                        ],
                        column_weights=(1.0, 1.4, 0.8),
                        row_heights=(44, 46, 46),
                        subtitle="템플릿별 문서 기준을 보조 화면에 분리 보관합니다.",
                    ),
                ],
            )
        )
    return pages, correct_choice_id


def _abbrev_query_page(
    question: str,
    answer: int,
    distractors: tuple[int, int, int],
    *,
    level: int,
    template_id: str,
    seed_slot: int,
):
    option_values = [
        {"value": distractors[0], "is_answer": False},
        {"value": answer, "is_answer": True},
        {"value": distractors[1], "is_answer": False},
        {"value": distractors[2], "is_answer": False},
    ]
    option_values = _unique_option_values(option_values, unit_label="원")
    random.Random(_choice_shuffle_seed(template_id=template_id, level=level, seed_slot=seed_slot)).shuffle(option_values)
    cards, correct_choice_id = _choice_cards_for_values(option_values, unit_label="원")
    request_panel = text_block(
        "abbrev-query-request",
        "접수 케이스",
        rect(72, 164, 540, 142),
        (
            "요청 번호: ARC-OPS-KPI-2047",
            "요청 부서: 운영성과 검토팀",
            "관련 문서: 지표 현황, 지표 코드북, 예외 기준",
        ),
        style="callout",
        subtitle="운영 지표 조정 검토",
    )
    submission_panel = text_block(
        "abbrev-query-submit",
        "제출 형식",
        rect(640, 164, 500, 142),
        (
            "제출 형식: 원 단위 값 또는 선택지 ID",
            "표시 단위와 보정 규칙은 문서 내 정의를 따릅니다.",
            "선택지는 ID와 값만 표시됩니다.",
        ),
        style="note",
        subtitle="검토 상태: 접수",
    )
    target_panel = text_block(
        "abbrev-query-target",
        "산출 요청",
        rect(72, 332, 700, 126),
        (question,),
        style="body",
        subtitle="원문 문서 묶음 기준으로 산출",
    )
    reference_panel = text_block(
        "abbrev-query-reference",
        "문서 묶음",
        rect(800, 332, 340, 126),
        (
            "지표 현황 리포트",
            "운영 지표 코드북",
            "보조 규정 공지",
        ),
        style="callout",
    )
    option_heading = text_block(
        "abbrev-query-options",
        "답안 선택",
        rect(72, 492, 700, 70),
        ("아래 목록에서 제출할 값 또는 선택지 ID를 고릅니다.",),
        style="note",
    )
    case_table = table_from_cells(
        "abbrev-query-case-register",
        "접수 기록",
        rect(72, 624, 700, 134),
        n_rows=4,
        n_cols=3,
        cells=[
            cell(0, 0, "필드", style="header"),
            cell(0, 1, "값", style="header"),
            cell(0, 2, "상태", style="header"),
            cell(1, 0, "문서 그룹", style="row_label", align="left"),
            cell(1, 1, "운영 지표 조정"),
            cell(1, 2, "활성"),
            cell(2, 0, "요청 유형", style="row_label", align="left"),
            cell(2, 1, "금액 산출"),
            cell(2, 2, "검토"),
            cell(3, 0, "응답 포맷", style="row_label", align="left"),
            cell(3, 1, "KRW integer"),
            cell(3, 2, "대기"),
        ],
        column_weights=(0.82, 1.0, 1.72),
        row_heights=(34, 34, 34, 34),
        subtitle="문서 접수 및 응답 포맷 관리 정보입니다.",
    )
    choice_elements, regions = query_choice_cards(
        prefix="answer",
        cards=cards,
        answer_form="number",
        y=492,
        columns=1,
        width=300,
        height=58,
        gap_y=10,
        x0=840,
    )
    pages = [
        page(
            "query-p1",
            "업무 요청",
            elements=(
                request_panel,
                submission_panel,
                target_panel,
                reference_panel,
                option_heading,
                case_table,
                *choice_elements,
            ),
            regions=regions,
        )
    ]
    if level >= 3:
        pages.append(
            page(
                "query-p2",
                "검수 예외 기준",
                elements=[
                    text_block(
                        "abbrev-hold-policy",
                        "보조 규정 문서",
                        rect(72, 176, 1080, 136),
                        (
                            "보류 상태가 포함된 요청은 코드북의 보정 기준과 함께 검토합니다.",
                            "표시값은 원문 문서의 값을 유지하며, 산출 해석은 문서 내 정의를 따릅니다.",
                        ),
                        style="note",
                        subtitle="운영 검수 기준",
                    ),
                    table_from_cells(
                        "abbrev-hold-scope",
                        "보조 규정 상태표",
                        rect(72, 384, 930, 176),
                        n_rows=3,
                        n_cols=4,
                        cells=[
                            cell(0, 0, "상태", style="header"),
                            cell(0, 1, "문서군", style="header"),
                            cell(0, 2, "산출 기준", style="header"),
                            cell(0, 3, "비고", style="header"),
                            cell(1, 0, "HLD=Y", style="row_label", align="left"),
                            cell(1, 1, "보조 규정"),
                            cell(1, 2, "코드북 정의 참조"),
                            cell(1, 3, "표 원본값은 유지"),
                            cell(2, 0, "HLD=N", style="row_label", align="left"),
                            cell(2, 1, "기본 기준"),
                            cell(2, 2, "코드북 정의 참조"),
                            cell(2, 3, "정상 흐름"),
                        ],
                        column_weights=(0.8, 1.1, 1.25, 1.2),
                        row_heights=(46, 54, 54),
                        subtitle="보조 규정의 문서 상태와 원문 보존 기준입니다.",
                    ),
                ],
            )
        )
    return pages, correct_choice_id


def _symbol_query_pages(
    *,
    question: str,
    answer: int,
    distractors: tuple[int, int, int],
    level: int,
    template_id: str,
    seed_slot: int,
    query_examples: Any,
    query_table: Any,
) -> tuple[list[Any], str]:
    option_values = [
        {"value": distractors[0], "is_answer": False},
        {"value": answer, "is_answer": True},
        {"value": distractors[1], "is_answer": False},
        {"value": distractors[2], "is_answer": False},
    ]
    option_values = _unique_option_values(option_values, unit_label="원")
    random.Random(_choice_shuffle_seed(template_id=template_id, level=level, seed_slot=seed_slot)).shuffle(option_values)
    cards, correct_choice_id = _choice_cards_for_values(option_values, unit_label="원")
    answer_elements, regions = query_choice_cards(
        prefix="answer",
        cards=cards,
        answer_form="number",
        columns=1,
        width=252,
        height=64,
        gap_y=12,
        x0=880,
        y=296,
    )
    pages = [
        page(
            "query-p1",
            "마킹 검토 요청",
            elements=[
                text_block(
                    "symbol-query-request",
                    "마킹 샘플 로그 검토 요청",
                    rect(48, 140, 826, 96),
                    (
                        "요청 유형: 미분류 레코드 검토 · 제출 형식: 원 단위 숫자 또는 선택지 ID",
                        question,
                    ),
                    style="body",
                ),
                query_examples,
                query_table,
                text_block(
                    "symbol-answer-rail-title",
                    "답안 후보",
                    rect(880, 224, 252, 58),
                    ("선택지는 ID와 값만 표시됩니다.",),
                    style="note",
                ),
                *answer_elements,
            ],
            regions=regions,
        )
    ]
    if level >= 3:
        pages.append(
            page(
                "query-p2",
                "마커 처리 기준",
                elements=[
                    text_block(
                        "symbol-marker-policy",
                        "마커 처리 정책 메모",
                        rect(56, 140, 1040, 154),
                        (
                            "미분류 레코드는 완료 샘플과 같은 표시 체계를 유지해 검수합니다.",
                            "원문 로그의 마커 위치와 값 표기는 산출 전 단계에서 변경하지 않습니다.",
                            "보조 정책은 누락된 처리값을 직접 제공하지 않고 판독 기준만 보관합니다.",
                        ),
                        style="note",
                    ),
                    table_from_cells(
                        "symbol-marker-policy-table",
                        "마커 처리 기준",
                        rect(56, 374, 900, 178),
                        n_rows=3,
                        n_cols=3,
                        cells=[
                            cell(0, 0, "항목", style="header"),
                            cell(0, 1, "보존 방식", style="header"),
                            cell(0, 2, "문서 메모", style="header"),
                            cell(1, 0, "마커 토큰", style="row_label", align="left"),
                            cell(1, 1, "원문 표시 유지"),
                            cell(1, 2, "값과 함께 판독"),
                            cell(2, 0, "무표식 값", style="row_label", align="left"),
                            cell(2, 1, "원문값 유지"),
                            cell(2, 2, "별도 표식 없음"),
                        ],
                        column_weights=(0.9, 1.3, 1.5),
                        row_heights=(48, 56, 56),
                        subtitle="검수 메모는 표시 보존 기준만 제공합니다.",
                    ),
                    text_block(
                        "symbol-policy-note",
                        "문서 표시 기준",
                        rect(56, 622, 1040, 104),
                        (
                            "검수 표의 마커는 원문 레코드에 남아 있는 시각 상태입니다.",
                            "샘플 로그와 미분류 레코드는 같은 문서 묶음의 표시 규칙을 사용합니다.",
                            "문서 메모는 표시 보존과 검수 기준만 기록합니다.",
                        ),
                        style="body",
                    ),
                ],
            )
        )
    return pages, correct_choice_id


def _symbol_episode(manifest: TemplateManifest, seed_slot: int):
    rng = random.Random(seed_slot + 1300 + manifest.level)
    a = 8 + rng.randint(0, 4)
    b = 5 + rng.randint(0, 3)
    multiplier = 2 + (manifest.level >= 2)
    bonus = 4 if manifest.level >= 3 else 0
    answer = (a * multiplier) + (b * multiplier) + bonus
    examples = table_from_cells(
        "symbol-examples",
        "완성 샘플",
        rect(48, 170, 760, 340),
        n_rows=4,
        n_cols=4,
        cells=[
            cell(0, 0, "항목", style="header"),
            cell(0, 1, "A", style="header"),
            cell(0, 2, "B", style="header"),
            cell(0, 3, "합계", style="header"),
            cell(1, 0, "가", style="row_label", align="left"),
            cell(1, 1, "10★"),
            cell(1, 2, "5"),
            cell(1, 3, str(10 * multiplier + 5), style="total"),
            cell(2, 0, "나", style="row_label", align="left"),
            cell(2, 1, "7"),
            cell(2, 2, "3★"),
            cell(2, 3, str(7 + 3 * multiplier), style="total"),
            cell(3, 0, "다", style="row_label", align="left"),
            cell(3, 1, "6★"),
            cell(3, 2, "2★"),
            cell(3, 3, str(8 * multiplier), style="total"),
        ],
        column_weights=(1.1, 1.0, 1.0, 1.1),
        row_heights=(64, 86, 86, 86),
        subtitle="문서 유형: 샘플 로그 · 기준 단위: 원 · 페이지 1/1",
    )
    rule_note = text_block(
        "symbol-level-note",
        "검사 메모",
        rect(840, 170, 280, 292),
        (
            "표기된 마커는 원문 로그의 시각 표시를 유지합니다.",
            "합계 열은 원문 기준으로 표시됩니다.",
            "빈 마커는 별도 처리 규정 없이 원문값으로 유지됩니다.",
            "보조 정책이 있는 문서는 같은 묶음 안에서 관리됩니다." if manifest.level >= 3 else "검수 표시는 샘플 로그 단위로 보관됩니다.",
        ),
        style="note",
    )
    examples_note = text_block(
        "symbol-examples-display-note",
        "문서 표시 기준",
        rect(48, 542, 1072, 156),
        (
            "표기된 마커는 원문 로그의 시각 표시를 유지합니다.",
            "합계 열은 원문 기준으로 표시됩니다.",
            "빈 마커는 별도 처리 규정 없이 원문값으로 유지됩니다.",
            "검수 기록은 행 단위로 보관되며 표시 단위는 원입니다.",
            "샘플 행은 완료된 레코드만 발췌해 보여줍니다.",
        ),
        style="body",
    )
    query_examples = table_from_cells(
        "symbol-query-completed-examples",
        "완성 샘플 로그",
        rect(48, 314, 826, 224),
        n_rows=4,
        n_cols=4,
        cells=[
            cell(0, 0, "항목", style="header"),
            cell(0, 1, "A", style="header"),
            cell(0, 2, "B", style="header"),
            cell(0, 3, "합계", style="header"),
            cell(1, 0, "가", style="row_label", align="left"),
            cell(1, 1, "10★"),
            cell(1, 2, "5"),
            cell(1, 3, str(10 * multiplier + 5), style="total"),
            cell(2, 0, "나", style="row_label", align="left"),
            cell(2, 1, "7"),
            cell(2, 2, "3★"),
            cell(2, 3, str(7 + 3 * multiplier), style="total"),
            cell(3, 0, "다", style="row_label", align="left"),
            cell(3, 1, "6★"),
            cell(3, 2, "2★"),
            cell(3, 3, str(8 * multiplier), style="total"),
        ],
        column_weights=(1.1, 1.0, 1.0, 1.1),
        row_heights=(52, 56, 56, 56),
        subtitle="완료된 처리 이력이 남아 있는 샘플 레코드입니다.",
    )
    query_table = table_from_cells(
        "symbol-query",
        "미분류 레코드",
        rect(48, 596, 826, 130),
        n_rows=2,
        n_cols=4,
        cells=[
            cell(0, 0, "항목", style="header"),
            cell(0, 1, "A", style="header"),
            cell(0, 2, "B", style="header"),
            cell(0, 3, "합계", style="header"),
            cell(1, 0, "검토", style="row_label", align="left"),
            cell(1, 1, f"{a}★"),
            cell(1, 2, f"{b}★"),
            cell(1, 3, "?"),
        ],
        row_heights=(58, 62),
        subtitle="아직 산출값이 비어 있는 레코드입니다.",
    )
    question = "마킹 샘플 로그 기준으로 미분류 레코드의 합계는 원 단위로 얼마인가?"
    query_pages, correct_choice_id = _symbol_query_pages(
        question=question,
        answer=answer,
        distractors=(answer - 3, answer - bonus, answer + 7),
        level=manifest.level,
        template_id=manifest.template_id,
        seed_slot=seed_slot,
        query_examples=query_examples,
        query_table=query_table,
    )
    return episode(
        manifest=manifest,
        family_display_name=FAMILY_LABEL,
        question=question,
        workbook_title="검사 코드 매핑 로그",
        sheets=[
            sheet("examples", "예시", [page("examples-p1", "검사 코드 매핑 로그", elements=[examples, rule_note, examples_note])]),
            sheet("query", "질의", query_pages),
        ],
        answer=_money_answer(answer, choice_id=correct_choice_id),
        seed_slot=seed_slot,
        metadata_extra={"hidden_program": "sum(marked_values * symbol_multiplier) + level3_exception_bonus"},
    )


def _merged_episode(manifest: TemplateManifest, seed_slot: int):
    rng = random.Random(seed_slot + 2300 + manifest.level)
    current = 12.4 + rng.randint(0, 4) / 10
    previous = 10.9 + rng.randint(0, 4) / 10
    answer = int(round((current - previous) * 10))
    table = table_from_cells(
        "merged-scope",
        "권역·채널 병합 헤더",
        rect(70, 190, 1120, 282),
        n_rows=5,
        n_cols=7,
        cells=[
            cell(0, 0, "기간", row_span=2, style="header"),
            cell(0, 1, "2024 하반기", col_span=3, style="header"),
            cell(0, 4, "2025 상반기", col_span=3, style="header"),
            cell(1, 1, "수도권 소매"),
            cell(1, 2, "수도권 B2B"),
            cell(1, 3, "비수도권 소매"),
            cell(1, 4, "수도권 소매"),
            cell(1, 5, "수도권 B2B"),
            cell(1, 6, "비수도권 소매"),
            cell(2, 0, "매출", style="row_label", align="left"),
            cell(2, 1, "81.2"),
            cell(2, 2, "64.0"),
            cell(2, 3, "42.5"),
            cell(2, 4, "88.0"),
            cell(2, 5, "69.1"),
            cell(2, 6, "45.8"),
            cell(3, 0, "반품률", style="row_label", align="left"),
            cell(3, 1, f"{previous:.1f}%"),
            cell(3, 2, "9.4%"),
            cell(3, 3, "8.8%"),
            cell(3, 4, f"{current:.1f}%"),
            cell(3, 5, "10.1%"),
            cell(3, 6, "9.0%"),
            cell(4, 0, "정산", style="row_label", align="left"),
            cell(4, 1, "완료"),
            cell(4, 2, "검토"),
            cell(4, 3, "완료"),
            cell(4, 4, "완료"),
            cell(4, 5, "검토"),
            cell(4, 6, "완료"),
        ],
        column_weights=(1.25, 1, 1, 1, 1, 1, 1),
        row_heights=(42, 40, 48, 48, 48),
        subtitle="상위 기간 그룹과 하위 채널 그룹이 결합된 운영 매트릭스입니다.",
    )
    note_panel = text_block(
        "scope-note",
        "%p 계산 안내",
        rect(94, 210, 1000, 140),
        ("반품률 차이는 퍼센트포인트로 계산합니다.", "예: 12.3%와 10.1%의 차이는 2.2%p입니다."),
        style="note",
    )
    question = "2025년 상반기 수도권 소매 부문의 반품률은 2024년 하반기 같은 범위보다 몇 %p 증가했는가? 소수 첫째 자리 값에 10을 곱한 정수로 제출하라."
    query_pages, correct_choice_id = _query_page(
        question,
        answer,
        (answer + 10, answer - 2, answer + 3),
        level=manifest.level,
        template_id=manifest.template_id,
        seed_slot=seed_slot,
        unit_label="점",
    )
    return episode(
        manifest=manifest,
        family_display_name=FAMILY_LABEL,
        question=question,
        workbook_title="운영 성과 매트릭스 검토",
        sheets=[
            sheet("examples", "매트릭스", [page("examples-p1", "채널 성과 매트릭스", elements=[table])]),
            sheet("notes", "기준메모", [page("notes-p1", "Calculation Note", elements=[note_panel])]),
            sheet("query", "질의", query_pages),
        ],
        answer=_money_answer(answer, unit_label="점", choice_id=correct_choice_id),
        seed_slot=seed_slot,
        metadata_extra={"hidden_program": "round((current_percent - previous_percent) * 10)"},
    )


def _abbrev_episode(manifest: TemplateManifest, seed_slot: int):
    rng = random.Random(seed_slot + 3300 + manifest.level)
    tca = 1200 + rng.randint(0, 9) * 50
    kadj = 108 + rng.randint(0, 5)
    r2n = 6.5 + rng.randint(0, 9) / 10
    margin_delta = -4 + rng.randint(0, 6)
    hold_flag = "Y" if manifest.level >= 3 else "N"
    effective_kadj = min(kadj, 106) if hold_flag == "Y" else kadj
    base_amount = tca * 1000
    if manifest.level >= 2:
        base_amount += margin_delta * 10000
    answer = int(round(base_amount * (effective_kadj / 100)))
    main = table_from_cells(
        "abbrev-main",
        "지점별 조정 지표 현황",
        rect(48, 176, 1024, 374),
        n_rows=7,
        n_cols=7,
        cells=[
            cell(0, 0, "지점", style="header"),
            cell(0, 1, "TCA", style="header"),
            cell(0, 2, "R2N", style="header"),
            cell(0, 3, "M-Adj", style="header"),
            cell(0, 4, "K-Adj", style="header"),
            cell(0, 5, "HLD", style="header"),
            cell(0, 6, "군집", style="header"),
            cell(1, 0, "서울A", style="row_label", align="left"),
            cell(1, 1, str(tca), style="numeric"),
            cell(1, 2, f"{r2n:.1f}", style="numeric"),
            cell(1, 3, str(margin_delta), style="numeric"),
            cell(1, 4, f"{kadj}", style="numeric"),
            cell(1, 5, hold_flag, style="negative" if hold_flag == "Y" else "body"),
            cell(1, 6, "북부", align="left"),
            cell(2, 0, "부산B", style="row_label", align="left"),
            cell(2, 1, str(tca - 160), style="numeric"),
            cell(2, 2, "7.6", style="numeric"),
            cell(2, 3, "-2.1", style="numeric"),
            cell(2, 4, "104", style="numeric"),
            cell(2, 5, "N"),
            cell(2, 6, "남부", align="left"),
            cell(3, 0, "대전C", style="row_label", align="left"),
            cell(3, 1, str(tca + 90), style="numeric"),
            cell(3, 2, "6.8", style="numeric"),
            cell(3, 3, "1.5", style="numeric"),
            cell(3, 4, "101", style="numeric"),
            cell(3, 5, "N"),
            cell(3, 6, "중부", align="left"),
            cell(4, 0, "서울D", style="row_label", align="left"),
            cell(4, 1, str(tca + 20), style="numeric"),
            cell(4, 2, f"{r2n + 0.3:.1f}", style="numeric"),
            cell(4, 3, str(margin_delta - 1), style="numeric"),
            cell(4, 4, str(kadj - 2), style="numeric"),
            cell(4, 5, "Y", style="negative"),
            cell(4, 6, "북부", align="left"),
            cell(5, 0, "광주E", style="row_label", align="left"),
            cell(5, 1, str(tca - 240), style="numeric"),
            cell(5, 2, "8.4", style="numeric"),
            cell(5, 3, "2", style="numeric"),
            cell(5, 4, "103", style="numeric"),
            cell(5, 5, "N"),
            cell(5, 6, "서남", align="left"),
            cell(6, 0, "원주F", style="row_label", align="left"),
            cell(6, 1, str(tca + 140), style="numeric"),
            cell(6, 2, "6.9", style="numeric"),
            cell(6, 3, "-3", style="numeric"),
            cell(6, 4, str(kadj), style="numeric"),
            cell(6, 5, "N"),
            cell(6, 6, "중부", align="left"),
        ],
        column_weights=(1.2, 0.95, 0.8, 0.8, 0.9, 0.75, 0.9),
        row_heights=(50, 52, 52, 52, 52, 52, 52),
        subtitle="문서 2025-Q2 · 지점 조정 리포트 · 페이지 1/1 · TCA: 천 원 · M-Adj: 만 원 · K-Adj: 표시값/100 · HLD: 검수 보류",
    )
    main_unit_note = text_block(
        "abbrev-main-unit-note",
        "단위 기준",
        rect(48, 592, 496, 92),
        ("금액 계열은 코드북의 표시 단위를 기준으로 해석합니다.", "상태값은 원문 표기 그대로 유지됩니다."),
        style="note",
    )
    main_revision_note = text_block(
        "abbrev-main-revision-note",
        "문서 기록",
        rect(576, 592, 496, 92),
        ("자료 기준일: 2025-Q2 마감 리포트", "행 순서와 지점명은 운영 원장 원문 순서를 유지합니다."),
        style="body",
    )
    glossary = table_from_cells(
        "glossary",
        "지표 코드북 / 산식 기준표",
        rect(48, 176, 1024, 410),
        n_rows=7,
        n_cols=6,
        cells=[
            cell(0, 0, "코드", style="header"),
            cell(0, 1, "의미", style="header"),
            cell(0, 2, "적용 위치", style="header"),
            cell(0, 3, "단위/스케일", style="header"),
            cell(0, 4, "계산 규칙", style="header"),
            cell(0, 5, "비고", style="header"),
            cell(1, 0, "TCA", style="row_label"),
            cell(1, 1, "총계약조정액", align="left"),
            cell(1, 2, "메인 표 금액 열", align="left"),
            cell(1, 3, "천 원", style="accent"),
            cell(1, 4, "원화값은 표시값 × 1,000", align="left"),
            cell(1, 5, "기초 금액", align="left"),
            cell(2, 0, "R2N", style="row_label"),
            cell(2, 1, "재방문 순전환율", align="left"),
            cell(2, 2, "참고 지표", align="left"),
            cell(2, 3, "백분율", style="accent"),
            cell(2, 4, "본 산출식에는 직접 반영하지 않음", align="left"),
            cell(2, 5, "행 상태 판별용", align="left"),
            cell(3, 0, "M-Adj", style="row_label"),
            cell(3, 1, "전월 대비 마진 변화", align="left"),
            cell(3, 2, "확장 산식", align="left"),
            cell(3, 3, "만 원", style="accent"),
            cell(3, 4, "TCA 원화값에 더한 뒤 보정", align="left"),
            cell(3, 5, "음수 허용", align="left"),
            cell(4, 0, "K-Adj", style="row_label"),
            cell(4, 1, "권역 보정계수", align="left"),
            cell(4, 2, "최종 보정", align="left"),
            cell(4, 3, "표시값/100", style="accent"),
            cell(4, 4, "금액에 계수를 곱함", align="left"),
            cell(4, 5, "소수 반올림", align="left"),
            cell(5, 0, "HLD", style="row_label"),
            cell(5, 1, "검수 보류 상태", align="left"),
            cell(5, 2, "보조 규정", align="left"),
            cell(5, 3, "Y/N", style="accent"),
            cell(5, 4, "Y이면 K-Adj는 106 상한", align="left"),
            cell(5, 5, "원본값 유지", align="left"),
            cell(6, 0, "군집", style="row_label"),
            cell(6, 1, "지점 묶음", align="left"),
            cell(6, 2, "행 구분", align="left"),
            cell(6, 3, "텍스트", style="accent"),
            cell(6, 4, "같은 도시명도 군집이 다르면 별도 행", align="left"),
            cell(6, 5, "중복명 구분", align="left"),
        ],
        column_weights=(0.58, 1.0, 1.0, 0.88, 2.25, 0.94),
        row_heights=(50, 58, 58, 64, 60, 64, 58),
        subtitle="코드북 v3.2 · 적용 범위: 지점별 조정 지표 리포트 · 코드 의미, 단위, 계산 위치를 분리해 확인합니다.",
    )
    glossary_revision_note = text_block(
        "abbrev-glossary-revision-note",
        "문서 사용 기준",
        rect(48, 624, 1024, 86),
        ("표시값은 원본 리포트의 셀 값을 바꾸지 않고 산출 단계에서 변환합니다.", "같은 코드가 여러 화면에 나타나면 코드북의 단위/스케일 정의를 우선합니다."),
        style="note",
    )
    if manifest.level == 1:
        question = "서울A 지점의 총계약조정액에 권역 보정계수를 반영한 금액은 원 단위로 얼마인가?"
    elif manifest.level == 2:
        question = "서울A 지점의 TCA 원화값에 M-Adj 조정을 더한 뒤 K-Adj를 반영한 금액은 원 단위로 얼마인가?"
    else:
        question = "서울A 지점의 HLD 상태와 약어 문서의 보조 규정까지 반영한 최종 조정 금액을 원 단위로 구하라."
    distractors = {
        1: (tca * 1000, answer + 60000, answer - 50000),
        2: (tca * 1000, int(round((tca * 1000) * (kadj / 100))), answer + 80000),
        3: (tca * 1000, int(round((tca * 1000 + margin_delta * 10000) * (kadj / 100))), answer + 80000),
    }[manifest.level]
    query_pages, correct_choice_id = _abbrev_query_page(
        question,
        answer,
        distractors,
        level=manifest.level,
        template_id=manifest.template_id,
        seed_slot=seed_slot,
    )
    return episode(
        manifest=manifest,
        family_display_name=FAMILY_LABEL,
        question=question,
        workbook_title="운영 분석 리포트 탐색",
        sheets=[
            sheet("query", "질의", query_pages),
            sheet("main", "메인 표", [page("main-p1", "지표 현황", elements=[main, main_unit_note, main_revision_note])]),
            sheet("glossary", "약어 문서", [page("glossary-p1", "지표 코드북", elements=[glossary, glossary_revision_note])]),
        ],
        answer=_money_answer(answer, choice_id=correct_choice_id),
        seed_slot=seed_slot,
        metadata_extra={
            "hidden_program": "(TCA * 1000 + MDelta * 10000) * (min(KAdj, 106) / 100 when HLD=Y else KAdj / 100)",
            "shortcut_traps": ["ignore_mdelta", "ignore_hld_cap", "use_same_city_distractor"],
        },
    )


def _wide_episode(manifest: TemplateManifest, seed_slot: int):
    rng = random.Random(seed_slot + 4300 + manifest.level)
    new_contract = 4200 + rng.randint(0, 8) * 100
    refund = 650 + rng.randint(0, 5) * 50
    review_hold = 120 if manifest.level >= 3 else 0
    target_c44 = new_contract + (90 if manifest.level >= 2 else 0)
    target_c52 = refund + review_hold
    answer = (target_c44 - target_c52) * 1000
    directory_table = table_from_cells(
        "wide-directory",
        "50+ 열 묶음 안내",
        rect(74, 204, 1040, 316),
        n_rows=6,
        n_cols=4,
        cells=[
            cell(0, 0, "열 범위", style="header"),
            cell(0, 1, "묶음", style="header"),
            cell(0, 2, "단위", style="header"),
            cell(0, 3, "주의", style="header"),
            cell(1, 0, "C01-C16", style="row_label"),
            cell(1, 1, "2024 가입/해지 기본값"),
            cell(1, 2, "건/천원 혼합"),
            cell(1, 3, "금액과 건수를 구분"),
            cell(2, 0, "C17-C32", style="row_label"),
            cell(2, 1, "2024 분기별 신규 계약"),
            cell(2, 2, "천원"),
            cell(2, 3, "C21은 건수, C22는 금액"),
            cell(3, 0, "C33-C44", style="row_label"),
            cell(3, 1, "2025 확정 계약 조정"),
            cell(3, 2, "천원"),
            cell(3, 3, "조정신규 금액 열"),
            cell(4, 0, "C45-C52", style="row_label"),
            cell(4, 1, "2025 환급/보류 조정"),
            cell(4, 2, "천원"),
            cell(4, 3, "보류 조정분 포함 가능"),
            cell(5, 0, "C53-C60", style="row_label"),
            cell(5, 1, "잔액/검산 열"),
            cell(5, 2, "천원"),
            cell(5, 3, "정답 열이 아님"),
        ],
        column_weights=(0.9, 1.6, 0.9, 2.2),
        row_heights=(42, 46, 46, 46, 46, 46),
        subtitle="같은 분기라도 금액 열과 건수 열이 섞여 있습니다.",
    )
    headers = [
        "행",
        "권역",
        "채널",
        "상태",
        "C12 신규액",
        "C13 신규건",
        "C21 신규건",
        "C22 신규액",
        "C33 계약건",
        "C39 환급액",
        "C40 환급건",
        "C41 보류건",
        "C44 조정신규",
        "C48 잔액",
        "C52 보정환급",
        "C53 보정잔액",
    ]
    cells = [cell(0, col, header, style="header") for col, header in enumerate(headers)]
    rows = [
        ("01", "수도권", "B2C", "확정", new_contract - 500, "21", "18", new_contract - 420, "20", refund + 100, "4", "0", new_contract - 260, "9100", refund + 140, "8840"),
        ("02", "부산권", "B2B", "확정", new_contract, "18", "17", new_contract + 70, "19", refund, "3", "1", target_c44, "8700", target_c52, str(target_c44 - target_c52)),
        ("03", "부산권", "B2C", "확정", new_contract + 250, "25", "24", new_contract + 180, "26", refund + 80, "5", "0", target_c44 + 210, "8820", target_c52 + 70, "8960"),
        ("04", "충청권", "B2B", "확정", new_contract - 300, "16", "15", new_contract - 220, "17", refund - 50, "2", "0", target_c44 - 330, "7900", target_c52 - 40, "8010"),
        ("05", "부산권", "B2B", "검토", new_contract + 40, "20", "21", new_contract + 110, "22", refund + 20, "3", "2", target_c44 + 50, "8660", target_c52 + 140, "8570"),
        ("06", "수도권", "B2B", "확정", new_contract - 180, "14", "16", new_contract - 120, "15", refund + 40, "3", "0", target_c44 - 190, "8150", target_c52 + 20, "8080"),
        ("07", "부산권", "B2B", "확정", new_contract - 90, "18", "18", new_contract + 30, "18", refund + 60, "4", "0", target_c44 - 120, "8610", target_c52 + 60, "8430"),
    ]
    for row_index, row in enumerate(rows, start=1):
        for col_index, value in enumerate(row):
            style = "row_label" if col_index in {1, 2, 3} else "body"
            cells.append(cell(row_index, col_index, str(value), style=style, align="left" if col_index in {1, 2, 3} else "center"))
    wide = table_from_cells(
        "wide-table",
        "60열 계약 조정 원장",
        rect(56, 176, 2100, 430),
        n_rows=8,
        n_cols=len(headers),
        cells=cells,
        column_weights=(0.5, 0.8, 0.75, 0.75, 1.25, 1.0, 1.0, 1.25, 1.0, 1.15, 1.0, 1.0, 1.55, 1.15, 1.45, 1.2),
        row_heights=(56, 46, 46, 46, 46, 46, 46, 46),
        subtitle="가로로 긴 원장 일부를 보는 화면이며 열 묶음과 단위가 혼재합니다.",
    )
    question = "상태가 확정인 부산권 B2B 행 중 첫 번째 대상 행에서 C44 신규계약조정액과 C52 보정환급액의 차이를 원 단위로 구하라."
    query_pages, correct_choice_id = _query_page(
        question,
        answer,
        ((target_c44 + target_c52) * 1000, target_c44 - target_c52, answer + 200000),
        level=manifest.level,
        template_id=manifest.template_id,
        seed_slot=seed_slot,
    )
    wide_page = PageSpec(
        page_id="wide-p1",
        title="Data Warehouse Grid",
        width=2260,
        height=900,
        elements=(wide,),
        regions=(),
        notes=(),
        metadata={
            "wide_table": True,
            "declared_column_count": 60,
            "initial_view": {"zoom_index": 2, "center_x": 565.0, "center_y": 506.0},
        },
    )
    required_navigation = dict(manifest.required_navigation)
    if manifest.level >= 2:
        required_navigation["required_viewport_states"] = [
            {
                "state_id": "wide-right-target-columns",
                "sheet_id": "wide",
                "page_id": "wide-p1",
                "min_zoom_index": 2,
                "required_action_types": ["pan_right", "pan_right", "pan_right", "pan_right"],
                "match": "viewbox_intersects_target",
                "target_rects": [
                    {"target_id": "c44-target", "kind": "column", "rect": {"x": 1640, "y": 176, "width": 190, "height": 430}},
                    {"target_id": "c52-target", "kind": "column", "rect": {"x": 1940, "y": 176, "width": 180, "height": 430}},
                ],
            }
        ]
        required_navigation["forbidden_shortcuts"] = [
            *required_navigation.get("forbidden_shortcuts", []),
            "initial_viewport_only",
            "no_pan_zoom",
            "wrong_similar_column",
        ]
    return episode(
        manifest=manifest,
        family_display_name=FAMILY_LABEL,
        question=question,
        workbook_title="계약 조정 원장 탐색",
        sheets=[
            sheet("directory", "인덱스", [page("directory-p1", "문서/테이블 인덱스", elements=[directory_table])]),
            sheet("wide", "원장", [wide_page]),
            sheet("query", "질의", query_pages),
        ],
        answer=_money_answer(answer, choice_id=correct_choice_id),
        seed_slot=seed_slot,
        metadata_extra={
            "hidden_program": "(C44_new_contract_adjusted - C52_adjusted_refund) * 1000 for first confirmed Busan B2B row",
            "declared_column_count": 60,
            "required_navigation": required_navigation,
        },
    )


def _striped_cell(row: int, col: int, text: str, *, style: str = "body"):
    return cell(
        row,
        col,
        text,
        style=style,
        metadata={"pattern": {"kind": "diagonal_stripe", "color": "#1d7a8c", "opacity": 0.62}},
    )


def _framed_cell(row: int, col: int, text: str, *, style: str = "body", color: str = "#2d6a4f"):
    return cell(row, col, text, style=style, metadata={"frame": {"color": color, "stroke_width": 2.4}})


def _color_condition_episode(manifest: TemplateManifest, seed_slot: int):
    rng = random.Random(seed_slot + 5300 + manifest.level)
    values = [rng.randint(10, 19), rng.randint(12, 22), rng.randint(14, 24), rng.randint(16, 26)]
    if manifest.level == 1:
        answer = 2
        rule_line = "사선 패턴이 있는 셀만 포함합니다."
    elif manifest.level == 2:
        answer = 3
        rule_line = "사선 패턴 또는 초록 테두리 셀을 포함합니다."
    else:
        answer = 2
        rule_line = "사선 패턴 또는 초록 테두리 셀을 포함하되 빨간 테두리는 제외합니다."
    examples = table_from_cells(
        "color-rule-examples",
        "조건부 서식 감사 샘플",
        rect(72, 190, 1080, 286),
        n_rows=5,
        n_cols=5,
        cells=[
            cell(0, 0, "행", style="header"),
            cell(0, 1, "상태칸", style="header"),
            cell(0, 2, "보조칸", style="header"),
            cell(0, 3, "점수", style="header"),
            cell(0, 4, "포함", style="header"),
            cell(1, 0, "예시1", style="row_label", align="left"),
            _striped_cell(1, 1, "완료"),
            cell(1, 2, "보통"),
            cell(1, 3, "18"),
            cell(1, 4, "예", style="total"),
            cell(2, 0, "예시2", style="row_label", align="left"),
            _framed_cell(2, 1, "대기"),
            cell(2, 2, "보통"),
            cell(2, 3, "16"),
            cell(2, 4, "예" if manifest.level >= 2 else "아니오", style="total" if manifest.level >= 2 else "body"),
            cell(3, 0, "예시3", style="row_label", align="left"),
            cell(3, 1, "완료"),
            cell(3, 2, "보통"),
            cell(3, 3, "21"),
            cell(3, 4, "아니오"),
            cell(4, 0, "예시4", style="row_label", align="left"),
            _framed_cell(4, 1, "검토", color="#b3261e"),
            _striped_cell(4, 2, "보조"),
            cell(4, 3, "20"),
            cell(4, 4, "아니오" if manifest.level >= 3 else "예", style="negative" if manifest.level >= 3 else "total"),
        ],
        column_weights=(0.8, 1.2, 1.1, 0.75, 0.75),
        row_heights=(44, 48, 48, 48, 48),
        subtitle="셀 패턴과 테두리 상태가 남아 있는 감사 샘플입니다.",
    )
    note_panel = text_block(
        "color-rule-note",
        "감사 메모",
        rect(76, 520, 900, 116),
        (rule_line, "미분류 표는 같은 문서 묶음의 시각 기준으로 판독합니다."),
        style="note",
    )
    query_cells = [
        cell(0, 0, "대상", style="header"),
        cell(0, 1, "상태칸", style="header"),
        cell(0, 2, "보조칸", style="header"),
        cell(0, 3, "값", style="header"),
        cell(1, 0, "Q1", style="row_label", align="left"),
        _striped_cell(1, 1, "완료"),
        cell(1, 2, "일반"),
        cell(1, 3, str(values[0])),
        cell(2, 0, "Q2", style="row_label", align="left"),
        _framed_cell(2, 1, "대기"),
        cell(2, 2, "일반"),
        cell(2, 3, str(values[1])),
        cell(3, 0, "Q3", style="row_label", align="left"),
        _framed_cell(3, 1, "검토", color="#b3261e"),
        _striped_cell(3, 2, "보조"),
        cell(3, 3, str(values[2])),
        cell(4, 0, "Q4", style="row_label", align="left"),
        cell(4, 1, "완료"),
        cell(4, 2, "일반"),
        cell(4, 3, str(values[3])),
    ]
    query_table = table_from_cells(
        "color-query",
        "미분류 조건부 서식 결과",
        rect(84, 348, 920, 260),
        n_rows=5,
        n_cols=4,
        cells=query_cells,
        column_weights=(0.75, 1.15, 1.15, 0.8),
        row_heights=(44, 48, 48, 48, 48),
        subtitle="포함 여부 열은 비어 있고 시각 표식만 남아 있습니다.",
    )
    question = "완성 예시의 시각 조건 규칙을 질의 표에 적용하면 포함 대상은 몇 개인가?"
    query_pages, correct_choice_id = _query_page(
        question,
        answer,
        (answer - 1, answer + 1, 4),
        level=manifest.level,
        template_id=manifest.template_id,
        seed_slot=seed_slot,
        lead_elements=(query_table,),
        unit_label="개",
    )
    return episode(
        manifest=manifest,
        family_display_name=FAMILY_LABEL,
        question=question,
        workbook_title="조건부 서식 감사 리포트",
        sheets=[
            sheet("examples", "감사샘플", [page("examples-p1", "서식 감사 샘플", elements=[examples, note_panel])]),
            sheet("query", "질의", query_pages),
        ],
        answer=_money_answer(answer, unit_label="개", choice_id=correct_choice_id),
        seed_slot=seed_slot,
        metadata_extra={"hidden_program": "count rows matching induced visual pattern/frame rule"},
    )


def _legend_color_exception_episode(manifest: TemplateManifest, seed_slot: int):
    rng = random.Random(seed_slot + 6300 + manifest.level)
    base_rows = 5 + (manifest.level >= 2)
    exception_applies = manifest.level >= 3
    answer = 3 if not exception_applies else 2
    legend_table = table_from_cells(
        "color-legend",
        "범례: 색상과 테두리의 우선순위",
        rect(78, 196, 1040, 300),
        n_rows=5,
        n_cols=4,
        cells=[
            cell(0, 0, "표식", style="header"),
            cell(0, 1, "의미", style="header"),
            cell(0, 2, "처리", style="header"),
            cell(0, 3, "우선순위", style="header"),
            _striped_cell(1, 0, ""),
            cell(1, 1, "사선 패턴"),
            cell(1, 2, "검토 대상"),
            cell(1, 3, "2"),
            _framed_cell(2, 0, ""),
            cell(2, 1, "초록 테두리"),
            cell(2, 2, "검토 대상"),
            cell(2, 3, "2"),
            _framed_cell(3, 0, "", color="#b3261e"),
            cell(3, 1, "빨간 테두리"),
            cell(3, 2, "우선 제외 조건"),
            cell(3, 3, "1"),
            cell(4, 0, "무표식"),
            cell(4, 1, "일반 상태"),
            cell(4, 2, "제외"),
            cell(4, 3, "3"),
        ],
        column_weights=(0.8, 1.2, 1.5, 0.8),
        row_heights=(44, 52, 52, 52, 52),
        subtitle="숫자나 텍스트 상태보다 표식 우선순위가 먼저 적용됩니다.",
    )
    rows = [
        ("청구A", "완료", "15", "stripe"),
        ("청구B", "대기", "12", "green"),
        ("청구C", "완료", "17", "plain"),
        ("청구D", "검토", "19", "redstripe"),
        ("청구E", "대기", "11", "plain"),
        ("청구F", "완료", str(10 + rng.randint(0, 3)), "stripe"),
    ][:base_rows]
    cells = [cell(0, 0, "항목", style="header"), cell(0, 1, "상태", style="header"), cell(0, 2, "값", style="header"), cell(0, 3, "표식칸", style="header")]
    for row_index, (name, status, value, marker) in enumerate(rows, start=1):
        cells.extend([cell(row_index, 0, name, style="row_label", align="left"), cell(row_index, 1, status), cell(row_index, 2, value)])
        if marker == "stripe":
            cells.append(_striped_cell(row_index, 3, ""))
        elif marker == "green":
            cells.append(_framed_cell(row_index, 3, ""))
        elif marker == "redstripe":
            cells.append(
                cell(
                    row_index,
                    3,
                    "",
                    metadata={
                        "pattern": {"kind": "diagonal_stripe", "color": "#1d7a8c", "opacity": 0.62},
                        "frame": {"color": "#b3261e", "stroke_width": 2.4},
                    },
                )
            )
        else:
            cells.append(cell(row_index, 3, ""))
    query_table = table_from_cells(
        "legend-query-table",
        "질의 표: 범례 적용 대상",
        rect(84, 340, 900, 310),
        n_rows=1 + len(rows),
        n_cols=4,
        cells=cells,
        column_weights=(1.2, 0.9, 0.75, 1.0),
        row_heights=(44,) + tuple(46 for _ in rows),
        subtitle="범례의 우선순위를 적용해 검토 대상을 셉니다.",
    )
    question = "범례의 색상·패턴·테두리 우선순위를 질의 표에 적용하면 검토 대상은 몇 개인가?"
    query_pages, correct_choice_id = _query_page(
        question,
        answer,
        (answer + 1, base_rows, max(answer - 1, 0)),
        level=manifest.level,
        template_id=manifest.template_id,
        seed_slot=seed_slot,
        lead_elements=(query_table,),
        unit_label="개",
    )
    return episode(
        manifest=manifest,
        family_display_name=FAMILY_LABEL,
        question=question,
        workbook_title="상태 코드 범례 검토",
        sheets=[
            sheet("legend", "범례", [page("legend-p1", "상태 코드 범례", elements=[legend_table])]),
            sheet("query", "질의", query_pages),
        ],
        answer=_money_answer(answer, unit_label="개", choice_id=correct_choice_id),
        seed_slot=seed_slot,
        metadata_extra={"hidden_program": "count visual legend matches with level3 red-frame exclusion"},
    )


def _viewport_trace_episode(manifest: TemplateManifest, seed_slot: int):
    rng = random.Random(seed_slot + 7300 + manifest.level)
    source_value = 180 + rng.randint(0, 7) * 10
    delta = 35 + rng.randint(0, 4) * 5
    target_value = source_value + delta + (20 if manifest.level >= 3 else 0)
    answer = target_value * 1000
    examples = table_from_cells(
        "offset-examples",
        "탐색 기록: 기준 열과 목표 열 간격",
        rect(80, 200, 1040, 230),
        n_rows=4,
        n_cols=6,
        cells=[
            cell(0, 0, "행", style="header"),
            cell(0, 1, "기준"),
            cell(0, 2, "중간1"),
            cell(0, 3, "중간2"),
            cell(0, 4, "목표", style="header"),
            cell(0, 5, "관계", style="header"),
            cell(1, 0, "예시A", style="row_label", align="left"),
            _framed_cell(1, 1, "120"),
            cell(1, 2, "130"),
            cell(1, 3, "140"),
            _striped_cell(1, 4, "155"),
            cell(1, 5, "동일 간격"),
            cell(2, 0, "예시B", style="row_label", align="left"),
            _framed_cell(2, 1, "90"),
            cell(2, 2, "100"),
            cell(2, 3, "110"),
            _striped_cell(2, 4, "125"),
            cell(2, 5, "동일 간격"),
            cell(3, 0, "주의", style="row_label", align="left"),
            cell(3, 1, "기준"),
            cell(3, 2, "건수"),
            cell(3, 3, "참고"),
            cell(3, 4, "금액"),
            cell(3, 5, "단위 천원"),
        ],
        column_weights=(0.85, 0.9, 0.9, 0.9, 0.9, 1.2),
        row_heights=(44, 48, 48, 48),
        subtitle="이전 스크롤 위치에서 기록된 기준 셀과 목표 셀의 관계입니다.",
    )
    headers = ["행", "권역", "상태", "기준C10", "C11", "C12", "C13", "C14", "C15", "C16", "목표C17", "검산C18"]
    cells = [cell(0, col, header, style="header") for col, header in enumerate(headers)]
    rows = [
        ("01", "수도", "확정", source_value - 40, "11", "12", source_value - 5, "참고", "보류", "15", target_value - 50, "0"),
        ("02", "영남", "확정", source_value, "21", "22", source_value + 10, "참고", "보류", "25", target_value, "0"),
        ("03", "영남", "검토", source_value + 20, "31", "32", source_value + 35, "참고", "보류", "35", target_value + 30, "0"),
        ("04", "충청", "확정", source_value - 10, "41", "42", source_value + 15, "참고", "보류", "45", target_value - 10, "0"),
    ]
    for row_index, row in enumerate(rows, start=1):
        for col_index, value in enumerate(row):
            metadata = None
            style = "row_label" if col_index in {1, 2} else "body"
            if row_index == 2 and col_index == 3:
                metadata = {"frame": {"color": "#2d6a4f", "stroke_width": 2.4}}
            if row_index == 2 and col_index == 10:
                metadata = {"pattern": {"kind": "diagonal_stripe", "color": "#1d7a8c", "opacity": 0.62}}
            cells.append(cell(row_index, col_index, str(value), style=style, align="left" if col_index in {1, 2} else "center", metadata=metadata))
    wide = table_from_cells(
        "viewport-trace-wide",
        "화면 캡처 로그: 목표 열 추적",
        rect(56, 188, 1840, 330),
        n_rows=5,
        n_cols=len(headers),
        cells=cells,
        column_weights=(0.5, 0.75, 0.75, 1.0, 0.7, 0.7, 1.0, 0.85, 0.85, 0.7, 1.05, 0.9),
        row_heights=(54, 46, 46, 46, 46),
        subtitle="현재 뷰포트에는 기준 열 중심의 원장 일부만 표시됩니다.",
    )
    question = "예시의 열 오프셋 규칙을 적용해 영남 확정 행의 목표C17 값을 원 단위로 제출하라."
    query_pages, correct_choice_id = _query_page(
        question,
        answer,
        (source_value * 1000, (source_value + delta) * 1000, answer + 40000),
        level=manifest.level,
        template_id=manifest.template_id,
        seed_slot=seed_slot,
    )
    wide_page = PageSpec(
        page_id="wide-p1",
        title="Viewport Trace Ledger",
        width=1960,
        height=900,
        elements=(wide,),
        regions=(),
        notes=(),
        metadata={"wide_table": True, "initial_view": {"zoom_index": 2, "center_x": 520.0, "center_y": 410.0}},
    )
    required_navigation = dict(manifest.required_navigation)
    required_navigation["required_viewport_states"] = [
        {
            "state_id": "viewport-trace-target-column",
            "sheet_id": "wide",
            "page_id": "wide-p1",
            "min_zoom_index": 2,
            "required_action_types": ["pan_right", "pan_right", "zoom_in"],
            "match": "viewbox_intersects_target",
            "target_rects": [{"target_id": "target-c17", "kind": "column", "rect": {"x": 1540, "y": 188, "width": 180, "height": 330}}],
        }
    ]
    required_navigation["forbidden_shortcuts"] = [*required_navigation.get("forbidden_shortcuts", []), "initial_viewport_only", "no_pan_zoom"]
    return episode(
        manifest=manifest,
        family_display_name=FAMILY_LABEL,
        question=question,
        workbook_title="뷰포트 탐색 기록 검토",
        sheets=[
            sheet("examples", "캡처로그", [page("examples-p1", "탐색 기록", elements=[examples])]),
            sheet("wide", "원장", [wide_page]),
            sheet("query", "질의", query_pages),
        ],
        answer=_money_answer(answer, choice_id=correct_choice_id),
        seed_slot=seed_slot,
        metadata_extra={
            "hidden_program": "target column learned as framed source + 3 visible offsets",
            "required_navigation": required_navigation,
            "required_actions": ["must_switch_sheet", "must_pan", "must_zoom"],
        },
    )


def _merged_pan_episode(manifest: TemplateManifest, seed_slot: int):
    rng = random.Random(seed_slot + 8300 + manifest.level)
    prev = 70 + rng.randint(0, 9)
    current = prev + 8 + rng.randint(0, 5) + (4 if manifest.level >= 3 else 0)
    answer = current - prev
    examples = table_from_cells(
        "merged-pan-examples",
        "헤더 밴드 샘플",
        rect(74, 198, 1090, 244),
        n_rows=4,
        n_cols=7,
        cells=[
            cell(0, 0, "구분", row_span=2, style="header"),
            cell(0, 1, "상반기", col_span=3, style="header"),
            cell(0, 4, "하반기", col_span=3, style="header"),
            cell(1, 1, "일반"),
            cell(1, 2, "보정"),
            cell(1, 3, "검산"),
            cell(1, 4, "일반"),
            cell(1, 5, "보정"),
            cell(1, 6, "검산"),
            cell(2, 0, "범위", style="row_label", align="left"),
            cell(2, 1, "제외"),
            _striped_cell(2, 2, "대상"),
            cell(2, 3, "제외"),
            cell(2, 4, "제외"),
            _striped_cell(2, 5, "대상"),
            cell(2, 6, "제외"),
            cell(3, 0, "단위", style="row_label", align="left"),
            cell(3, 1, "점"),
            cell(3, 2, "점"),
            cell(3, 3, "점"),
            cell(3, 4, "점"),
            cell(3, 5, "점"),
            cell(3, 6, "점"),
        ],
        column_weights=(0.9, 0.85, 0.85, 0.85, 0.85, 0.85, 0.85),
        row_heights=(42, 40, 48, 48),
        subtitle="상위 기간 밴드와 하위 지표 열이 함께 구성된 샘플 매트릭스입니다.",
    )
    headers = ["항목", "24상 일반", "24상 보정", "24상 검산", "비고1", "비고2", "비고3", "25하 일반", "25하 보정", "25하 검산"]
    cells = [
        cell(0, 0, "항목", row_span=2, style="header"),
        cell(0, 1, "2024 상반기", col_span=3, style="header"),
        cell(0, 4, "중간 참고", col_span=3, style="header"),
        cell(0, 7, "2025 하반기", col_span=3, style="header"),
    ]
    for col, header in enumerate(headers[1:], start=1):
        cells.append(cell(1, col, header.replace("24상 ", "").replace("25하 ", ""), style="header"))
    rows = [
        ("서울", prev - 3, prev, prev + 1, "a", "b", "c", current - 2, current, current + 1),
        ("부산", prev + 4, prev + 7, prev + 9, "a", "b", "c", current + 5, current + 8, current + 9),
        ("대구", prev - 5, prev - 1, prev, "a", "b", "c", current - 4, current - 1, current),
    ]
    for row_index, row in enumerate(rows, start=2):
        cells.append(cell(row_index, 0, row[0], style="row_label", align="left"))
        for col_index, value in enumerate(row[1:], start=1):
            cells.append(cell(row_index, col_index, str(value)))
    wide = table_from_cells(
        "merged-pan-wide",
        "원거리 병합 헤더 질의 표",
        rect(56, 188, 1880, 306),
        n_rows=5,
        n_cols=10,
        cells=cells,
        column_weights=(0.75, 0.95, 0.95, 0.95, 0.8, 0.8, 0.8, 0.95, 0.95, 0.95),
        row_heights=(44, 42, 48, 48, 48),
        subtitle="가로로 분리된 기간 밴드를 가진 운영 매트릭스입니다.",
    )
    question = "서울 행에서 2025 하반기 보정 값은 2024 상반기 보정 값보다 몇 점 큰가?"
    query_pages, correct_choice_id = _query_page(
        question,
        answer,
        (current, prev, answer + 3),
        level=manifest.level,
        template_id=manifest.template_id,
        seed_slot=seed_slot,
        unit_label="점",
    )
    required_navigation = dict(manifest.required_navigation)
    required_navigation["required_viewport_states"] = [
        {
            "state_id": "merged-pan-right-scope",
            "sheet_id": "wide",
            "page_id": "wide-p1",
            "min_zoom_index": 2,
            "required_action_types": ["pan_right", "pan_right", "zoom_in"],
            "match": "viewbox_intersects_target",
            "target_rects": [{"target_id": "2025-second-band", "kind": "merged_header_scope", "rect": {"x": 1380, "y": 188, "width": 520, "height": 306}}],
        }
    ]
    required_navigation["forbidden_shortcuts"] = [*required_navigation.get("forbidden_shortcuts", []), "initial_viewport_only", "wrong_merged_scope"]
    wide_page = PageSpec(page_id="wide-p1", title="Wide Matrix Ledger", width=2000, height=900, elements=(wide,), regions=(), notes=(), metadata={"wide_table": True, "initial_view": {"zoom_index": 2, "center_x": 520.0, "center_y": 410.0}})
    return episode(
        manifest=manifest,
        family_display_name=FAMILY_LABEL,
        question=question,
        workbook_title="원거리 헤더 매트릭스 검토",
        sheets=[
            sheet("examples", "헤더샘플", [page("examples-p1", "헤더 밴드 샘플", elements=[examples])]),
            sheet("wide", "매트릭스", [wide_page]),
            sheet("query", "질의", query_pages),
        ],
        answer=_money_answer(answer, unit_label="점", choice_id=correct_choice_id),
        seed_slot=seed_slot,
        metadata_extra={
            "hidden_program": "right merged header corrected value minus left merged header corrected value",
            "required_navigation": required_navigation,
            "required_actions": ["must_switch_sheet", "must_pan", "must_zoom"],
        },
    )


def _zoom_micro_marker_episode(manifest: TemplateManifest, seed_slot: int):
    rng = random.Random(seed_slot + 9300 + manifest.level)
    base = 34 + rng.randint(0, 6)
    bonus = 6 if manifest.level >= 2 else 4
    penalty = 3 if manifest.level >= 3 else 0
    answer = base + bonus - penalty
    examples = table_from_cells(
        "micro-marker-examples",
        "Inspection Samples: 코너 마커",
        rect(78, 202, 1060, 252),
        n_rows=4,
        n_cols=5,
        cells=[
            cell(0, 0, "행", style="header"),
            cell(0, 1, "값", style="header"),
            cell(0, 2, "마커칸", style="header"),
            cell(0, 3, "처리", style="header"),
            cell(0, 4, "결과", style="header"),
            cell(1, 0, "예시A", style="row_label", align="left"),
            cell(1, 1, "30"),
            cell(1, 2, "", metadata={"icon": {"kind": "triangle", "anchor": "top_right", "color": "#2d6a4f", "size": 9}}),
            cell(1, 3, "가산"),
            cell(1, 4, str(30 + bonus), style="total"),
            cell(2, 0, "예시B", style="row_label", align="left"),
            cell(2, 1, "30"),
            cell(2, 2, "", metadata={"icon": {"kind": "triangle", "anchor": "bottom_right", "color": "#b3261e", "size": 9}}),
            cell(2, 3, "감산" if manifest.level >= 3 else "제외"),
            cell(2, 4, str(30 - penalty) if manifest.level >= 3 else "30"),
            cell(3, 0, "예시C", style="row_label", align="left"),
            cell(3, 1, "30"),
            cell(3, 2, ""),
            cell(3, 3, "기본"),
            cell(3, 4, "30"),
        ],
        column_weights=(0.85, 0.7, 0.9, 1.0, 0.8),
        row_heights=(44, 50, 50, 50),
        subtitle="작은 코너 마커 위치가 검수 판정에 사용되는 샘플입니다.",
    )
    query_table = table_from_cells(
        "micro-marker-query",
        "Inspection Row: 마커 확대 검수",
        rect(84, 350, 760, 176),
        n_rows=2,
        n_cols=5,
        cells=[
            cell(0, 0, "행", style="header"),
            cell(0, 1, "기본값", style="header"),
            cell(0, 2, "마커A", style="header"),
            cell(0, 3, "마커B", style="header"),
            cell(0, 4, "결과", style="header"),
            cell(1, 0, "검수", style="row_label", align="left"),
            cell(1, 1, str(base)),
            cell(1, 2, "", metadata={"icon": {"kind": "triangle", "anchor": "top_right", "color": "#2d6a4f", "size": 8}}),
            cell(1, 3, "", metadata={"icon": {"kind": "triangle", "anchor": "bottom_right", "color": "#b3261e", "size": 8}} if manifest.level >= 3 else {}),
            cell(1, 4, "?"),
        ],
        column_weights=(0.75, 0.85, 0.85, 0.85, 0.75),
        row_heights=(46, 54),
        subtitle="미세 마커는 확대 상태에서 판독하는 주석 표식입니다.",
    )
    loupe_panel = text_block(
        "micro-marker-loupe",
        "확대 판독 패널",
        rect(884, 350, 250, 176),
        (
            "Zoom 160% · 셀 내부 주석 판독",
            "녹색 코너: 상단 위치",
            "적색 코너: 하단 위치",
            "결과 칸은 제출 전 비어 있음",
        ),
        style="note",
        subtitle="Inspection Lens",
    )
    question = "Inspection samples 기준으로 검수 행의 결과 값은 얼마인가?"
    query_pages, correct_choice_id = _query_page(
        question,
        answer,
        (base, base + bonus + 2, answer + penalty + 2),
        level=manifest.level,
        template_id=manifest.template_id,
        seed_slot=seed_slot,
        lead_elements=(query_table, loupe_panel),
        unit_label="점",
    )
    required_navigation = dict(manifest.required_navigation)
    required_navigation["required_viewport_states"] = [
        {
            "state_id": "zoom-micro-marker-query",
            "sheet_id": "query",
            "page_id": "query-p1",
            "min_zoom_index": 3,
            "required_action_types": ["zoom_in"],
            "match": "viewbox_intersects_target",
            "target_rects": [{"target_id": "micro-marker-cells", "kind": "cell_range", "rect": {"x": 390, "y": 350, "width": 320, "height": 176}}],
        }
    ]
    required_navigation["forbidden_shortcuts"] = [*required_navigation.get("forbidden_shortcuts", []), "no_zoom", "marker_presence_only"]
    return episode(
        manifest=manifest,
        family_display_name=FAMILY_LABEL,
        question=question,
        workbook_title="미세 마커 검수 워크벤치",
        sheets=[
            sheet("examples", "검수샘플", [page("examples-p1", "마커 검수 샘플", elements=[examples])]),
            sheet("query", "질의", query_pages),
        ],
        answer=_money_answer(answer, unit_label="점", choice_id=correct_choice_id),
        seed_slot=seed_slot,
        metadata_extra={
            "hidden_program": "base + top_right_bonus - level3_bottom_right_penalty",
            "required_navigation": required_navigation,
            "required_actions": ["must_switch_sheet", "must_zoom"],
        },
    )


BUILDERS = {
    "symbol_rule_induction": _symbol_episode,
    "merged_header_scope": _merged_episode,
    "abbrev_doc_reference": _abbrev_episode,
    "wide_table_navigation": _wide_episode,
    "color_condition_rule_induction": _color_condition_episode,
    "legend_color_exception_scope": _legend_color_exception_episode,
    "wide_table_viewport_trace": _viewport_trace_episode,
    "merged_header_pan_scope": _merged_pan_episode,
    "zoom_micro_marker_exception": _zoom_micro_marker_episode,
}


def build_episode(level: int, seed: int, *, template_id: str | None = None):
    manifest, seed_slot = resolve_template_seed(list_manifests(level), seed, template_id=template_id)
    return BUILDERS[manifest.template_id](manifest, seed_slot)
