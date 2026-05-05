"""계층 머리글과 행 묶음을 읽는 canonical family."""

from __future__ import annotations

from table_env_bench.data.models import AnswerSpec
from table_env_bench.data.families.shared import (
    ChoiceCardSpec,
    TemplateManifest,
    episode,
    make_banded_table,
    page,
    query_choice_cards,
    query_header_blocks,
    rect,
    region,
    resolve_template_seed,
    rotate,
    sheet,
    text_block,
)

FAMILY = "report_scope_reconciliation"
FAMILY_LABEL = "보고 범위 판정"
REGIONS = ("북부", "중부", "남부")
TEAM_LABELS = ("1팀", "2팀", "3팀")
PERIODS = ("상반기", "하반기")
SUB_HEADERS = ("구간", "매출", "마진")
STATE_LABELS = ("집중", "유지", "검토")

_LEVEL_REASONING_STEPS = {1: (2, 3), 2: (3, 4), 3: (4, 5)}
_LEVEL_RATIONALES = {
    1: "반복 라벨이 있는 보고표에서 올바른 집계 범위를 읽어 답을 고르는 2-3단계 문제다.",
    2: "소계와 기준 메모가 함께 나와 3-4단계 수준의 범위 확정이 필요한 문제다.",
    3: "같은 팀 라벨과 항목이 여러 블록에 반복되어 4-5단계 수준의 구조 판정이 필요한 문제다.",
}
_TEMPLATE_QUALITY = {
    "merged_scope_cell": {
        "primary_operator": "select_scope",
        "support_operator": "match",
        "required_visual_cues": ("merged_header_scope", "indentation_depth"),
        "text_only_failure_modes": (
            "같은 1팀/2팀/3팀 라벨이 지역마다 반복되고 매출·마진 열도 상/하반기 아래에서 반복되어 텍스트만으로는 정답 셀을 확정할 수 없다.",
            "Level 2 이상에서는 소계·총계와 데이터 행이 함께 들어와 기준 메모 없이 범위를 텍스트로만 읽으면 머리글 범위를 자주 놓친다.",
        ),
        "distractor_failure_modes": (
            "같은 팀이지만 다른 지역 셀을 고르는 오답",
            "같은 팀·같은 반기지만 마진 열이나 소계 행을 데이터 셀로 착각하는 오답",
        ),
    },
    "grouped_statement": {
        "primary_operator": "verify_statement",
        "support_operator": "scope_resolution",
        "required_visual_cues": ("subtotal_block", "indentation_depth"),
        "text_only_failure_modes": (
            "소계 블록과 들여쓰기 경계를 무시하면 특정 지역 소계와 전체 합계 범위를 문장만으로는 분리하기 어렵다.",
            "기준 메모 카드 없이 바로 위아래만 따라가면 3개 팀 묶음인지, 지역 소계인지, 전체 합계인지 확정하기 어렵다.",
        ),
        "distractor_failure_modes": (
            "특정 지역 소계를 모든 지역 합이나 바로 위 한 팀 복사로 오해하는 오답",
            "매출과 마진 열을 함께 섞어 읽거나 전체 합계를 소계와 동일시하는 오답",
        ),
    },
    "subtotal_row_label": {
        "primary_operator": "classify",
        "support_operator": "scope_resolution",
        "required_visual_cues": ("subtotal_block", "merged_header_scope"),
        "text_only_failure_modes": (
            "소계 라벨만 읽고 실제로 어떤 데이터 행이 묶이는지 보지 않으면 지역별 3팀 묶음과 총계 묶음을 확정할 수 없다.",
            "같은 팀 이름이 모든 지역에 반복되어 머리글과 행 묶음을 함께 읽지 않으면 선택지가 여러 개 살아 남는다.",
        ),
        "distractor_failure_modes": (
            "특정 지역 3팀 대신 다른 지역 3팀을 고르는 오답",
            "지역 소계와 전체 총계를 혼동해 모든 팀 묶음을 너무 일찍 고르는 오답",
        ),
    },
}


def _manifest(level: int, template_id: str, label: str, *, answer_form: str, operator_tags: tuple[str, ...], cue_tags: tuple[str, ...], max_actions: int) -> TemplateManifest:
    quality = _TEMPLATE_QUALITY[template_id]
    page_refs = ("overview:overview-p1", "query:query-p1")
    required_surfaces = ("table_panel", "answer_choice_panel")
    required_actions = ("must_read_group_scope",)
    required_evidence = (
        {"kind": "page", "sheet_id": "overview", "page_id": "overview-p1"},
        {"kind": "page", "sheet_id": "query", "page_id": "query-p1"},
    )
    if level >= 2:
        page_refs = (*page_refs, "notes:notes-p1")
        required_surfaces = (*required_surfaces, "note_card")
        required_actions = (*required_actions, "must_open_note")
        required_evidence = (
            *required_evidence,
            {"kind": "page", "sheet_id": "notes", "page_id": "notes-p1"},
            {"kind": "note", "sheet_id": "notes", "page_id": "notes-p1", "note_id": "scope-note"},
        )
    return TemplateManifest(
        family=FAMILY,
        level=level,
        template_id=template_id,
        template_label=label,
        task_archetype="scope_reconciliation",
        scenario_context="밀도 높은 실적 보고표에서 반복 라벨과 소계 경계를 맞춰 실제 보고 범위를 확정하는 과업이다.",
        latent_rule="반복 팀 라벨과 다층 소계가 있는 밀도 높은 표에서 머리글과 행 묶음 구조가 실제 범위를 결정한다.",
        operator_tags=operator_tags,
        cue_tags=cue_tags,
        answer_form=answer_form,
        primary_operator=quality["primary_operator"],
        support_operator=quality["support_operator"],
        required_visual_cues=quality["required_visual_cues"],
        required_surfaces=required_surfaces,
        capability_axes=("visual_grounding", "scope_resolution", "navigation"),
        benchmark_track="canonical_real_tableqa",
        reasoning_archetype="compose_apply",
        abstraction_tier="abstract_worksheet",
        support_surface_policy="optional",
        qa_dependency="hybrid_induction_tableqa",
        generalization_group=f"{FAMILY}:{template_id}:l{level}",
        required_sheet_ids=("overview", "query") if level == 1 else ("overview", "notes", "query"),
        required_page_refs=page_refs,
        allowed_cue_variants=("merged_header_scope", "indentation_depth", "subtotal_block"),
        distractor_policy="같은 팀 이름과 비슷한 수치가 다른 지역, 다른 반기, 다른 항목 아래에도 반복되게 두어 범위를 틀리게 읽게 만든다.",
        level_rationale=_LEVEL_RATIONALES[level],
        text_only_failure_modes=quality["text_only_failure_modes"],
        distractor_failure_modes=quality["distractor_failure_modes"],
        level_knobs={"level": level, "density_profile": "3_regions_3_teams_2_metrics"},
        max_actions=max_actions,
        required_actions=required_actions,
        required_evidence=required_evidence,
        expected_min_steps=_LEVEL_REASONING_STEPS[level][0],
        expected_reasoning_steps=_LEVEL_REASONING_STEPS[level],
        shortcut_probes=("text_scrape_only", "ignore_hierarchy"),
    )


TEMPLATES_BY_LEVEL: dict[int, tuple[TemplateManifest, ...]] = {
    level: (
        _manifest(level, "merged_scope_cell", "중첩 머리글의 대상 칸 찾기", answer_form="cell_choice", operator_tags=("select_scope", "match"), cue_tags=("merged_header_scope", "indentation_depth"), max_actions=8 + level),
        _manifest(level, "grouped_statement", "소계 범위 진술 검증", answer_form="statement_choice", operator_tags=("verify_statement", "scope_resolution"), cue_tags=("subtotal_block", "indentation_depth"), max_actions=8 + level),
        _manifest(level, "subtotal_row_label", "소계가 가리키는 행 묶음 찾기", answer_form="row_label_choice", operator_tags=("classify", "scope_resolution"), cue_tags=("subtotal_block", "merged_header_scope"), max_actions=8 + level),
    )
    for level in (1, 2, 3)
}


def list_manifests(level: int) -> tuple[TemplateManifest, ...]:
    return TEMPLATES_BY_LEVEL[level]


def build_episode(level: int, seed: int, *, template_id: str | None = None):
    manifest, seed_slot = resolve_template_seed(TEMPLATES_BY_LEVEL[level], seed, template_id=template_id)
    if manifest.template_id == "merged_scope_cell":
        return _build_merged_scope_episode(manifest, seed_slot)
    if manifest.template_id == "grouped_statement":
        return _build_grouped_statement_episode(manifest, seed_slot)
    return _build_subtotal_row_label_episode(manifest, seed_slot)


def _region_order(seed_slot: int) -> tuple[str, ...]:
    return rotate(REGIONS, seed_slot % len(REGIONS))


def _team_order(seed_slot: int) -> tuple[str, ...]:
    return rotate(TEAM_LABELS, seed_slot % len(TEAM_LABELS))


def _row_specs(seed_slot: int) -> tuple[tuple[str, str | None, str | None], ...]:
    specs: list[tuple[str, str | None, str | None]] = []
    for region in _region_order(seed_slot):
        specs.append(("region", region, None))
        for team in _team_order(seed_slot):
            specs.append(("team", region, team))
        specs.append(("subtotal", region, None))
    specs.append(("grand_total", None, None))
    return tuple(specs)


def _row_labels(seed_slot: int) -> tuple[str, ...]:
    labels: list[str] = []
    for kind, region, team in _row_specs(seed_slot):
        if kind == "region":
            labels.append(str(region))
        elif kind == "team":
            labels.append(f"  {team}")
        elif kind == "subtotal":
            labels.append(f"소계 {region}")
        else:
            labels.append("합계 전체")
    return tuple(labels)


def _metric_value(region_index: int, team_index: int, period_index: int, seed_slot: int) -> tuple[str, int, int]:
    state = STATE_LABELS[(seed_slot + region_index + team_index + period_index) % len(STATE_LABELS)]
    revenue = 28 + (region_index * 12) + (team_index * 5) + (period_index * 7) + (seed_slot % 3)
    margin = 7 + (region_index * 4) + (team_index * 2) + (period_index * 3) + ((seed_slot + team_index) % 2)
    return state, revenue, margin


def _value_grid(seed_slot: int) -> list[list[list[str | dict]]]:
    regions = _region_order(seed_slot)
    teams = _team_order(seed_slot)
    region_index = {region: index for index, region in enumerate(regions)}
    team_index = {team: index for index, team in enumerate(teams)}
    team_metrics: dict[tuple[str, str, str], tuple[str, int, int]] = {}
    for region in regions:
        for team in teams:
            for period_index, period in enumerate(PERIODS):
                team_metrics[(region, team, period)] = _metric_value(region_index[region], team_index[team], period_index, seed_slot)

    values: list[list[list[str | dict]]] = []
    for kind, region, team in _row_specs(seed_slot):
        row_cells: list[list[str | dict]] = []
        if kind == "region":
            for period in PERIODS:
                row_cells.append(
                    [
                        {"text": "묶음", "style": "muted"},
                        {"text": "", "style": "muted"},
                        {"text": "", "style": "muted"},
                    ]
                )
            values.append(row_cells)
            continue

        if kind == "team":
            assert region is not None and team is not None
            for period in PERIODS:
                state, revenue, margin = team_metrics[(region, team, period)]
                row_cells.append([state, str(revenue), str(margin)])
            values.append(row_cells)
            continue

        if kind == "subtotal":
            assert region is not None
            for period in PERIODS:
                revenue = sum(team_metrics[(region, team_name, period)][1] for team_name in teams)
                margin = sum(team_metrics[(region, team_name, period)][2] for team_name in teams)
                row_cells.append(["소계", str(revenue), str(margin)])
            values.append(row_cells)
            continue

        for period in PERIODS:
            revenue = sum(team_metrics[(region_name, team_name, period)][1] for region_name in regions for team_name in teams)
            margin = sum(team_metrics[(region_name, team_name, period)][2] for region_name in regions for team_name in teams)
            row_cells.append(["총계", str(revenue), str(margin)])
        values.append(row_cells)

    return values


def _overview_table(seed_slot: int, *, title: str, subtitle: str):
    row_height = 32
    row_count = len(_row_labels(seed_slot))
    table_height = 38 + 34 + (row_count * row_height)
    return make_banded_table(
        element_id=f"hierarchy-table-{seed_slot}",
        title=title,
        box=rect(84, 208, 1112, table_height),
        band_labels=PERIODS,
        sub_headers=SUB_HEADERS,
        row_labels=_row_labels(seed_slot),
        values=_value_grid(seed_slot),
        subtitle=subtitle,
        column_weights=(2.15, 0.82, 1.0, 0.94, 0.82, 1.0, 0.94),
        row_height=row_height,
    )


def _scope_note(title: str, lines: tuple[str, ...]):
    note_panel = text_block(
        "scope-note-panel",
        title,
        rect(124, 210, 980, 188),
        lines,
        style="note",
        subtitle="검토 기준 메모",
    )
    return sheet("notes", "기준 메모", [page("notes-p1", "기준 메모 시트", elements=[note_panel], regions=(region("scope-note-panel", "evidence_panel", title, note_panel.rect),))])


def _query_brief_blocks(*, target_title: str, target_lines: tuple[str, ...], guidance_title: str, guidance_lines: tuple[str, ...]):
    return query_header_blocks(
        target_title=target_title,
        target_lines=target_lines,
        guidance_title=guidance_title,
        guidance_lines=guidance_lines,
        mode="auto",
    )


def _build_merged_scope_episode(manifest: TemplateManifest, seed_slot: int):
    regions = _region_order(seed_slot)
    teams = _team_order(seed_slot)
    target_region = regions[seed_slot % len(regions)]
    target_team = teams[(seed_slot + 1) % len(teams)]
    target_period = PERIODS[seed_slot % len(PERIODS)]
    target_metric = "매출" if seed_slot % 2 == 0 else "마진"
    other_metric = "마진" if target_metric == "매출" else "매출"
    other_region = regions[(regions.index(target_region) + 1) % len(regions)]

    overview_table = _overview_table(seed_slot, title="실적 검토표", subtitle="같은 1팀/2팀/3팀 라벨이 지역마다 반복되고, 상·하반기 아래 매출과 마진이 함께 배치된다")
    choice_rows = (
        ChoiceCardSpec("A", f"{other_region} / {target_team} / {target_period}-{target_metric}", ("같은 팀이지만 다른 지역",)),
        ChoiceCardSpec("B", f"{target_region} / {target_team} / {target_period}-{target_metric}", ("지역·팀·반기·항목이 모두 맞는 정답",)),
        ChoiceCardSpec("C", f"{target_region} / {target_team} / {target_period}-{other_metric}", ("같은 범위지만 항목이 다른 경우",)),
        ChoiceCardSpec("D", f"소계 {target_region} / {target_period}-{target_metric}", ("소계 행은 개별 팀 칸이 아니다",)),
    )
    query_blocks, choices_y = _query_brief_blocks(
        target_title="확인 요청",
        target_lines=(f"{target_region} / {target_team} / {target_period}-{target_metric}",),
        guidance_title="검토 기준 메모",
        guidance_lines=(
            "지역 머리글과 팀 라벨, 반기, 항목을 모두 맞춰 실제 확인 대상 칸을 확정합니다.",
            "소계 행과 같은 팀의 다른 지역 셀은 검토 대상이 아닙니다.",
        ),
    )
    cards, choice_regions = query_choice_cards(
        prefix="merged-choice",
        answer_form="cell_choice",
        cards=choice_rows,
        y=choices_y,
        subtitle=None,
    )

    sheets = [
        sheet(
            "overview",
            "보고표",
            [page("overview-p1", "보고표 시트", elements=[overview_table], regions=(region("merged-overview", "evidence_panel", "보고표 표", overview_table.rect),))],
        )
    ]
    relevant_region_ids = ["merged-overview"]
    if manifest.level >= 2:
        sheets.append(
            _scope_note(
                "범위 기준 메모",
                (
                    "소계와 총계는 데이터 행이 아니므로, 특정 팀 검토에서는 선택 대상에서 제외합니다.",
                    "같은 1팀/2팀/3팀 라벨이 여러 지역에 반복되므로 지역 머리글과 항목 열을 먼저 확정해야 합니다.",
                ),
            )
        )
        relevant_region_ids.append("scope-note-panel")
    sheets.append(
        sheet(
            "query",
            "선택",
            [
                page(
                    "query-p1",
                    "선택 시트",
                    elements=[
                        *query_blocks,
                        *cards,
                    ],
                    regions=choice_regions,
                )
            ],
        )
    )
    return episode(
        manifest=manifest,
        family_display_name=FAMILY_LABEL,
        question=f"밀도 높은 집계표에서 {target_region} / {target_team} / {target_period}-{target_metric} 에 해당하는 실제 검토 대상은 어느 선택지인가?",
        workbook_title="계층 범위 검토표",
        sheets=sheets,
        answer=AnswerSpec(canonical="B", accepted=("b",), normalizer="basic"),
        seed_slot=seed_slot,
        metadata_extra={"relevant_region_ids": tuple(relevant_region_ids)},
    )


def _build_grouped_statement_episode(manifest: TemplateManifest, seed_slot: int):
    regions = _region_order(seed_slot)
    teams = _team_order(seed_slot)
    target_region = regions[(seed_slot + 1) % len(regions)]
    team_phrase = " + ".join(f"{target_region} {team}" for team in teams)
    other_region = regions[(regions.index(target_region) + 1) % len(regions)]

    table = _overview_table(seed_slot, title="요약 검토표", subtitle="지역 소계와 전체 합계가 함께 있어 범위 경계를 정확히 읽어야 한다")
    query_blocks, choices_y = _query_brief_blocks(
        target_title="확인 요청",
        target_lines=(f"{target_region} 소계가 실제로 요약하는 범위를 판단",),
        guidance_title="검토 기준 메모",
        guidance_lines=(
            "지역 소계는 같은 지역 3개 팀의 매출만 포함합니다.",
            "전체 합계와 마진 열은 다른 범위로 구분해야 합니다.",
        ),
    )
    cards, regions_for_cards = query_choice_cards(
        prefix="grouped-statement",
        answer_form="statement_choice",
        cards=(
            ChoiceCardSpec("A", f"{target_region} 소계는 모든 지역 팀을 합친 값이다", ("지역 경계를 무시한 오답",)),
            ChoiceCardSpec("B", f"{target_region} 소계는 {team_phrase}의 매출만 합친 값이다", ("같은 지역 3개 팀만 포함하는 정답",)),
            ChoiceCardSpec("C", f"{target_region} 소계는 바로 위 {teams[-1]} 한 행을 복사한 값이다", ("소계 묶음을 무시한 오답",)),
            ChoiceCardSpec("D", f"{target_region} 소계와 전체 합계는 {other_region} 팀도 같은 범위로 포함한다", ("전체 합계와 소계를 혼동한 오답",)),
        ),
        y=choices_y,
        subtitle=None,
    )

    sheets = [
        sheet(
            "overview",
            "보고표",
            [page("overview-p1", "보고표 시트", elements=[table], regions=(region("grouped-statement-table", "evidence_panel", "보고표 표", table.rect),))],
        )
    ]
    relevant_region_ids = ["grouped-statement-table"]
    if manifest.level >= 2:
        sheets.append(
            _scope_note(
                "그룹 경계 검토 기준 메모",
                (
                    "각 지역 소계는 같은 지역 3개 팀의 매출만 요약합니다. 마진 열과 총계는 별도 범위입니다.",
                    "합계 전체는 세 지역 소계를 모두 포함하지만, 개별 지역 소계는 다른 지역 팀을 포함하지 않습니다.",
                ),
            )
        )
        relevant_region_ids.append("scope-note-panel")
    sheets.append(
        sheet(
            "query",
            "선택",
            [
                page(
                    "query-p1",
                    "선택 시트",
                    elements=[
                        *query_blocks,
                        *cards,
                    ],
                    regions=regions_for_cards,
                )
            ],
        )
    )
    return episode(
        manifest=manifest,
        family_display_name=FAMILY_LABEL,
        question=f"{target_region} 소계와 전체 합계 블록을 함께 검토했을 때 실제 범위 설명으로 맞는 선택지는 무엇인가?",
        workbook_title="그룹 소계 검토표",
        sheets=sheets,
        answer=AnswerSpec(canonical="B", accepted=("b",), normalizer="basic"),
        seed_slot=seed_slot,
        metadata_extra={"relevant_region_ids": tuple(relevant_region_ids)},
    )


def _build_subtotal_row_label_episode(manifest: TemplateManifest, seed_slot: int):
    regions = _region_order(seed_slot)
    teams = _team_order(seed_slot)
    target_scope = "합계 전체" if manifest.level == 3 and seed_slot % 2 == 1 else f"소계 {regions[seed_slot % len(regions)]}"
    query_title = "검토 합계" if target_scope == "합계 전체" else "검토 소계"

    table = _overview_table(seed_slot, title="집계 검토표", subtitle="각 지역 3팀 소계와 전체 합계가 함께 배치되어 행 묶음 경계를 구분해야 한다")
    query_blocks, choices_y = _query_brief_blocks(
        target_title=query_title,
        target_lines=(target_scope,),
        guidance_title="검토 기준 메모",
        guidance_lines=(
            "지역 소계는 해당 지역 3개 팀만 묶습니다.",
            "전체 합계는 세 지역 전체를 묶는 별도 선택지입니다.",
        ),
    )
    cards, regions_for_cards = query_choice_cards(
        prefix="subtotal-row",
        answer_form="row_label_choice",
        cards=(
            ChoiceCardSpec("A", f"{regions[0]} 1팀 + 2팀 + 3팀", ("첫 번째 지역 소계가 가리키는 묶음",)),
            ChoiceCardSpec("B", f"{regions[1]} 1팀 + 2팀 + 3팀", ("두 번째 지역 소계가 가리키는 묶음",)),
            ChoiceCardSpec("C", f"{regions[2]} 1팀 + 2팀 + 3팀", ("세 번째 지역 소계가 가리키는 묶음",)),
            ChoiceCardSpec("D", "모든 지역 1팀 + 2팀 + 3팀", ("전체 합계가 가리키는 묶음",)),
        ),
        y=choices_y,
        subtitle=None,
    )

    if target_scope == "합계 전체":
        answer = "D"
    else:
        target_region = target_scope.replace("소계 ", "")
        answer = ("A", "B", "C")[regions.index(target_region)]

    sheets = [
        sheet(
            "overview",
            "보고표",
            [page("overview-p1", "보고표 시트", elements=[table], regions=(region("subtotal-row-table", "evidence_panel", "보고표 표", table.rect),))],
        )
    ]
    relevant_region_ids = ["subtotal-row-table"]
    if manifest.level >= 2:
        sheets.append(
            _scope_note(
                "소계 해석 검토 기준 메모",
                (
                    "지역 소계는 같은 지역 3개 팀만 묶고, 합계 전체는 세 지역 팀 전체를 묶습니다.",
                    "같은 1팀/2팀/3팀 이름이 지역마다 반복되므로, 선택지는 반드시 지역 헤더와 함께 읽어야 합니다.",
                ),
            )
        )
        relevant_region_ids.append("scope-note-panel")

    sheets.append(
        sheet(
            "query",
            "선택",
            [
                page(
                    "query-p1",
                    "선택 시트",
                    elements=[
                        *query_blocks,
                        *cards,
                    ],
                    regions=regions_for_cards,
                )
            ],
        )
    )
    return episode(
        manifest=manifest,
        family_display_name=FAMILY_LABEL,
        question=f"{target_scope} 가 실제로 요약하는 행 묶음으로 맞는 검토 결과는 어느 선택지인가?",
        workbook_title="소계 묶음 검토표",
        sheets=sheets,
        answer=AnswerSpec(canonical=answer, accepted=(answer.lower(),), normalizer="basic"),
        seed_slot=seed_slot,
        metadata_extra={"relevant_region_ids": tuple(relevant_region_ids)},
    )
