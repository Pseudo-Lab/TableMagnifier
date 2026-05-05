"""셀 모서리 표식 위치 규칙을 유도해 전이하는 canonical family."""

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

FAMILY = "marker_position_rule_transfer"
FAMILY_LABEL = "표식 위치 규칙 전이"

TEMPLATE_ID = "corner_anchor_statement"
NOTE_ID = "anchor-scope-note"

_LEVEL_REASONING_STEPS = {1: (3, 3), 2: (4, 4), 3: (5, 5)}
_LEVEL_RATIONALES = {
    1: "예시, 범례, 가벼운 반례를 모두 보되 각 surface가 작아 3단계로 풀리는 문제다.",
    2: "두 번째 예시와 네 모서리 anchor mapping을 함께 적용하는 4단계 문제다.",
    3: "두 예시, 범례, 반례, openable note를 결합해 위치 규칙을 확정하는 5단계 문제다.",
}

_ANCHOR_LABELS = {
    "top_left": "좌상단",
    "top_right": "우상단",
    "bottom_left": "좌하단",
    "bottom_right": "우하단",
}
_BASE_ANSWER_LABELS = ("C", "D", "B")


def _manifest(level: int) -> TemplateManifest:
    required_page_refs = ("examples:examples-p1", "legend:legend-p1", "exception:exception-p1", "query:query-p1")
    required_actions = ("must_switch_sheet", "must_visit_legend", "must_visit_exception")
    required_evidence: tuple[dict[str, Any], ...] = (
        {"kind": "page", "sheet_id": "examples", "page_id": "examples-p1"},
        {"kind": "page", "sheet_id": "legend", "page_id": "legend-p1"},
        {"kind": "page", "sheet_id": "exception", "page_id": "exception-p1"},
        {"kind": "page", "sheet_id": "query", "page_id": "query-p1"},
    )
    cue_tags = ("icon_anchor_position", "legend_item")
    operator_tags = ("match_mapping", "convert_representation", "disambiguate_by_exception")
    shortcut_probes = ("query_only", "text_scrape", "marker_presence_only", "legend_skip")
    if level >= 2:
        required_page_refs = ("examples:examples-p1", "examples:examples-p2", "legend:legend-p1", "exception:exception-p1", "query:query-p1")
        required_actions = (*required_actions, "must_visit_examples_page2")
        required_evidence = (
            {"kind": "page", "sheet_id": "examples", "page_id": "examples-p1"},
            {"kind": "page", "sheet_id": "examples", "page_id": "examples-p2"},
            {"kind": "page", "sheet_id": "legend", "page_id": "legend-p1"},
            {"kind": "page", "sheet_id": "exception", "page_id": "exception-p1"},
            {"kind": "page", "sheet_id": "query", "page_id": "query-p1"},
        )
        cue_tags = (*cue_tags, "row_group_band")
        shortcut_probes = (*shortcut_probes, "exception_skip")
    if level == 3:
        required_page_refs = (
            "examples:examples-p1",
            "examples:examples-p2",
            "legend:legend-p1",
            "exception:exception-p1",
            "exception:exception-p2",
            "query:query-p1",
        )
        required_actions = (*required_actions, "must_open_note")
        required_evidence = (
            *required_evidence,
            {"kind": "page", "sheet_id": "exception", "page_id": "exception-p2"},
            {"kind": "note", "sheet_id": "exception", "page_id": "exception-p2", "note_id": NOTE_ID},
        )
        cue_tags = (*cue_tags, "note_anchor")
        shortcut_probes = (*shortcut_probes, "note_skip")
    return TemplateManifest(
        family=FAMILY,
        level=level,
        template_id=TEMPLATE_ID,
        template_label="모서리 표식 위치 설명 선택",
        latent_rule="범례와 예시에서 삼각 표식의 셀 내부 모서리 위치가 뜻하는 연산을 유도하고, 반례로 모양-only 해석을 버린다.",
        operator_tags=operator_tags,
        cue_tags=cue_tags,
        answer_form="statement_choice",
        primary_operator="match_mapping",
        support_operator="disambiguate_by_exception",
        required_visual_cues=cue_tags,
        required_surfaces=("example_table_panel", "legend_panel", "exception_card", "query_table_panel", "answer_choice_panel"),
        capability_axes=("visual_grounding", "rule_induction", "rule_transfer", "disambiguation"),
        task_archetype="marker_position_transfer",
        scenario_context="표식 모양이 아니라 셀 안의 모서리 위치가 업무 표의 판정 상태를 결정하는 과업이다.",
        benchmark_track="canonical_real_tableqa",
        reasoning_archetype="induce_apply",
        abstraction_tier="abstract_worksheet",
        support_surface_policy="required",
        qa_dependency="hybrid_induction_tableqa",
        generalization_group=f"{FAMILY}:{TEMPLATE_ID}:l{level}",
        required_sheet_ids=("examples", "legend", "exception", "query"),
        required_page_refs=required_page_refs,
        allowed_cue_variants=("top_left", "top_right", "bottom_left", "bottom_right"),
        distractor_policy="같은 삼각형 모양을 다른 모서리에 반복해 위치를 무시하는 오답과 범례 또는 반례를 건너뛰는 오답을 함께 둔다.",
        level_rationale=_LEVEL_RATIONALES[level],
        text_only_failure_modes=(
            "row label과 note text만 읽으면 어느 모서리 anchor가 실제 상태인지 고정되지 않는다.",
            "삼각형이 있다는 사실만 따라가면 반례 표가 제거하는 wrong-anchor 행을 고르게 된다.",
        ),
        distractor_failure_modes=(
            "삼각형 모양만 보고 모든 표식 행을 포함하는 오답",
            "범례를 건너뛰고 반대 모서리 anchor를 실제 후보로 읽는 오답",
            "Level 3에서 note가 고정하는 적용 묶음을 무시하는 오답",
        ),
        level_knobs={"level": level, "template": TEMPLATE_ID},
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


def _triangle(anchor: str, *, color: str = "#0f766e") -> dict[str, Any]:
    return {"icon": {"kind": "triangle", "anchor": anchor, "color": color}}


def _frame(*, color: str = "#2563eb") -> dict[str, Any]:
    return {"frame": {"kind": "selection", "color": color}}


def _marker_cell(anchor: str | None, *, selected: bool = False) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    if anchor:
        metadata.update(_triangle(anchor))
    if selected:
        metadata.update(_frame())
    return {"metadata": metadata}


def _anchor_rule(seed_slot: int, *, counterfactual: bool = False) -> dict[str, str]:
    include_anchor = ("top_right", "bottom_right", "top_left", "bottom_left")[seed_slot % 4]
    exclude_anchor = ("bottom_left", "top_left", "bottom_right", "top_right")[seed_slot % 4]
    if counterfactual:
        include_anchor, exclude_anchor = exclude_anchor, include_anchor
    return {
        "include": include_anchor,
        "exclude": exclude_anchor,
        "review": "top_left" if include_anchor != "top_left" else "bottom_right",
        "hold": "bottom_right" if include_anchor != "bottom_right" else "top_left",
    }


def _rule_table(
    *,
    element_id: str,
    title: str,
    box,
    rows: list[tuple[str, str | None, bool]],
    subtitle: str,
    show_result: bool = True,
):
    headers = ("항목", "표식", "결과") if show_result else ("항목", "표식")
    cells = [cell(0, index, header, style="header") for index, header in enumerate(headers)]
    for row_index, (label, anchor, selected) in enumerate(rows, start=1):
        cells.append(cell(row_index, 0, label, style="row_label", align="left"))
        cells.append(cell(row_index, 1, "", metadata=_marker_cell(anchor)["metadata"]))
        if show_result:
            cells.append(cell(row_index, 2, "", metadata=_frame() if selected else {}))
    return table_from_cells(
        element_id,
        title,
        box,
        n_rows=1 + len(rows),
        n_cols=len(headers),
        cells=cells,
        column_weights=(0.52, 0.24, 0.24) if show_result else (0.62, 0.38),
        row_heights=(40,) + tuple(48 for _ in rows),
        subtitle=subtitle,
    )


def _grouped_rule_table(
    *,
    element_id: str,
    title: str,
    box,
    groups: list[tuple[str, list[tuple[str, str | None, bool]]]],
    subtitle: str,
    show_result: bool = True,
):
    headers = ("묶음", "항목", "표식", "결과") if show_result else ("묶음", "항목", "표식")
    cells = [cell(0, index, header, style="header") for index, header in enumerate(headers)]
    row_heights = [38]
    row_index = 1
    for group_label, rows in groups:
        cells.append(cell(row_index, 0, group_label, style="total_label", align="left"))
        cells.append(cell(row_index, 1, "", style="muted"))
        cells.append(cell(row_index, 2, "", style="muted"))
        if show_result:
            cells.append(cell(row_index, 3, "", style="muted"))
        row_heights.append(34)
        row_index += 1
        for label, anchor, selected in rows:
            cells.append(cell(row_index, 0, "", style="muted"))
            cells.append(cell(row_index, 1, f"  {label}", style="row_label", align="left"))
            cells.append(cell(row_index, 2, "", metadata=_marker_cell(anchor)["metadata"]))
            if show_result:
                cells.append(cell(row_index, 3, "", metadata=_frame() if selected else {}))
            row_heights.append(42)
            row_index += 1
    return table_from_cells(
        element_id,
        title,
        box,
        n_rows=row_index,
        n_cols=len(headers),
        cells=cells,
        column_weights=(0.24, 0.34, 0.20, 0.22) if show_result else (0.28, 0.42, 0.30),
        row_heights=tuple(row_heights),
        subtitle=subtitle,
    )


def _legend_table(element_id: str, box, *, rule: dict[str, str], level: int):
    anchors = (rule["include"], rule["exclude"]) if level == 1 else ("top_left", "top_right", "bottom_left", "bottom_right")
    cells = [cell(0, 0, "표식 위치", style="header"), cell(0, 1, "판정 의미", style="header")]
    for row_index, anchor in enumerate(anchors, start=1):
        meaning = "실제 후보" if anchor == rule["include"] else "제외 후보" if anchor == rule["exclude"] else "검토 전용"
        if level == 3 and anchor == rule["hold"]:
            meaning = "메모 확인"
        cells.append(cell(row_index, 0, _ANCHOR_LABELS[anchor], metadata=_triangle(anchor)))
        cells.append(cell(row_index, 1, meaning, style="row_label", align="left"))
    return table_from_cells(
        element_id,
        "표식 위치 범례",
        box,
        n_rows=1 + len(anchors),
        n_cols=2,
        cells=cells,
        column_weights=(0.42, 0.58),
        row_heights=(40,) + tuple(46 for _ in anchors),
        subtitle="같은 삼각형이라도 셀 안 모서리 위치가 다르면 의미가 달라진다",
    )


def _choice_cards(
    *,
    prefix: str,
    correct_statement: str,
    distractors: tuple[str, str, str],
    answer_choice: str,
    y: float = 604.0,
):
    statements = {
        "A": distractors[0],
        "B": distractors[1],
        "C": distractors[2],
        "D": distractors[1],
    }
    statements[answer_choice] = correct_statement
    unused_distractors = iter(distractors)
    for label in ("A", "B", "C", "D"):
        if label == answer_choice:
            continue
        statements[label] = next(unused_distractors)
    cards = tuple(ChoiceCardSpec(label, f"설명 {index}", (statements[label],)) for index, label in enumerate(("A", "B", "C", "D"), start=1))
    choice_elements, choice_regions = query_choice_cards(
        prefix=prefix,
        cards=cards,
        answer_form="statement_choice",
        y=y,
        columns=2,
        height=104,
    )
    return choice_elements, choice_regions, answer_choice


def _base_answer_choice(seed_slot: int) -> str:
    return _BASE_ANSWER_LABELS[seed_slot % len(_BASE_ANSWER_LABELS)]


def _counterfactual_answer_choice(seed_slot: int) -> str:
    base_choice = _base_answer_choice(seed_slot)
    for choice in ("B", "C", "D"):
        if choice != base_choice:
            return choice
    return "B"


def _query_header(*, target: tuple[str, ...], guidance: tuple[str, ...]):
    return query_header_blocks(
        target_title="질의 대상",
        target_lines=target,
        guidance_title="판정 기준",
        guidance_lines=guidance,
        mode="compact",
    )


def _level_rows(labels: tuple[str, ...], rule: dict[str, str]) -> list[tuple[str, str | None, bool]]:
    return [
        (labels[0], rule["include"], True),
        (labels[1], rule["exclude"], False),
        (labels[2], rule["review"], False),
        (labels[3], None, False),
    ]


def _build_level_1(manifest: TemplateManifest, seed_slot: int, *, counterfactual: bool = False):
    rule = _anchor_rule(seed_slot, counterfactual=counterfactual)
    query_rule = _anchor_rule(seed_slot, counterfactual=False)
    labels = rotate(("가람", "나래", "다온", "라온"), seed_slot)
    query_labels = rotate(("현재-가", "현재-나", "현재-다", "현재-라"), seed_slot)
    correct = query_labels[0]
    expected = query_labels[1] if counterfactual else correct
    example_rows = _level_rows(labels, rule)
    query_rows = [
        (correct, query_rule["include"], False),
        (query_labels[1], query_rule["exclude"], False),
        (query_labels[2], query_rule["review"], False),
        (query_labels[3], None, False),
    ]
    query_blocks, _ = _query_header(
        target=("현재 표의 판정 설명을 고릅니다.",),
        guidance=("범례와 반례를 함께 보면 표식 모양이 아니라 모서리 위치가 기준입니다.",),
    )
    choices, choice_regions, answer_choice = _choice_cards(
        prefix="marker-l1-choice",
        correct_statement=f"{expected} 행만 실제 후보로 남는다.",
        distractors=(
            f"{correct}, {query_labels[1]}, {query_labels[2]} 행을 모두 포함한다.",
            f"{query_labels[1]} 행만 실제 후보로 남는다.",
            "삼각형 표식이 있는 모든 행을 포함한다.",
        ),
        answer_choice=_counterfactual_answer_choice(seed_slot) if counterfactual else _base_answer_choice(seed_slot),
    )
    metadata_extra: dict[str, Any] = {"relevant_region_ids": tuple(item.public_id for item in choice_regions)}
    if counterfactual:
        metadata_extra.update({"pair_group": f"{FAMILY}:l1:s{seed_slot}", "variant": "counterfactual"})
    example_a = _rule_table(
        element_id="marker-l1-example-a",
        title="작동 예시 1",
        box=rect(84, 220, 512, 306),
        rows=example_rows[:3],
        subtitle="선택 프레임은 실제 후보를 보여 준다",
    )
    example_b = _rule_table(
        element_id="marker-l1-example-b",
        title="작동 예시 2",
        box=rect(646, 220, 512, 306),
        rows=[example_rows[0], example_rows[1], example_rows[3]],
        subtitle="같은 삼각형이라도 위치가 다르면 결과가 달라진다",
    )
    query_table = _rule_table(
        element_id="marker-l1-query",
        title="",
        box=rect(84, 294, 720, 242),
        rows=query_rows,
        subtitle="",
        show_result=False,
    )
    return episode(
        manifest=manifest,
        family_display_name=FAMILY_LABEL,
        question="예시와 범례, 반례를 함께 반영했을 때 현재 표에 대한 올바른 설명은 어느 선택지인가?",
        workbook_title="표식 위치 판정 워크북",
        sheets=[
            sheet(
                "examples",
                "예시",
                [
                    page(
                        "examples-p1",
                        "예시 시트",
                        elements=[example_a, example_b],
                        regions=(region("marker-l1-example-a-region", "example_table", "작동 예시 1", example_a.rect),),
                    )
                ],
            ),
            sheet("legend", "범례", [page("legend-p1", "범례 시트", elements=[_legend_table("marker-l1-legend", rect(236, 220, 808, 238), rule=rule, level=1)])]),
            sheet(
                "exception",
                "반례",
                [
                    page(
                        "exception-p1",
                        "반례 시트",
                        elements=[
                            _rule_table(
                                element_id="marker-l1-exception",
                                title="모양-only 반례",
                                box=rect(236, 212, 808, 286),
                                rows=[(labels[1], rule["exclude"], False), (labels[0], rule["include"], True)],
                                subtitle="삼각형 모양만 보면 두 행이 같아 보이지만 모서리 위치가 결과를 가른다",
                            )
                        ],
                    )
                ],
            ),
            sheet(
                "query",
                "질의",
                [page("query-p1", "질의 시트", elements=[*query_blocks, query_table, *choices], regions=choice_regions)],
            ),
        ],
        answer=answer_choice,
        seed_slot=seed_slot,
        metadata_extra=metadata_extra,
    )


def _build_group_level(manifest: TemplateManifest, seed_slot: int, *, level: int, counterfactual: bool = False):
    rule = _anchor_rule(seed_slot, counterfactual=counterfactual)
    query_rule = _anchor_rule(seed_slot, counterfactual=False)
    labels = rotate(("가람", "나래", "다온", "라온", "마루", "바다"), seed_slot)
    groups = ("1묶음", "2묶음")
    active_group = groups[seed_slot % 2]
    correct = labels[0] if active_group == groups[0] else labels[3]
    opposite = labels[1] if active_group == groups[0] else labels[4]
    expected = opposite if counterfactual else correct
    note_rows = [("메모-가", rule["hold"], False), ("메모-나", rule["review"], False)]
    query_groups = [
        (groups[0], [(labels[0], query_rule["include"], False), (labels[1], query_rule["exclude"], False), (labels[2], query_rule["review"], False)]),
        (groups[1], [(labels[3], query_rule["include"], False), (labels[4], query_rule["exclude"], False), (labels[5], None, False)]),
    ]
    examples_page_1 = _grouped_rule_table(
        element_id=f"marker-l{level}-example-a",
        title="작동 예시 1",
        box=rect(84, 218, 1074, 300),
        groups=[
            (groups[0], [(labels[0], rule["include"], True), (labels[1], rule["exclude"], False)]),
            (groups[1], [(labels[3], rule["include"], True), (labels[4], rule["exclude"], False)]),
        ],
        subtitle="같은 묶음 안에서도 모서리 위치가 실제 후보를 결정한다",
    )
    examples_pages = [
        page(
            "examples-p1",
            "예시 시트",
            elements=[examples_page_1],
            regions=(region(f"marker-l{level}-example-a-region", "example_table", "작동 예시 1", examples_page_1.rect),),
        ),
        page(
            "examples-p2",
            "보강 예시",
            elements=[
                _grouped_rule_table(
                    element_id=f"marker-l{level}-example-b",
                    title="작동 예시 2",
                    box=rect(84, 218, 1074, 300),
                    groups=[
                        (groups[0], [(labels[2], rule["review"], False), (labels[0], rule["include"], True)]),
                        (groups[1], [(labels[5], None, False), (labels[3], rule["include"], True)]),
                    ],
                    subtitle="행 순서가 바뀌어도 anchor 위치 규칙은 유지된다",
                )
            ],
        ),
    ]
    exception_pages = [
        page(
            "exception-p1",
            "반례 시트",
            elements=[
                _grouped_rule_table(
                    element_id=f"marker-l{level}-exception",
                    title="위치 반례",
                    box=rect(84, 206, 1074, 318),
                    groups=[
                        (groups[0], [(labels[1], rule["exclude"], False), (labels[0], rule["include"], True)]),
                        (groups[1], [(labels[4], rule["exclude"], False), (labels[3], rule["include"], True)]),
                    ],
                    subtitle="동일한 삼각형이지만 반대 모서리는 제외 후보로 처리된다",
                )
            ],
        )
    ]
    if level == 3:
        note_block = text_block(
            "marker-l3-note-block",
            "적용 범위 메모",
            rect(140, 184, 980, 160),
            (
                f"현재 질의에서는 {active_group} 안의 행만 판정한다.",
                "모서리별 의미는 범례와 반례 표의 판정 결과를 함께 맞춰야 한다.",
            ),
            style="note",
            subtitle="openable note",
        )
        exception_pages.append(
            page(
                "exception-p2",
                "범위 메모",
                elements=[
                    note_block,
                    _grouped_rule_table(
                        element_id="marker-l3-note-support",
                        title="메모 적용 예",
                        box=rect(140, 424, 980, 228),
                        groups=[
                            (active_group, note_rows),
                            ("다른 묶음", [("메모-다", rule["include"], False)]),
                        ],
                        subtitle="메모가 현재 묶음 범위만 고정한다",
                        show_result=False,
                    ),
                ],
                notes=(note(NOTE_ID, "적용 범위", f"질의 표에서는 {active_group} 행만 비교 범위에 넣는다. 표식의 의미는 범례 시트 기준을 따른다."),),
                regions=(region("marker-l3-note-region", "note_marker", "적용 범위 메모", note_block.rect, linked_note_id=NOTE_ID),),
            )
        )
    query_blocks, _ = _query_header(
        target=(f"현재 판정 묶음: {active_group}",),
        guidance=("예시, 범례, 반례가 같은 모서리 규칙을 가리키는지 확인합니다.",),
    )
    choices, choice_regions, answer_choice = _choice_cards(
        prefix=f"marker-l{level}-choice",
        correct_statement=f"{active_group}의 {expected} 행만 실제 후보로 남는다.",
        distractors=(
            f"{active_group}에서 삼각형 표식이 있는 모든 행을 포함한다.",
            f"{active_group}의 반대 모서리 표식 행만 실제 후보로 남는다.",
            "두 묶음의 실제 후보를 모두 포함한다.",
        ),
        answer_choice=_counterfactual_answer_choice(seed_slot) if counterfactual else _base_answer_choice(seed_slot),
    )
    metadata_extra: dict[str, Any] = {"relevant_region_ids": tuple(item.public_id for item in choice_regions)}
    if counterfactual:
        metadata_extra.update({"pair_group": f"{FAMILY}:l{level}:s{seed_slot}", "variant": "counterfactual"})
    query_table = _grouped_rule_table(
        element_id=f"marker-l{level}-query",
        title="",
        box=rect(84, 286, 720, 276),
        groups=query_groups,
        subtitle="",
        show_result=False,
    )
    return episode(
        manifest=manifest,
        family_display_name=FAMILY_LABEL,
        question="예시, 범례, 반례를 반영했을 때 현재 표에 대한 올바른 설명은 어느 선택지인가?",
        workbook_title="표식 위치 판정 워크북",
        sheets=[
            sheet("examples", "예시", examples_pages),
            sheet("legend", "범례", [page("legend-p1", "범례 시트", elements=[_legend_table(f"marker-l{level}-legend", rect(236, 190, 808, 334), rule=rule, level=level)])]),
            sheet("exception", "반례", exception_pages),
            sheet(
                "query",
                "질의",
                [
                    page(
                        "query-p1",
                        "질의 시트",
                        elements=[*query_blocks, query_table, *choices],
                        regions=choice_regions,
                    )
                ],
            ),
        ],
        answer=answer_choice,
        seed_slot=seed_slot,
        metadata_extra=metadata_extra,
    )


def build_episode(level: int, seed: int, *, template_id: str | None = None):
    manifest, seed_slot = resolve_template_seed(TEMPLATES_BY_LEVEL[level], seed, template_id=template_id)
    if level == 1:
        return _build_level_1(manifest, seed_slot)
    return _build_group_level(manifest, seed_slot, level=level)


def build_counterfactual_episode(level: int, seed: int):
    manifest, seed_slot = resolve_template_seed(TEMPLATES_BY_LEVEL[level], seed, template_id=TEMPLATE_ID)
    if level == 1:
        return _build_level_1(manifest, seed_slot, counterfactual=True)
    return _build_group_level(manifest, seed_slot, level=level, counterfactual=True)
