"""Interaction-critical eval_hard episode builders."""

from __future__ import annotations

from typing import Any

from table_env_bench.data.models import AnswerSpec, EpisodeSpec
from table_env_bench.data.families.shared import (
    ChoiceCardSpec,
    TemplateManifest,
    choice_cards,
    episode,
    legend,
    make_banded_table,
    note,
    page,
    rect,
    region,
    rotate,
    sheet,
    text_block,
)

HARD_LEVELS = (2, 3)
SEEDS_PER_TEMPLATE = 8


def _triangle(anchor: str, *, color: str = "#0f766e") -> dict[str, Any]:
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


def _hard_manifest(
    family: str,
    level: int,
    variant: str,
    *,
    label: str,
    answer_form: str,
    cue_tags: tuple[str, ...],
    operator_tags: tuple[str, ...],
    required_sheet_ids: tuple[str, ...],
    required_page_refs: tuple[str, ...],
    required_actions: tuple[str, ...],
    required_evidence: tuple[dict[str, Any], ...],
    shortcut_probes: tuple[str, ...],
    holdout_group: str,
) -> TemplateManifest:
    expected_steps = (5, 5) if level == 2 else (5, 6)
    if family == "channel_policy_transfer":
        task_archetype = "review_verification"
        scenario_context = "선행 검토 사례와 부록 메모를 함께 읽고 현재 표의 실제 처리 대상을 확정하는 하드 검토 과업이다."
    else:
        task_archetype = "scope_reconciliation"
        scenario_context = "개요 표와 보조 메모를 함께 읽고 반복 라벨과 소계 경계를 맞춰 실제 범위를 확정하는 하드 검토 과업이다."
    return TemplateManifest(
        family=family,
        level=level,
        template_id=f"evalhard_l{level}_{variant}",
        template_label=label,
        task_archetype=task_archetype,
        scenario_context=scenario_context,
        latent_rule="한 페이지 shortcut으로는 풀 수 없고, 보조 evidence를 반드시 읽어야 한다.",
        operator_tags=operator_tags,
        cue_tags=cue_tags,
        answer_form=answer_form,
        primary_operator=operator_tags[0],
        support_operator=operator_tags[1] if len(operator_tags) > 1 else None,
        required_visual_cues=cue_tags,
        required_surfaces=("table_panel", "note_card", "answer_choice_panel"),
        capability_axes=("visual_grounding", "navigation", "disambiguation"),
        required_sheet_ids=required_sheet_ids,
        required_page_refs=required_page_refs,
        allowed_cue_variants=cue_tags,
        distractor_policy="base와 counterfactual은 레이아웃은 유지하되, 핵심 cue 하나만 바꿔 정답을 뒤집는다.",
        level_rationale="eval_hard는 base canonical보다 한 단계 높은 탐색 요구를 강제하며, 최소 두 surface 이상의 decisive evidence를 읽어야 한다.",
        text_only_failure_modes=(
            "단일 페이지나 단일 surface만 읽는 shortcut으로는 정답을 확정할 수 없다.",
            "note 또는 보조 evidence를 생략하면 counterfactual pair를 구분하지 못한다.",
        ),
        distractor_failure_modes=(
            "핵심 cue 하나를 바꿨을 때 이전 규칙을 그대로 유지하는 오답",
            "required evidence를 보지 않고 가장 가까운 visible cue만 따라가는 오답",
        ),
        level_knobs={"level": level, "variant": variant},
        max_actions=11 if level == 2 else 12,
        difficulty_tier="eval_hard",
        required_capabilities=("navigation", "disambiguation", "scope_resolution", "operator_composition"),
        required_actions=required_actions,
        required_evidence=required_evidence,
        expected_min_steps=expected_steps[0],
        expected_reasoning_steps=expected_steps,
        shortcut_probes=shortcut_probes,
        holdout_group=holdout_group,
        pair_group=holdout_group,
        variant=variant,
    )


def list_hard_manifests(family: str, level: int) -> tuple[TemplateManifest, ...]:
    if level not in HARD_LEVELS:
        return ()
    base_group = f"{family}:l{level}:hard_pair"
    if family == "channel_policy_transfer":
        return (
            _hard_manifest(
                family,
                level,
                "base",
                label="하드 예시 전이 (base)",
                answer_form="cell_choice",
                cue_tags=("band_scope", "icon_anchor", "row_group_band", "note_scope"),
                operator_tags=("select_scope", "transfer"),
                required_sheet_ids=("examples", "appendix", "query"),
                required_page_refs=("examples:examples-p2", "appendix:appendix-p1", "query:query-p1"),
                required_actions=("must_switch_sheet", "must_open_note"),
                required_evidence=(
                    {"kind": "page", "sheet_id": "examples", "page_id": "examples-p2"},
                    {"kind": "page", "sheet_id": "appendix", "page_id": "appendix-p1"},
                    {"kind": "note", "sheet_id": "appendix", "page_id": "appendix-p1", "note_id": "rule-note"},
                ),
                shortcut_probes=("single_page", "query_only", "no_appendix"),
                holdout_group=base_group,
            ),
            _hard_manifest(
                family,
                level,
                "counterfactual",
                label="하드 예시 전이 (counterfactual)",
                answer_form="cell_choice",
                cue_tags=("band_scope", "icon_anchor", "row_group_band", "note_scope"),
                operator_tags=("select_scope", "transfer"),
                required_sheet_ids=("examples", "appendix", "query"),
                required_page_refs=("examples:examples-p2", "appendix:appendix-p1", "query:query-p1"),
                required_actions=("must_switch_sheet", "must_open_note"),
                required_evidence=(
                    {"kind": "page", "sheet_id": "examples", "page_id": "examples-p2"},
                    {"kind": "page", "sheet_id": "appendix", "page_id": "appendix-p1"},
                    {"kind": "note", "sheet_id": "appendix", "page_id": "appendix-p1", "note_id": "rule-note"},
                ),
                shortcut_probes=("single_page", "query_only", "no_appendix"),
                holdout_group=base_group,
            ),
        )
    if family in {
        "excel_viewport_sheet_navigation",
        "inventory_exception_disambiguation",
        "marker_position_rule_transfer",
    }:
        return ()
    if family != "report_scope_reconciliation":
        raise KeyError(f"Unknown eval_hard family: {family}")
    return (
        _hard_manifest(
            family,
            level,
            "base",
            label="하드 계층 범위 (base)",
            answer_form="row_label_choice",
            cue_tags=("merged_header_scope", "indentation_depth", "subtotal_block"),
            operator_tags=("scope_resolution", "classify"),
            required_sheet_ids=("overview", "notes", "query"),
            required_page_refs=("overview:overview-p1", "notes:notes-p1", "query:query-p1"),
            required_actions=("must_switch_sheet", "must_open_note"),
            required_evidence=(
                {"kind": "page", "sheet_id": "notes", "page_id": "notes-p1"},
                {"kind": "note", "sheet_id": "notes", "page_id": "notes-p1", "note_id": "scope-note"},
            ),
            shortcut_probes=("single_page", "text_scrape_only"),
            holdout_group=base_group,
        ),
        _hard_manifest(
            family,
            level,
            "counterfactual",
            label="하드 계층 범위 (counterfactual)",
            answer_form="row_label_choice",
            cue_tags=("merged_header_scope", "indentation_depth", "subtotal_block"),
            operator_tags=("scope_resolution", "classify"),
            required_sheet_ids=("overview", "notes", "query"),
            required_page_refs=("overview:overview-p1", "notes:notes-p1", "query:query-p1"),
            required_actions=("must_switch_sheet", "must_open_note"),
            required_evidence=(
                {"kind": "page", "sheet_id": "notes", "page_id": "notes-p1"},
                {"kind": "note", "sheet_id": "notes", "page_id": "notes-p1", "note_id": "scope-note"},
            ),
            shortcut_probes=("single_page", "text_scrape_only"),
            holdout_group=base_group,
        ),
    )


def _resolve_hard_manifest(family: str, level: int, template_id: str) -> TemplateManifest:
    for manifest in list_hard_manifests(family, level):
        if manifest.template_id == template_id:
            return manifest
    raise KeyError(f"Unknown eval_hard template {template_id} for {family} level {level}")


def build_hard_episode(family: str, level: int, seed: int, template_id: str) -> EpisodeSpec:
    manifest = _resolve_hard_manifest(family, level, template_id)
    seed_slot = seed % SEEDS_PER_TEMPLATE
    variant = manifest.variant or "base"
    if family == "channel_policy_transfer":
        return _build_channel_policy_transfer_hard(manifest, seed_slot, variant)
    if family != "report_scope_reconciliation":
        raise KeyError(f"Unknown eval_hard family: {family}")
    return _build_hierarchical_hard(manifest, seed_slot, variant)


def _build_channel_policy_transfer_hard(manifest: TemplateManifest, seed_slot: int, variant: str) -> EpisodeSpec:
    names = rotate(("하나", "둘", "셋", "넷", "다섯"), seed_slot)[:4]
    focus_band = "검토"
    bands = ("기본", "검토")
    note_anchor = "top_right" if variant == "base" else "bottom_left"
    answer_choice = "B" if variant == "base" else "C"

    def _values(correct_row: int) -> list[list[list[str | dict[str, Any]]]]:
        values: list[list[list[str | dict[str, Any]]]] = []
        for row_index, _name in enumerate(names):
            row_cells = []
            for band_index, band in enumerate(bands):
                band_cells: list[str | dict[str, Any]] = [{"text": "", "metadata": {}}, {"text": "", "metadata": {}}]
                if band == focus_band and row_index == correct_row:
                    band_cells[1] = {"text": "", "metadata": _triangle(note_anchor)}
                elif row_index == (correct_row + 1) % len(names) and band == focus_band:
                    band_cells[1] = {"text": "", "metadata": _triangle("top_right" if note_anchor == "bottom_left" else "bottom_left")}
                elif row_index == (correct_row + 2) % len(names) and band != focus_band:
                    band_cells[1] = {"text": "", "metadata": _triangle(note_anchor)}
                row_cells.append(band_cells)
            values.append(row_cells)
        return values

    example_1 = make_banded_table(
        element_id="hard-transfer-example-1",
        title="예시 1",
        box=rect(84, 184, 520, 262),
        band_labels=bands,
        sub_headers=("상태", "조치"),
        row_labels=tuple(names),
        values=_values(1),
        subtitle="예시 1만 보면 모서리 방향이 불안정하다",
    )
    example_2 = make_banded_table(
        element_id="hard-transfer-example-2",
        title="예시 2",
        box=rect(634, 184, 520, 262),
        band_labels=bands,
        sub_headers=("상태", "조치"),
        row_labels=tuple(names),
        values=_values(2),
        subtitle="두 번째 예시가 active band를 다시 고정한다",
    )
    examples_p2_note = text_block(
        "hard-transfer-hint",
        "보강 예시",
        rect(118, 214, 960, 150),
        (
            "검토 밴드에서는 appendix note가 모서리 방향을 최종 고정합니다.",
            "같은 삼각형이 기본 밴드에도 반복되므로 query는 한 페이지로 찍기 어렵습니다.",
        ),
        style="note",
        subtitle="예시 보강",
    )
    appendix_page = page(
        "appendix-p1",
        "부록 규칙",
        elements=[
            text_block(
                "appendix-note-block",
                "부록 메모",
                rect(160, 214, 900, 220),
                (
                    f"rule-note: 검토 밴드의 실제 후보는 {note_anchor} 삼각형만 해당합니다.",
                    "같은 위치가 기본 밴드에 보이면 distractor이며 정답이 아닙니다.",
                ),
                style="note",
                subtitle="appendix",
            )
        ],
        notes=(note("rule-note", "부록 규칙", f"검토 밴드의 후보는 {note_anchor} 삼각형만 해당한다."),),
        regions=(region("appendix-note-region", "note_marker", "부록 메모", rect(160, 214, 900, 220), linked_note_id="rule-note"),),
    )
    query_table = make_banded_table(
        element_id="hard-transfer-query",
        title="질의 표",
        box=rect(84, 182, 720, 300),
        band_labels=bands,
        sub_headers=("상태", "조치"),
        row_labels=tuple(names),
        values=_values(1),
        subtitle="부록 규칙을 읽어야 정답이 고정된다",
    )
    choices, choice_regions = choice_cards(
        prefix="hard-transfer-choice",
        answer_form="cell_choice",
        cards=(
            ChoiceCardSpec("A", f"{names[0]} / 검토-조치", ("첫 예시만 보고 고르기 쉬운 위치",)),
            ChoiceCardSpec("B", f"{names[1]} / 검토-조치", ("appendix note가 top_right일 때 정답",)),
            ChoiceCardSpec("C", f"{names[2]} / 검토-조치", ("appendix note가 bottom_left일 때 정답",)),
            ChoiceCardSpec("D", f"{names[3]} / 기본-조치", ("active band를 놓친 오답",)),
        ),
    )
    return episode(
        manifest=manifest,
        family_display_name="예시 규칙 전이",
        question="예시 보강 페이지와 부록 메모까지 읽었을 때 질의 표의 정답 위치는 어느 선택지인가?",
        workbook_title="하드 예시 규칙 전이",
        sheets=[
            sheet("examples", "예시", [page("examples-p1", "예시 시트", elements=[example_1, example_2], regions=(region("hard-transfer-example-1", "evidence_panel", "예시 표 1", example_1.rect), region("hard-transfer-example-2", "evidence_panel", "예시 표 2", example_2.rect))), page("examples-p2", "보강 예시", elements=[examples_p2_note], regions=(region("hard-transfer-hint", "evidence_panel", "보강 예시", examples_p2_note.rect),))]),
            sheet("appendix", "부록", [appendix_page]),
            sheet("query", "질의", [page("query-p1", "질의 시트", elements=[text_block("hard-transfer-focus", "현재 대상", rect(84, 132, 220, 40), (focus_band,), style="callout", subtitle="질의"), query_table, *choices], regions=(region("hard-transfer-query", "evidence_panel", "질의 표", query_table.rect), *choice_regions))]),
        ],
        answer=AnswerSpec(canonical=answer_choice, accepted=(answer_choice.lower(),), normalizer="basic"),
        seed_slot=seed_slot,
        metadata_extra={"relevant_region_ids": ("hard-transfer-hint", "appendix-note-region", "hard-transfer-query")},
    )


def _build_exception_hard(manifest: TemplateManifest, seed_slot: int, variant: str) -> EpisodeSpec:
    names = rotate(("가람", "나래", "다온", "라온"), seed_slot)[:4]
    answer_choice = "B" if variant == "base" else "C"
    decisive_icon_rows = (names[1], names[3]) if variant == "base" else (names[2], names[3])

    def _values(pattern_rows: tuple[str, ...], icon_rows: tuple[str, ...], framed_rows: tuple[str, ...]) -> list[list[list[str | dict[str, Any]]]]:
        rows: list[list[list[str | dict[str, Any]]]] = []
        for name in names:
            rows.append(
                [
                    [{"text": name, "style": "row_label", "align": "left", "metadata": _frame() if name in framed_rows else {}}, {"text": "", "style": "muted"}],
                    [
                        {"text": "", "metadata": _stripe() if name in pattern_rows else {}},
                        {"text": "", "metadata": _triangle("top_right") if name in icon_rows else {}},
                    ],
                ]
            )
        return rows

    example_table = make_banded_table(
        element_id="hard-counter-example",
        title="예시",
        box=rect(84, 184, 720, 280),
        band_labels=("행", "표식"),
        sub_headers=("이름", "비고"),
        row_labels=tuple(names),
        values=_values((names[0], names[2]), (names[0], names[2]), (names[0], names[2])),
        subtitle="예시만 보면 줄무늬와 아이콘 가설이 둘 다 그럴듯하다",
    )
    weak_exception = text_block(
        "hard-counter-weak",
        "약한 예외 사례",
        rect(118, 214, 960, 150),
        (
            "약한 반례에서는 줄무늬와 아이콘이 아직 일부 겹쳐 있습니다.",
            "그래서 결정적 예외 사례 페이지까지 봐야 가설이 하나로 줄어듭니다.",
        ),
        style="note",
        subtitle="weak exception",
    )
    decisive_table = make_banded_table(
        element_id="hard-counter-decisive",
        title="결정적 반례",
        box=rect(84, 184, 720, 280),
        band_labels=("행", "표식"),
        sub_headers=("이름", "비고"),
        row_labels=tuple(names),
        values=_values((names[0], names[2]), decisive_icon_rows, decisive_icon_rows),
        subtitle="여기서만 pattern과 icon의 정답이 분리된다",
    )
    query_table = make_banded_table(
        element_id="hard-counter-query",
        title="질의 표",
        box=rect(84, 184, 720, 280),
        band_labels=("행", "표식"),
        sub_headers=("이름", "비고"),
        row_labels=tuple(names),
        values=_values((names[0], names[3]), decisive_icon_rows, ()),
        subtitle="반례를 무시하면 틀린 설명이 계속 그럴듯하게 남는다",
    )
    choices, choice_regions = choice_cards(
        prefix="hard-counter-choice",
        answer_form="statement_choice",
        cards=(
            ChoiceCardSpec("A", "줄무늬 행만 선택된다", ("예시만 보고 유지하기 쉬운 오답",)),
            ChoiceCardSpec("B", f"{decisive_icon_rows[0]} / {decisive_icon_rows[1]} 행이 선택된다", ("base variant 정답",)),
            ChoiceCardSpec("C", f"{names[2]} / {names[3]} 행이 선택된다", ("counterfactual variant 정답",)),
            ChoiceCardSpec("D", "표식은 정답과 무관하다", ("반례 페이지를 무시한 오답",)),
        ),
    )
    return episode(
        manifest=manifest,
        family_display_name="반례 기반 규칙 구분",
        question="약한 반례와 결정적 반례까지 모두 반영했을 때 맞는 설명은 어느 선택지인가?",
        workbook_title="하드 예외 사례 구분",
        sheets=[
            sheet("examples", "예시", [page("examples-p1", "예시 시트", elements=[example_table], regions=(region("hard-counter-example", "evidence_panel", "예시 표", example_table.rect),))]),
            sheet("exception", "예외", [page("exception-p1", "약한 예외 사례", elements=[weak_exception], regions=(region("hard-counter-weak", "evidence_panel", "약한 예외 사례", weak_exception.rect),)), page("exception-p2", "결정적 예외 사례", elements=[decisive_table], regions=(region("hard-counter-decisive", "evidence_panel", "결정적 예외 사례", decisive_table.rect),))]),
            sheet("query", "질의", [page("query-p1", "질의 시트", elements=[query_table, *choices], regions=(region("hard-counter-query", "evidence_panel", "질의 표", query_table.rect), *choice_regions))]),
        ],
        answer=AnswerSpec(canonical=answer_choice, accepted=(answer_choice.lower(),), normalizer="basic"),
        seed_slot=seed_slot,
        metadata_extra={"relevant_region_ids": ("hard-counter-weak", "hard-counter-decisive", "hard-counter-query")},
    )


def _build_hierarchical_hard(manifest: TemplateManifest, seed_slot: int, variant: str) -> EpisodeSpec:
    teams = rotate(("북부 1팀", "북부 2팀", "남부 1팀", "남부 2팀"), seed_slot)
    header_target = "상반기-매출" if variant == "base" else "하반기-매출"
    answer_choice = "B" if variant == "base" else "C"
    rows = ("북부", f"  {teams[0]}", f"  {teams[1]}", "소계 북부", "남부", f"  {teams[2]}", f"  {teams[3]}", "소계 남부")

    def _values() -> list[list[list[str | dict[str, Any]]]]:
        values: list[list[list[str | dict[str, Any]]]] = []
        for row in rows:
            if row.startswith("소계"):
                values.append(
                    [
                        [{"text": "", "style": "muted"}, {"text": "24", "style": "total"}],
                        [{"text": "", "style": "muted"}, {"text": "28", "style": "total"}],
                    ]
                )
            else:
                display = "" if row in {"북부", "남부"} else row.strip()
                values.append(
                    [
                        [{"text": display, "style": "muted" if row in {"북부", "남부"} else "body", "align": "left"}, {"text": str(10 + rows.index(row)), "style": "numeric"}],
                        [{"text": display, "style": "muted" if row in {"북부", "남부"} else "body", "align": "left"}, {"text": str(20 + rows.index(row)), "style": "numeric"}],
                    ]
                )
        return values

    overview = make_banded_table(
        element_id="hard-hier-overview",
        title="요약 표",
        box=rect(84, 184, 1040, 346),
        band_labels=("상반기", "하반기"),
        sub_headers=("구간", "매출"),
        row_labels=rows,
        values=_values(),
        subtitle="헤더 깊이와 행 들여쓰기를 함께 읽어야 한다",
    )
    notes_page = page(
        "notes-p1",
        "범위 메모",
        elements=[
            text_block(
                "hard-hier-note-block",
                "범위 규칙",
                rect(130, 224, 960, 180),
                (
                    "scope-note: 들여쓰기된 팀 행만 query 답 후보입니다.",
                    f"이번 variant에서는 {header_target} 열만 정답 범위로 인정합니다.",
                ),
                style="note",
                subtitle="scope note",
            )
        ],
        notes=(note("scope-note", "범위 규칙", f"{header_target} 열만 정답 범위로 인정한다."),),
        regions=(region("hard-hier-note-region", "note_marker", "범위 메모", rect(130, 224, 960, 180), linked_note_id="scope-note"),),
    )
    choices, choice_regions = choice_cards(
        prefix="hard-hier-choice",
        answer_form="row_label_choice",
        cards=(
            ChoiceCardSpec("A", teams[0], ("북부 1팀",)),
            ChoiceCardSpec("B", teams[1], ("base variant에서만 범위가 맞는 팀",)),
            ChoiceCardSpec("C", teams[3], ("counterfactual variant에서만 범위가 맞는 팀",)),
            ChoiceCardSpec("D", "소계 북부", ("소계 블록을 데이터 행으로 오해한 오답",)),
        ),
    )
    return episode(
        manifest=manifest,
        family_display_name="계층 헤더/행 그룹 추론",
        question=f"개요 표와 범위 메모를 함께 읽었을 때 {header_target} 범위에 해당하는 팀은 어느 선택지인가?",
        workbook_title="하드 계층 범위",
        sheets=[
            sheet("overview", "개요", [page("overview-p1", "개요 시트", elements=[overview], regions=(region("hard-hier-overview", "evidence_panel", "개요 표", overview.rect),))]),
            sheet("notes", "메모", [notes_page]),
            sheet("query", "질의", [page("query-p1", "질의 시트", elements=[text_block("hard-hier-target", "목표 헤더", rect(84, 136, 280, 40), (header_target,), style="callout", subtitle="질의"), *choices], regions=choice_regions)]),
        ],
        answer=AnswerSpec(canonical=answer_choice, accepted=(answer_choice.lower(),), normalizer="basic"),
        seed_slot=seed_slot,
        metadata_extra={"relevant_region_ids": ("hard-hier-overview", "hard-hier-note-region")},
    )


def _build_legend_hard(manifest: TemplateManifest, seed_slot: int, variant: str) -> EpisodeSpec:
    items = rotate(("청", "록", "주", "황"), seed_slot)
    order_hint = "포함 후 제외" if variant == "base" else "제외 후 포함"
    answer_choice = "B" if variant == "base" else "C"

    def _values(include_rows: tuple[str, ...], exclude_rows: tuple[str, ...]) -> list[list[list[str | dict[str, Any]]]]:
        rows: list[list[list[str | dict[str, Any]]]] = []
        for item in items:
            rows.append(
                [
                    [{"text": item, "style": "row_label", "align": "left"}, {"text": "", "style": "muted"}],
                    [
                        {"text": "", "metadata": _triangle("top_right") if item in include_rows else {}},
                        {"text": "", "metadata": _stripe() if item in exclude_rows else {}},
                    ],
                ]
            )
        return rows

    legend_page = page(
        "legend-p1",
        "범례 시트",
        elements=[
            legend("hard-legend", "연산 범례", rect(84, 190, 420, 220), (("삼각형 = 후보 포함", "#0f766e"), ("줄무늬 = 제외", "#f97316")), subtitle="legend"),
            text_block("hard-legend-order", "적용 순서", rect(546, 208, 570, 160), (f"이번 variant의 worked example 순서는 {order_hint} 입니다.", "예시 페이지를 보지 않으면 순서를 확정할 수 없습니다."), style="note", subtitle="operator order"),
        ],
        regions=(region("hard-legend", "evidence_panel", "범례", rect(84, 190, 420, 220)), region("hard-legend-order", "evidence_panel", "적용 순서", rect(546, 208, 570, 160))),
    )
    examples_page_1 = page(
        "examples-p1",
        "worked example",
        elements=[
            make_banded_table(
                element_id="hard-legend-worked",
                title="worked example",
                box=rect(84, 184, 720, 280),
                band_labels=("행", "표식"),
                sub_headers=("이름", "메모"),
                row_labels=tuple(items),
                values=_values((items[0], items[1], items[3]), (items[1],)),
                subtitle="예시 결과는 operator order를 보여 주지만 query와 동일하지는 않다",
            )
        ],
        regions=(region("hard-legend-worked", "evidence_panel", "worked example", rect(84, 184, 720, 280)),),
    )
    examples_page_2 = page(
        "examples-p2",
        "보강 예시",
        elements=[
            text_block(
                "hard-legend-note",
                "보강 예시",
                rect(120, 220, 960, 160),
                (
                    "예시 순서는 query에도 그대로 적용되지만, 최종 남는 행은 배치에 따라 달라집니다.",
                    "범례만 보면 포함/제외 의미는 알 수 있어도 순서까지는 못 고정합니다.",
                ),
                style="note",
                subtitle="worked example note",
            )
        ],
        regions=(region("hard-legend-note", "evidence_panel", "보강 예시", rect(120, 220, 960, 160)),),
    )
    query = make_banded_table(
        element_id="hard-legend-query",
        title="질의 표",
        box=rect(84, 184, 720, 280),
        band_labels=("행", "표식"),
        sub_headers=("이름", "메모"),
        row_labels=tuple(items),
        values=_values((items[0], items[2], items[3]), (items[2],)),
        subtitle="worked example 순서를 읽어야 미리보기 정답이 정해진다",
    )
    choices, choice_regions = choice_cards(
        prefix="hard-legend-choice",
        answer_form="mini_table_choice",
        cards=(
            ChoiceCardSpec("A", f"{items[0]} + {items[2]}", ("포함만 보고 고른 결과",)),
            ChoiceCardSpec("B", f"{items[0]} + {items[3]}", ("base variant 정답",)),
            ChoiceCardSpec("C", f"{items[2]} + {items[3]}", ("counterfactual variant 정답",)),
            ChoiceCardSpec("D", f"{items[3]}만", ("순서를 과도하게 좁힌 결과",)),
        ),
    )
    return episode(
        manifest=manifest,
        family_display_name="범례/연산 조합",
        question="범례와 worked example 두 페이지를 모두 반영했을 때 query와 맞는 미리보기는 어느 선택지인가?",
        workbook_title="하드 범례 연산",
        sheets=[
            sheet("legend", "범례", [legend_page]),
            sheet("examples", "예시", [examples_page_1, examples_page_2]),
            sheet("query", "질의", [page("query-p1", "질의 시트", elements=[query, *choices], regions=(region("hard-legend-query", "evidence_panel", "질의 표", query.rect), *choice_regions))]),
        ],
        answer=AnswerSpec(canonical=answer_choice, accepted=(answer_choice.lower(),), normalizer="basic"),
        seed_slot=seed_slot,
        metadata_extra={"relevant_region_ids": ("hard-legend", "hard-legend-note", "hard-legend-query")},
    )
