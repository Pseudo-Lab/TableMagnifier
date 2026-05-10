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
        allowed_cue_variants=("symbol", "merged", "abbrev", "wide", "unit"),
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


def _money_answer(value: int) -> AnswerSpec:
    return AnswerSpec(
        canonical=str(value),
        accepted=(f"{value:,}", f"{value}원", f"{value:,}원"),
        normalizer="ko_answer",
    )


def _query_page(
    question: str,
    answer: int,
    distractors: tuple[int, int, int],
    *,
    level: int,
    lead_elements: tuple[Any, ...] = (),
    unit_label: str = "원",
):
    cards = [
        ChoiceCardSpec("A", f"{distractors[0]:,}{unit_label}", ("단위만 맞춘 후보",)),
        ChoiceCardSpec("B", f"{answer:,}{unit_label}", ("계산 규칙과 단위를 모두 반영",)),
        ChoiceCardSpec("C", f"{distractors[1]:,}{unit_label}", ("지원 문서 또는 예외를 건너뛴 후보",)),
        ChoiceCardSpec("D", f"{distractors[2]:,}{unit_label}", ("유사 열/행을 고른 후보",)),
    ]
    headers, y = query_header_blocks(
        target_title="최종 질의",
        target_lines=(question,),
        guidance_title="제출 형식",
        guidance_lines=(f"정답은 {unit_label} 단위 숫자로 제출합니다. 선택지는 검산용이며 직접 숫자를 입력해도 됩니다.",),
    )
    choice_y = max(y, 560.0 if lead_elements else y)
    choice_elements, regions = query_choice_cards(prefix="answer", cards=cards, answer_form="number", y=choice_y)
    pages = [page("query-p1", "질의", elements=(*headers, *lead_elements, *choice_elements), regions=regions)]
    if level >= 3:
        pages.append(
            page(
                "query-p2",
                "예외 확인",
                elements=[
                    text_block(
                        "exception-check",
                        "Level 3 예외",
                        rect(84, 176, 1080, 150),
                        ("보조 페이지의 예외 문구가 기본 규칙보다 우선합니다.", "예외가 적용되는 행 또는 열만 다시 확인하세요."),
                        style="note",
                    ),
                    table_from_cells(
                        "exception-application",
                        "예외 적용 범위",
                        rect(84, 386, 900, 170),
                        n_rows=3,
                        n_cols=3,
                        cells=[
                            cell(0, 0, "조건", style="header"),
                            cell(0, 1, "적용", style="header"),
                            cell(0, 2, "판정", style="header"),
                            cell(1, 0, "질의 행", style="row_label", align="left"),
                            cell(1, 1, "예외 보너스 확인", style="accent"),
                            cell(1, 2, "필수"),
                            cell(2, 0, "예시 행", style="row_label", align="left"),
                            cell(2, 1, "기본 규칙만 사용"),
                            cell(2, 2, "제외"),
                        ],
                        column_weights=(1.0, 1.4, 0.8),
                        row_heights=(44, 46, 46),
                        subtitle="질의 행에만 보조 페이지의 예외를 적용합니다.",
                    ),
                ],
            )
        )
    return pages


def _symbol_episode(manifest: TemplateManifest, seed_slot: int):
    rng = random.Random(seed_slot + 1300 + manifest.level)
    a = 8 + rng.randint(0, 4)
    b = 5 + rng.randint(0, 3)
    multiplier = 2 + (manifest.level >= 2)
    bonus = 4 if manifest.level >= 3 else 0
    answer = (a * multiplier) + (b * multiplier) + bonus
    examples = table_from_cells(
        "symbol-examples",
        "완성 행에서 기호 규칙 찾기",
        rect(84, 190, 760, 260),
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
        subtitle="★가 붙은 값의 처리 방식은 완성 행에서만 유도합니다.",
    )
    rule_note = text_block(
        "symbol-level-note",
        "탐색 메모",
        rect(884, 206, 296, 172),
        (
            "같은 숫자라도 ★ 위치가 붙은 셀만 달라집니다.",
            "Level 3에서는 질의 시트의 예외 보너스를 더합니다." if manifest.level >= 3 else "기호가 없는 값은 그대로 둡니다.",
        ),
        style="note",
    )
    query_table = table_from_cells(
        "symbol-query",
        "미완성 행",
        rect(84, 360, 760, 168),
        n_rows=2,
        n_cols=4,
        cells=[
            cell(0, 0, "항목", style="header"),
            cell(0, 1, "A", style="header"),
            cell(0, 2, "B", style="header"),
            cell(0, 3, "합계", style="header"),
            cell(1, 0, "질의", style="row_label", align="left"),
            cell(1, 1, f"{a}★", style="accent"),
            cell(1, 2, f"{b}★", style="accent"),
            cell(1, 3, "?"),
        ],
        subtitle="완성 행에서 유도한 규칙을 이 행에 적용합니다.",
    )
    question = "완성 행에서 ★ 규칙을 유도했을 때 질의 행의 합계는 원 단위로 얼마인가?"
    return episode(
        manifest=manifest,
        family_display_name=FAMILY_LABEL,
        question=question,
        workbook_title="기호 규칙 유도 에피소드",
        sheets=[
            sheet("examples", "예시", [page("examples-p1", "예시 표", elements=[examples, rule_note])]),
            sheet(
                "query",
                "질의",
                _query_page(
                    question,
                    answer,
                    (answer - 3, answer - bonus, answer + 7),
                    level=manifest.level,
                    lead_elements=(query_table,),
                ),
            ),
        ],
        answer=_money_answer(answer),
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
            cell(3, 1, f"{previous:.1f}%", style="accent"),
            cell(3, 2, "9.4%"),
            cell(3, 3, "8.8%"),
            cell(3, 4, f"{current:.1f}%", style="accent"),
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
        subtitle="상단 병합 헤더가 각 하위 열의 기간 범위를 결정합니다.",
    )
    note_panel = text_block(
        "scope-note",
        "%p 계산 안내",
        rect(94, 210, 1000, 140),
        ("반품률 차이는 퍼센트포인트로 계산합니다.", "예: 12.3%와 10.1%의 차이는 2.2%p입니다."),
        style="note",
    )
    question = "2025년 상반기 수도권 소매 부문의 반품률은 2024년 하반기 같은 범위보다 몇 %p 증가했는가? 소수 첫째 자리 값에 10을 곱한 정수로 제출하라."
    return episode(
        manifest=manifest,
        family_display_name=FAMILY_LABEL,
        question=question,
        workbook_title="병합 헤더 범위 상속 에피소드",
        sheets=[
            sheet("examples", "범위표", [page("examples-p1", "병합 헤더 표", elements=[table])]),
            sheet("notes", "계산규칙", [page("notes-p1", "단위 안내", elements=[note_panel])]),
            sheet("query", "질의", _query_page(question, answer, (answer + 10, answer - 2, answer + 3), level=manifest.level, unit_label="점")),
        ],
        answer=_money_answer(answer),
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
        "지점별 조정 지표와 상태 코드",
        rect(64, 206, 1110, 318),
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
            cell(1, 1, str(tca), style="accent"),
            cell(1, 2, f"{r2n:.1f}", style="accent" if manifest.level >= 3 else "body"),
            cell(1, 3, str(margin_delta), style="accent" if manifest.level >= 2 else "body"),
            cell(1, 4, f"{kadj}", style="accent"),
            cell(1, 5, hold_flag, style="negative" if hold_flag == "Y" else "body"),
            cell(1, 6, "북부"),
            cell(2, 0, "부산B", style="row_label", align="left"),
            cell(2, 1, str(tca - 160)),
            cell(2, 2, "7.6"),
            cell(2, 3, "-2.1"),
            cell(2, 4, "104"),
            cell(2, 5, "N"),
            cell(2, 6, "남부"),
            cell(3, 0, "대전C", style="row_label", align="left"),
            cell(3, 1, str(tca + 90)),
            cell(3, 2, "6.8"),
            cell(3, 3, "1.5"),
            cell(3, 4, "101"),
            cell(3, 5, "N"),
            cell(3, 6, "중부"),
            cell(4, 0, "서울D", style="row_label", align="left"),
            cell(4, 1, str(tca + 20)),
            cell(4, 2, f"{r2n + 0.3:.1f}"),
            cell(4, 3, str(margin_delta - 1)),
            cell(4, 4, str(kadj - 2)),
            cell(4, 5, "Y"),
            cell(4, 6, "북부"),
            cell(5, 0, "광주E", style="row_label", align="left"),
            cell(5, 1, str(tca - 240)),
            cell(5, 2, "8.4"),
            cell(5, 3, "2"),
            cell(5, 4, "103"),
            cell(5, 5, "N"),
            cell(5, 6, "서남"),
            cell(6, 0, "원주F", style="row_label", align="left"),
            cell(6, 1, str(tca + 140)),
            cell(6, 2, "6.9"),
            cell(6, 3, "-3"),
            cell(6, 4, str(kadj)),
            cell(6, 5, "N"),
            cell(6, 6, "중부"),
        ],
        column_weights=(1.2, 0.95, 0.8, 0.8, 0.9, 0.75, 0.9),
        row_heights=(42, 42, 42, 42, 42, 42, 42),
        subtitle="약어 의미, 단위, 상태 코드 예외는 별도 문서를 확인해야 합니다.",
    )
    glossary = table_from_cells(
        "glossary",
        "합성 약어·상태 규칙 문서",
        rect(64, 206, 1110, 390),
        n_rows=7,
        n_cols=3,
        cells=[
            cell(0, 0, "약어", style="header"),
            cell(0, 1, "의미", style="header"),
            cell(0, 2, "계산상 주의", style="header"),
            cell(1, 0, "TCA", style="row_label"),
            cell(1, 1, "총계약조정액"),
            cell(1, 2, "천 원 단위"),
            cell(2, 0, "R2N", style="row_label"),
            cell(2, 1, "재방문 순전환율"),
            cell(2, 2, "백분율"),
            cell(3, 0, "M-Adj", style="row_label"),
            cell(3, 1, "전월 대비 마진 변화"),
            cell(3, 2, "Level 2 이상: 만 원 단위로 TCA 원화값에 더한 뒤 보정"),
            cell(4, 0, "K-Adj", style="row_label"),
            cell(4, 1, "권역 보정계수"),
            cell(4, 2, "표시값을 100으로 나누어 최종 금액에 곱함"),
            cell(5, 0, "HLD", style="row_label"),
            cell(5, 1, "검수 보류 상태"),
            cell(5, 2, "Level 3: HLD=Y이면 K-Adj는 106을 상한으로 사용"),
            cell(6, 0, "군집", style="row_label"),
            cell(6, 1, "동명이 지점 구분용 묶음"),
            cell(6, 2, "같은 도시명이라도 군집이 다르면 다른 행"),
        ],
        column_weights=(0.75, 1.45, 2.7),
        row_heights=(42, 48, 48, 58, 58, 58, 48),
        subtitle="실제 세계 약어가 아니라 에피소드별 합성 약어입니다.",
    )
    if manifest.level == 1:
        question = "서울A 지점의 총계약조정액에 권역 보정계수를 반영한 금액은 원 단위로 얼마인가?"
    elif manifest.level == 2:
        question = "서울A 지점의 TCA 원화값에 M-Adj 조정을 더한 뒤 K-Adj를 반영한 금액은 원 단위로 얼마인가?"
    else:
        question = "서울A 지점은 HLD=Y이다. 약어 문서의 Level 3 예외까지 적용해 최종 조정 금액을 원 단위로 구하라."
    return episode(
        manifest=manifest,
        family_display_name=FAMILY_LABEL,
        question=question,
        workbook_title="합성 약어 문서 참조 에피소드",
        sheets=[
            sheet("main", "메인", [page("main-p1", "메인 표", elements=[main])]),
            sheet("glossary", "약어집", [page("glossary-p1", "약어 문서", elements=[glossary])]),
            sheet(
                "query",
                "질의",
                _query_page(
                    question,
                    answer,
                    (tca * 1000, int(round((tca * 1000) * (kadj / 100))), answer + 80000),
                    level=manifest.level,
                ),
            ),
        ],
        answer=_money_answer(answer),
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
            cell(3, 3, "질의는 C44 신규계약조정액 사용"),
            cell(4, 0, "C45-C52", style="row_label"),
            cell(4, 1, "2025 환급/보류 조정"),
            cell(4, 2, "천원"),
            cell(4, 3, "Level 3: 보류분은 C52에 합산"),
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
            style = "accent" if row_index == 2 and col_index in {12, 14} else "row_label" if col_index in {1, 2, 3} else "body"
            if row_index == 5 and col_index in {1, 2, 3}:
                style = "negative"
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
        subtitle="오른쪽 C44/C52 열은 초기 화면에서 작게 보이거나 이동 후 확인해야 합니다.",
    )
    question = "상태가 확정인 부산권 B2B 행 중 첫 번째 대상 행에서 C44 신규계약조정액과 C52 보정환급액의 차이를 원 단위로 구하라."
    wide_page = PageSpec(
        page_id="wide-p1",
        title="넓은 표",
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
        workbook_title="넓은 테이블 탐색 계산 에피소드",
        sheets=[
            sheet("directory", "열안내", [page("directory-p1", "열 안내", elements=[directory_table])]),
            sheet("wide", "넓은표", [wide_page]),
            sheet(
                "query",
                "질의",
                _query_page(
                    question,
                    answer,
                    ((target_c44 + target_c52) * 1000, target_c44 - target_c52, answer + 200000),
                    level=manifest.level,
                ),
            ),
        ],
        answer=_money_answer(answer),
        seed_slot=seed_slot,
        metadata_extra={
            "hidden_program": "(C44_new_contract_adjusted - C52_adjusted_refund) * 1000 for first confirmed Busan B2B row",
            "declared_column_count": 60,
            "required_navigation": required_navigation,
        },
    )


BUILDERS = {
    "symbol_rule_induction": _symbol_episode,
    "merged_header_scope": _merged_episode,
    "abbrev_doc_reference": _abbrev_episode,
    "wide_table_navigation": _wide_episode,
}


def build_episode(level: int, seed: int, *, template_id: str | None = None):
    manifest, seed_slot = resolve_template_seed(list_manifests(level), seed, template_id=template_id)
    return BUILDERS[manifest.template_id](manifest, seed_slot)
