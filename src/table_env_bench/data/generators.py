"""Deterministic workbook benchmark generators."""

from __future__ import annotations

import random
from typing import Callable, Iterable

from table_env_bench.data.canonical_catalog import (
    benchmark_episode_records as _canonical_benchmark_episode_records,
    benchmark_suite_manifest as _benchmark_suite_manifest,
    benchmark_suite_records as _benchmark_suite_records,
    benchmark_split_manifest as _canonical_benchmark_split_manifest,
    canonical_episode_catalog as _canonical_episode_catalog,
    canonical_level_wrappers,
    canonical_seed_capacity as _canonical_seed_capacity,
    eval_hard_episode_catalog as _eval_hard_episode_catalog,
    generate_canonical_episode,
    list_templates as _canonical_list_templates,
)
from table_env_bench.data.instances import (
    instance_benchmark_records as _instance_benchmark_records,
    list_instance_packs as _list_instance_packs,
    list_instances as _list_instances,
    load_instance as _load_instance,
    load_instance_pack as _load_instance_pack,
)
from table_env_bench.data.models import (
    AnswerSpec,
    ChartElementSpec,
    ChartSeriesSpec,
    EpisodeSpec,
    LegendElementSpec,
    LegendItemSpec,
    NoteSpec,
    PageSpec,
    RectSpec,
    RegionSpec,
    SheetSpec,
    TableCellSpec,
    TableElementSpec,
    TextBlockElementSpec,
    WorkbookSpec,
)

PAGE_WIDTH = 1280
PAGE_HEIGHT = 900

FAMILY_LABELS = {
    "inventory_exception_disambiguation": "재고 예외 판정",
    "channel_policy_transfer": "채널 집행 기준 적용",
    "excel_viewport_sheet_navigation": "스프레드시트 뷰포트 탐색",
    "marker_position_rule_transfer": "표식 위치 규칙 전이",
    "report_scope_reconciliation": "보고 범위 판정",
}

PALETTE = {
    "blue": "#2563eb",
    "teal": "#0f766e",
    "orange": "#f97316",
    "rose": "#e11d48",
    "violet": "#7c3aed",
}


def _accepted_numeric_forms(value: int, suffix: str | None = None) -> tuple[str, ...]:
    variants = {str(value), f"{value:,}"}
    if suffix:
        variants.update({f"{value}{suffix}", f"{value:,}{suffix}", f"{value} {suffix}", f"{value:,} {suffix}"})
    canonical = str(value)
    return tuple(sorted(variant for variant in variants if variant != canonical))


def _accepted_choice_forms(choice_id: str) -> tuple[str, ...]:
    upper = choice_id.upper()
    lower = choice_id.lower()
    return (lower, f"선택지 {upper}", f"{upper}번", f"정답 {upper}")


def _rect(x: float, y: float, width: float, height: float) -> RectSpec:
    return RectSpec(x=x, y=y, width=width, height=height)


def _summary_split_layout() -> dict[str, RectSpec]:
    return {
        "main": _rect(84, 188, 772, 352),
        "aside": _rect(886, 196, 316, 156),
    }


def _table_focus_layout(*, height: float = 272) -> dict[str, RectSpec]:
    return {"main": _rect(84, 188, 1112, height)}


def _chart_focus_layout() -> dict[str, RectSpec]:
    return {
        "chart": _rect(84, 184, 800, 392),
        "legend": _rect(918, 198, 224, 110),
    }


def _note_band_layout(*, y: float = 496, height: float = 118) -> dict[str, RectSpec]:
    return {"main": _rect(84, y, 1112, height)}


def _column_widths(total_width: float, weights: tuple[float, ...]) -> tuple[int, ...]:
    scaled = [int(round(total_width * (weight / sum(weights)))) for weight in weights]
    scaled[-1] += int(total_width) - sum(scaled)
    return tuple(scaled)


def _excel_column_label(index: int) -> str:
    label = ""
    current = index + 1
    while current > 0:
        current, remainder = divmod(current - 1, 26)
        label = chr(65 + remainder) + label
    return label


def _spreadsheet_table(
    *,
    element_id: str,
    title: str,
    rect: RectSpec,
    headers: tuple[str, ...],
    rows: list[tuple[str, ...]],
    column_weights: tuple[float, ...],
    alignments: tuple[str, ...],
    subtitle: str | None = None,
    worksheet_name: str | None = None,
    highlight_labels: tuple[str, ...] = (),
    accent_labels: tuple[str, ...] = (),
    total_labels: tuple[str, ...] = (),
    muted_columns: tuple[int, ...] = (),
    row_height: int = 34,
) -> TableElementSpec:
    if not headers or len(headers) != len(column_weights) or len(headers) != len(alignments):
        raise ValueError("headers, column_weights, and alignments must have the same length")
    if any(len(row) != len(headers) for row in rows):
        raise ValueError("All rows must match header length")

    widths = _column_widths(rect.width, column_weights)
    cells: list[TableCellSpec] = []
    highlight_set = set(highlight_labels)
    accent_set = set(accent_labels)
    total_set = set(total_labels)
    muted_set = set(muted_columns)

    for col_index, header in enumerate(headers):
        header_align = "center" if col_index == 0 else alignments[col_index]
        header_text = header if col_index == 0 else f"{header} ▾"
        cells.append(TableCellSpec(row=0, col=col_index, text=header_text, style="header", align=header_align))

    for row_index, row in enumerate(rows, start=1):
        row_key = row[1] if len(row) > 1 else row[0]
        numeric_emphasis_used = False
        for col_index, value in enumerate(row):
            align = "center" if col_index == 0 else alignments[col_index]
            style = "body"
            if col_index == 0:
                style = "index"
            elif row_key in total_set:
                style = "total_label" if align == "left" and col_index == 1 else "total"
            elif row_key in highlight_set and align == "right" and not numeric_emphasis_used:
                style = "highlight"
                numeric_emphasis_used = True
            elif row_key in accent_set and align == "right" and not numeric_emphasis_used:
                style = "accent"
                numeric_emphasis_used = True
            elif col_index == 1 and align == "left":
                style = "row_label"
            elif col_index in muted_set:
                style = "muted"
            elif align == "right" and str(value).strip().startswith("-"):
                style = "negative"
            elif align == "right":
                style = "numeric"
            cells.append(TableCellSpec(row=row_index, col=col_index, text=value, style=style, align=align))

    top_left = _excel_column_label(0)
    bottom_right = _excel_column_label(len(headers) - 1)
    range_label = f"{top_left}1:{bottom_right}{len(rows) + 1}"

    return TableElementSpec(
        element_id=element_id,
        rect=rect,
        title=title,
        n_rows=len(rows) + 1,
        n_cols=len(headers),
        column_widths=widths,
        row_heights=(40,) + (row_height,) * len(rows),
        cells=tuple(cells),
        metadata={
            "subtitle": subtitle or "정렬된 시트 보기",
            "worksheet_name": worksheet_name or element_id.upper().replace("-", "_"),
            "record_count": len(rows),
            "range_label": range_label,
            "excel_chrome": True,
            "freeze_columns": 2 if len(headers) >= 3 else 1,
        },
    )


def _two_col_table(
    *,
    element_id: str,
    title: str,
    rect: RectSpec,
    value_header: str,
    rows: list[tuple[str, str, str]],
    subtitle: str | None = None,
) -> TableElementSpec:
    left_width = int(round(rect.width * 0.58))
    right_width = int(round(rect.width - left_width))
    row_height = 54
    cells = [
        TableCellSpec(row=0, col=0, text="항목", style="header", align="left"),
        TableCellSpec(row=0, col=1, text=value_header, style="header", align="right"),
    ]
    for index, (label, value, style) in enumerate(rows, start=1):
        cells.append(TableCellSpec(row=index, col=0, text=label, style="row_label", align="left"))
        cells.append(TableCellSpec(row=index, col=1, text=value, style=style, align="right"))
    return TableElementSpec(
        element_id=element_id,
        rect=rect,
        title=title,
        n_rows=len(rows) + 1,
        n_cols=2,
        column_widths=(left_width, right_width),
        row_heights=(60,) + (row_height,) * len(rows),
        cells=tuple(cells),
        metadata={"subtitle": subtitle or f"단위 · {value_header}"},
    )


def _three_col_table(
    *,
    element_id: str,
    title: str,
    rect: RectSpec,
    headers: tuple[str, str, str],
    rows: list[tuple[str, str, str, str]],
    subtitle: str | None = None,
) -> TableElementSpec:
    widths = (int(round(rect.width * 0.44)), int(round(rect.width * 0.24)), int(round(rect.width * 0.32)))
    widths = (widths[0], widths[1], int(rect.width - widths[0] - widths[1]))
    cells = [
        TableCellSpec(row=0, col=0, text=headers[0], style="header", align="left"),
        TableCellSpec(row=0, col=1, text=headers[1], style="header", align="right"),
        TableCellSpec(row=0, col=2, text=headers[2], style="header", align="left"),
    ]
    for index, (label, value, note, style) in enumerate(rows, start=1):
        cells.append(TableCellSpec(row=index, col=0, text=label, style="row_label", align="left"))
        cells.append(TableCellSpec(row=index, col=1, text=value, style=style, align="right"))
        cells.append(TableCellSpec(row=index, col=2, text=note, style="body", align="left"))
    return TableElementSpec(
        element_id=element_id,
        rect=rect,
        title=title,
        n_rows=len(rows) + 1,
        n_cols=3,
        column_widths=widths,
        row_heights=(58,) + (52,) * len(rows),
        cells=tuple(cells),
        metadata={"subtitle": subtitle or f"{headers[1]} · {headers[2]}"},
    )


def _chart(
    *,
    element_id: str,
    chart_type: str,
    title: str,
    rect: RectSpec,
    categories: Iterable[str],
    series: Iterable[ChartSeriesSpec],
    y_axis_label: str,
    subtitle: str | None = None,
) -> ChartElementSpec:
    return ChartElementSpec(
        element_id=element_id,
        rect=rect,
        chart_type=chart_type,
        title=title,
        categories=tuple(categories),
        series=tuple(series),
        y_axis_label=y_axis_label,
        metadata={"subtitle": subtitle or f"비교 기준 · {y_axis_label}"},
    )


def _legend(*, element_id: str, title: str, rect: RectSpec, items: Iterable[tuple[str, str]]) -> LegendElementSpec:
    return LegendElementSpec(
        element_id=element_id,
        rect=rect,
        title=title,
        items=tuple(LegendItemSpec(label=label, color=color) for label, color in items),
    )


def _text_block(
    *,
    element_id: str,
    title: str,
    rect: RectSpec,
    lines: Iterable[str],
    style: str = "body",
    subtitle: str | None = None,
) -> TextBlockElementSpec:
    return TextBlockElementSpec(
        element_id=element_id,
        rect=rect,
        title=title,
        lines=tuple(lines),
        style=style,
        metadata={"subtitle": subtitle} if subtitle else {},
    )


def _choice_block(*, element_id: str, choice_id: str, rect: RectSpec, description: str) -> TextBlockElementSpec:
    return _text_block(
        element_id=element_id,
        title=f"선택지 {choice_id}",
        rect=rect,
        lines=(description,),
        style="body",
        subtitle="정답 후보",
    )


def _triangle_marker(anchor: str, *, color: str = PALETTE["teal"]) -> dict[str, object]:
    return {"kind": "triangle", "anchor": anchor, "color": color}


def _selection_frame(*, color: str = PALETTE["teal"]) -> dict[str, object]:
    return {"kind": "selection", "color": color}


def _visual_rule_table(
    *,
    element_id: str,
    title: str,
    rect: RectSpec,
    active_band: str,
    rows: list[tuple[str, str | None, str | None, str | None, str | None]],
    selected_target: tuple[int, int] | None = None,
    subtitle: str | None = None,
) -> TableElementSpec:
    column_widths = _column_widths(rect.width, (0.18, 0.205, 0.205, 0.205, 0.205))
    row_heights = (38, 36) + (48,) * len(rows)
    cells: list[TableCellSpec] = [
        TableCellSpec(row=0, col=0, text="행", row_span=2, style="header", align="center"),
        TableCellSpec(row=0, col=1, text="기본", col_span=2, style="header", align="center"),
        TableCellSpec(row=0, col=3, text="검토", col_span=2, style="header", align="center"),
        TableCellSpec(row=1, col=1, text="상태", style="header", align="center"),
        TableCellSpec(row=1, col=2, text="조치", style="header", align="center"),
        TableCellSpec(row=1, col=3, text="상태", style="header", align="center"),
        TableCellSpec(row=1, col=4, text="조치", style="header", align="center"),
    ]

    for row_index, (label, basic_status, basic_action, review_status, review_action) in enumerate(rows, start=2):
        cells.append(TableCellSpec(row=row_index, col=0, text=label, style="row_label", align="left"))
        for col_index, marker in enumerate((basic_status, basic_action, review_status, review_action), start=1):
            metadata: dict[str, object] = {}
            if marker:
                metadata["icon"] = _triangle_marker(marker)
            if selected_target == (row_index, col_index):
                metadata["frame"] = _selection_frame()
            cells.append(TableCellSpec(row=row_index, col=col_index, text="", style="body", align="center", metadata=metadata))

    return TableElementSpec(
        element_id=element_id,
        rect=rect,
        title=title,
        n_rows=2 + len(rows),
        n_cols=5,
        column_widths=column_widths,
        row_heights=row_heights,
        cells=tuple(cells),
        metadata={
            "subtitle": subtitle or f"대상 구역: {active_band}",
            "worksheet_name": element_id.upper().replace("-", "_"),
            "record_count": len(rows),
            "range_label": f"A1:E{len(rows) + 2}",
            "excel_chrome": True,
            "freeze_columns": 1,
        },
    )


def _pattern_icon_table(
    *,
    element_id: str,
    title: str,
    rect: RectSpec,
    rows: list[tuple[str, bool, bool, bool]],
    subtitle: str | None = None,
) -> TableElementSpec:
    column_widths = _column_widths(rect.width, (0.30, 0.70))
    row_heights = (42,) + (52,) * len(rows)
    cells: list[TableCellSpec] = [
        TableCellSpec(row=0, col=0, text="행", style="header", align="center"),
        TableCellSpec(row=0, col=1, text="상태", style="header", align="center"),
    ]

    for row_index, (label, patterned, icon_marked, selected) in enumerate(rows, start=1):
        cells.append(TableCellSpec(row=row_index, col=0, text=label, style="row_label", align="left"))
        metadata: dict[str, object] = {}
        if patterned:
            metadata["pattern"] = {"kind": "diagonal_stripe", "color": PALETTE["orange"], "opacity": 0.78}
        if icon_marked:
            metadata["icon"] = _triangle_marker("top_right", color=PALETTE["teal"])
        if selected:
            metadata["frame"] = _selection_frame(color=PALETTE["blue"])
        cells.append(TableCellSpec(row=row_index, col=1, text="", style="body", align="center", metadata=metadata))

    return TableElementSpec(
        element_id=element_id,
        rect=rect,
        title=title,
        n_rows=1 + len(rows),
        n_cols=2,
        column_widths=column_widths,
        row_heights=row_heights,
        cells=tuple(cells),
        metadata={
            "subtitle": subtitle or "줄무늬와 삼각형 표식을 함께 관찰",
            "worksheet_name": element_id.upper().replace("-", "_"),
            "record_count": len(rows),
            "range_label": f"A1:B{len(rows) + 1}",
            "excel_chrome": True,
            "freeze_columns": 1,
        },
    )


def _target_choice_preview_table(
    *,
    element_id: str,
    choice_id: str,
    rect: RectSpec,
    row_label: str,
    target_col: int,
) -> TableElementSpec:
    column_widths = _column_widths(rect.width, (0.18, 0.205, 0.205, 0.205, 0.205))
    row_heights = (28, 26, 24, 32)
    cells: list[TableCellSpec] = [
        TableCellSpec(row=0, col=0, text=f"선택지 {choice_id}", col_span=5, style="header", align="center"),
        TableCellSpec(row=1, col=0, text="행", row_span=2, style="header", align="center"),
        TableCellSpec(row=1, col=1, text="기본", col_span=2, style="header", align="center"),
        TableCellSpec(row=1, col=3, text="검토", col_span=2, style="header", align="center"),
        TableCellSpec(row=2, col=1, text="상태", style="header", align="center"),
        TableCellSpec(row=2, col=2, text="조치", style="header", align="center"),
        TableCellSpec(row=2, col=3, text="상태", style="header", align="center"),
        TableCellSpec(row=2, col=4, text="조치", style="header", align="center"),
        TableCellSpec(row=3, col=0, text=row_label, style="row_label", align="left"),
    ]
    for col_index in range(1, 5):
        metadata = {"frame": _selection_frame()} if col_index == target_col else {}
        cells.append(TableCellSpec(row=3, col=col_index, text="", style="body", align="center", metadata=metadata))

    return TableElementSpec(
        element_id=element_id,
        rect=rect,
        title="",
        n_rows=4,
        n_cols=5,
        column_widths=column_widths,
        row_heights=row_heights,
        cells=tuple(cells),
        metadata={
            "worksheet_name": "",
            "range_label": "",
            "record_count": 1,
            "excel_chrome": False,
            "freeze_columns": 0,
        },
    )


def _statement_choice_preview_table(
    *,
    element_id: str,
    choice_id: str,
    rect: RectSpec,
    selected_rows: tuple[str, ...],
) -> TableElementSpec:
    column_widths = _column_widths(rect.width, (0.52, 0.48))
    row_heights = (28, 24, 22, 22, 22, 22)
    cells: list[TableCellSpec] = [
        TableCellSpec(row=0, col=0, text=f"선택지 {choice_id}", col_span=2, style="header", align="center"),
        TableCellSpec(row=1, col=0, text="행", style="header", align="center"),
        TableCellSpec(row=1, col=1, text="선택", style="header", align="center"),
    ]
    selected = set(selected_rows)
    for row_index, row_label in enumerate(("A행", "B행", "C행", "D행"), start=2):
        cells.append(TableCellSpec(row=row_index, col=0, text=row_label, style="row_label", align="left"))
        metadata = {"frame": _selection_frame(color=PALETTE["blue"])} if row_label in selected else {}
        cells.append(TableCellSpec(row=row_index, col=1, text="", style="body", align="center", metadata=metadata))

    return TableElementSpec(
        element_id=element_id,
        rect=rect,
        title="",
        n_rows=6,
        n_cols=2,
        column_widths=column_widths,
        row_heights=row_heights,
        cells=tuple(cells),
        metadata={
            "worksheet_name": "",
            "range_label": "",
            "record_count": 4,
            "excel_chrome": False,
            "freeze_columns": 0,
        },
    )


def _region_for_element(element, *, linked_note_id: str | None = None, label: str | None = None) -> RegionSpec:
    role_map = {
        "table": "table_region",
        "chart": "chart_region",
        "legend": "legend_region",
        "text_block": "note_region" if getattr(element, "style", "") == "note" else "text_region",
    }
    return RegionSpec(
        public_id=element.element_id,
        role=role_map.get(element.type, "region"),
        label=label or element.title or element.element_id,
        rect=element.rect,
        linked_note_id=linked_note_id,
    )


def _page(
    *,
    page_id: str,
    title: str,
    elements: list,
    regions: list[RegionSpec] | None = None,
    notes: tuple[NoteSpec, ...] = (),
) -> PageSpec:
    custom_regions = regions or []
    custom_ids = {region.public_id for region in custom_regions}
    auto_regions = [_region_for_element(element) for element in elements if element.element_id not in custom_ids]
    return PageSpec(
        page_id=page_id,
        title=title,
        width=PAGE_WIDTH,
        height=PAGE_HEIGHT,
        elements=tuple(elements),
        regions=tuple(custom_regions + auto_regions),
        notes=notes,
    )


def _sheet(sheet_id: str, tab_label: str, pages: list[PageSpec]) -> SheetSpec:
    return SheetSpec(sheet_id=sheet_id, tab_label=tab_label, pages=tuple(pages))


def _episode(
    *,
    episode_id: str,
    family: str,
    level: int,
    seed: int,
    question: str,
    answer: int,
    sheets: list[SheetSpec],
    max_actions: int,
    answer_suffix: str = "원",
) -> EpisodeSpec:
    return EpisodeSpec(
        episode_id=episode_id,
        family=family,
        family_display_name=FAMILY_LABELS[family],
        level=level,
        seed=seed,
        locale="ko-KR",
        question=question,
        workbook=WorkbookSpec(
            workbook_id=f"{family}_workbook",
            title=f"{FAMILY_LABELS[family]} 워크북",
            sheets=tuple(sheets),
        ),
        answer=AnswerSpec(
            canonical=str(answer),
            accepted=_accepted_numeric_forms(answer, answer_suffix),
            normalizer="ko_answer",
        ),
        max_actions=max_actions,
    )


def _choice_episode(
    *,
    episode_id: str,
    family: str,
    level: int,
    seed: int,
    question: str,
    answer: str,
    sheets: list[SheetSpec],
    max_actions: int,
    accepted: tuple[str, ...] = (),
    metadata: dict[str, object] | None = None,
) -> EpisodeSpec:
    return EpisodeSpec(
        episode_id=episode_id,
        family=family,
        family_display_name=FAMILY_LABELS[family],
        level=level,
        seed=seed,
        locale="ko-KR",
        question=question,
        workbook=WorkbookSpec(
            workbook_id=f"{family}_workbook",
            title=f"{FAMILY_LABELS[family]} 워크북",
            sheets=tuple(sheets),
        ),
        answer=AnswerSpec(
            canonical=answer,
            accepted=accepted,
            normalizer="basic",
        ),
        max_actions=max_actions,
        metadata=dict(metadata or {}),
    )


def _summary_appendix_override_level_1(seed: int) -> EpisodeSpec:
    rng = random.Random(seed + 101)
    shown_profit = 84 + rng.randint(0, 4)
    adjustment = 5 + rng.randint(0, 2)
    corrected = (shown_profit + adjustment) * 100_000_000
    layout = _summary_split_layout()
    appendix_layout = _table_focus_layout(height=326)

    summary_table = _spreadsheet_table(
        element_id="summary-table",
        title="핵심 손익 요약",
        rect=layout["main"],
        headers=("No.", "계정", "보고값 (억원)", "전년동기", "증감률", "메모"),
        rows=[
            ("01", "매출", str(210 + rng.randint(0, 12)), str(198 + rng.randint(0, 4)), f"+{5.8 + 0.2 * rng.randint(0, 3):.1f}%", "본사"),
            ("02", "매출총이익", str(118 + rng.randint(0, 4)), str(110 + rng.randint(0, 3)), f"+{6.1 + 0.2 * rng.randint(0, 3):.1f}%", "잠정"),
            ("03", "영업이익", str(shown_profit), str(shown_profit - 7), f"+{9.8 + 0.3 * rng.randint(0, 4):.1f}%", "잠정"),
            ("04", "영업외손익", str(3 + rng.randint(0, 2)), str(2 + rng.randint(0, 1)), f"+{1.2 + 0.2 * rng.randint(0, 2):.1f}%", "정산 전"),
            ("05", "세전이익", str(shown_profit + 2 + rng.randint(0, 2)), str(shown_profit - 3), f"+{7.1 + 0.2 * rng.randint(0, 2):.1f}%", "연결"),
            ("06", "당기순이익", str(61 + rng.randint(0, 4)), str(58 + rng.randint(0, 3)), f"+{4.7 + 0.2 * rng.randint(0, 2):.1f}%", "연결"),
            ("07", "CAPEX", str(19 + rng.randint(0, 2)), str(18 + rng.randint(0, 2)), f"+{1.4 + 0.2 * rng.randint(0, 2):.1f}%", "참고"),
            ("08", "현금성자산", str(92 + rng.randint(0, 5)), str(88 + rng.randint(0, 4)), f"+{3.6 + 0.2 * rng.randint(0, 2):.1f}%", "월말"),
        ],
        column_weights=(0.08, 0.26, 0.18, 0.16, 0.12, 0.20),
        alignments=("center", "left", "right", "right", "right", "left"),
        subtitle="잠정 마감 기준 · 주요 계정 비교",
        worksheet_name="SUMMARY_OVERVIEW",
        highlight_labels=("영업이익",),
        accent_labels=("당기순이익",),
        muted_columns=(5,),
    )
    callout_note = NoteSpec(id="주1", title="주1 영업이익 조정", text=f"영업이익 조정 +{adjustment}억원")
    callout = _text_block(
        element_id="summary-callout",
        title="부록 메모",
        rect=layout["aside"],
        lines=("주1 조정은 다음 페이지 부록 시트에서 확인합니다.", "필요하면 클릭해 메모를 확대해 볼 수 있습니다."),
        style="callout",
        subtitle="관련 근거 이동",
    )
    appendix = _spreadsheet_table(
        element_id="appendix-note",
        title="부록 조정 등록부",
        rect=appendix_layout["main"],
        headers=("No.", "조정 항목", "조정값 (억원)", "반영 월", "근거", "상태"),
        rows=[
            ("01", "매출 조정", f"+{2 + rng.randint(0, 1)}", "3월", "프로모션 정산", "검토"),
            ("02", "영업이익 조정", f"+{adjustment}", "3월", "시범 프로젝트 정산", "확정"),
            ("03", "판관비 재분류", f"-{1 + rng.randint(0, 1)}", "3월", "분개 재분류", "완료"),
            ("04", "충당금 환입", f"+{1 + rng.randint(0, 1)}", "3월", "미사용 예산", "완료"),
            ("05", "재고평가 조정", f"-{1 + rng.randint(0, 1)}", "3월", "참고용", "보류"),
            ("06", "순조정", f"+{adjustment + 1}", "3월", "부록 집계", "요약 반영 전"),
        ],
        column_weights=(0.08, 0.26, 0.16, 0.14, 0.20, 0.16),
        alignments=("center", "left", "right", "left", "left", "left"),
        subtitle="시범 프로젝트 정산 및 보조 분개",
        worksheet_name="APPENDIX_REGISTER",
        highlight_labels=("영업이익 조정",),
        total_labels=("순조정",),
        muted_columns=(4, 5),
        row_height=40,
    )
    appendix_page = _page(
        page_id="summary-p2",
        title="요약 시트 부록",
        elements=[appendix],
        notes=(callout_note,),
    )
    summary_page = _page(
        page_id="summary-p1",
        title="요약 시트",
        elements=[summary_table, callout],
        regions=[_region_for_element(callout, linked_note_id="주1", label="주1 메모")],
        notes=(callout_note,),
    )
    return _episode(
        episode_id=f"summary_appendix_override_l1_s{seed}",
        family="summary_appendix_override",
        level=1,
        seed=seed,
        question="요약 시트의 영업이익에 부록의 주1 조정을 반영하면 원 단위로 얼마인가?",
        answer=corrected,
        sheets=[_sheet("summary", "요약", [summary_page, appendix_page])],
        max_actions=8,
    )


def _summary_appendix_override_level_2(seed: int) -> EpisodeSpec:
    rng = random.Random(seed + 202)
    shown_profit = 71 + rng.randint(0, 4)
    adjustment = 6 + rng.randint(0, 2)
    corrected = (shown_profit + adjustment) * 100_000_000
    summary_layout = _summary_split_layout()
    appendix_layout = _table_focus_layout(height=360)

    summary_table = _spreadsheet_table(
        element_id="summary-table",
        title="경영 요약",
        rect=summary_layout["main"],
        headers=("No.", "계정", "보고값 (억원)", "예산", "차이", "비고"),
        rows=[
            ("01", "매출", str(198 + rng.randint(0, 12)), str(194 + rng.randint(0, 6)), f"+{4 + rng.randint(0, 2)}", "월말"),
            ("02", "매출총이익", str(104 + rng.randint(0, 4)), str(99 + rng.randint(0, 3)), f"+{4 + rng.randint(0, 2)}", "잠정"),
            ("03", "영업이익", str(shown_profit), str(shown_profit - 5), f"+{5 + rng.randint(0, 2)}", "정정 예정"),
            ("04", "투자비", str(12 + rng.randint(0, 3)), str(11 + rng.randint(0, 2)), f"+{1 + rng.randint(0, 1)}", "참고"),
            ("05", "마케팅비", str(14 + rng.randint(0, 2)), str(13 + rng.randint(0, 2)), f"+{1 + rng.randint(0, 1)}", "참고"),
            ("06", "법인세비용", str(18 + rng.randint(0, 2)), str(17 + rng.randint(0, 2)), f"+{1 + rng.randint(0, 1)}", "연결"),
            ("07", "당기순이익", str(54 + rng.randint(0, 3)), str(51 + rng.randint(0, 2)), f"+{2 + rng.randint(0, 1)}", "잠정"),
        ],
        column_weights=(0.08, 0.28, 0.18, 0.16, 0.12, 0.18),
        alignments=("center", "left", "right", "right", "right", "left"),
        subtitle="요약 마감본 · 정정 전 수치",
        worksheet_name="MGMT_SUMMARY",
        highlight_labels=("영업이익",),
        accent_labels=("당기순이익",),
        muted_columns=(5,),
    )
    summary_hint = _text_block(
        element_id="appendix-hint",
        title="참고",
        rect=summary_layout["aside"],
        lines=("영업이익 정정은 부록 시트에서 확인", "매출 메모는 답과 무관합니다."),
        style="callout",
        subtitle="탐색 힌트",
    )
    appendix_notes = _spreadsheet_table(
        element_id="appendix-adjustments",
        title="부록 조정 메모",
        rect=appendix_layout["main"],
        headers=("No.", "항목", "조정 (억원)", "반영 구분", "근거", "상태"),
        rows=[
            ("01", "매출 조정", f"+{2 + rng.randint(0, 1)}", "할인 정산", "채널 환급", "검토"),
            ("02", "영업이익 조정", f"+{adjustment}", "손익 반영", "충당금 환입", "확정"),
            ("03", "재고 조정", f"-{1 + rng.randint(0, 1)}", "재고평가", "참고용", "완료"),
            ("04", "반품충당 조정", f"-{1 + rng.randint(0, 1)}", "판관비", "보수적 반영", "완료"),
            ("05", "법인세 효과", f"+{1 + rng.randint(0, 1)}", "세효과", "자동 계산", "참고"),
            ("06", "순조정", f"+{adjustment}", "부록 집계", "영업이익 반영 기준", "요약 반영 전"),
        ],
        column_weights=(0.08, 0.24, 0.16, 0.16, 0.20, 0.16),
        alignments=("center", "left", "right", "left", "left", "left"),
        subtitle="요약 시트와 별도로 관리되는 조정 항목",
        worksheet_name="APPENDIX_ADJUSTMENTS",
        highlight_labels=("영업이익 조정",),
        total_labels=("순조정",),
        muted_columns=(4, 5),
        row_height=40,
    )
    summary_page = _page(page_id="summary-p1", title="요약 시트", elements=[summary_table, summary_hint])
    appendix_page = _page(page_id="appendix-p1", title="부록 시트", elements=[appendix_notes])
    return _episode(
        episode_id=f"summary_appendix_override_l2_s{seed}",
        family="summary_appendix_override",
        level=2,
        seed=seed,
        question="부록 시트의 영업이익 조정을 반영한 최종 영업이익은 원 단위로 얼마인가?",
        answer=corrected,
        sheets=[
            _sheet("summary", "요약", [summary_page]),
            _sheet("appendix", "부록", [appendix_page]),
        ],
        max_actions=9,
    )


def _summary_appendix_override_level_3(seed: int) -> EpisodeSpec:
    rng = random.Random(seed + 303)
    service_profit = 62 + rng.randint(0, 3)
    manufacturing_profit = 55 + rng.randint(0, 3)
    service_adjustment = 4 + rng.randint(0, 2)
    manufacturing_adjustment = -(1 + rng.randint(0, 1))
    corrected = (service_profit + service_adjustment) * 100_000_000
    summary_layout = _table_focus_layout(height=328)
    appendix_layout = _table_focus_layout(height=294)
    note_layout = _note_band_layout(y=516, height=132)

    summary_table = _spreadsheet_table(
        element_id="summary-profit",
        title="부문별 영업이익",
        rect=summary_layout["main"],
        headers=("No.", "항목", "금액 (억원)", "전년", "YoY", "비고"),
        rows=[
            ("01", "서비스 영업이익", str(service_profit), str(service_profit - 5), f"+{7.2 + 0.2 * rng.randint(0, 2):.1f}%", "핵심"),
            ("02", "제조 영업이익", str(manufacturing_profit), str(manufacturing_profit - 3), f"+{4.8 + 0.2 * rng.randint(0, 2):.1f}%", "핵심"),
            ("03", "서비스 매출총이익", str(103 + rng.randint(0, 4)), str(98 + rng.randint(0, 3)), f"+{4.6 + 0.2 * rng.randint(0, 2):.1f}%", "참고"),
            ("04", "제조 매출총이익", str(96 + rng.randint(0, 4)), str(91 + rng.randint(0, 3)), f"+{5.0 + 0.2 * rng.randint(0, 2):.1f}%", "참고"),
            ("05", "서비스 판관비", str(41 + rng.randint(0, 2)), str(39 + rng.randint(0, 2)), f"+{2.5 + 0.2 * rng.randint(0, 2):.1f}%", "참고"),
            ("06", "제조 판관비", str(38 + rng.randint(0, 2)), str(37 + rng.randint(0, 2)), f"+{1.9 + 0.2 * rng.randint(0, 2):.1f}%", "참고"),
            ("07", "합계", str(service_profit + manufacturing_profit), str(service_profit + manufacturing_profit - 8), f"+{5.7 + 0.2 * rng.randint(0, 2):.1f}%", "부문 합계"),
        ],
        column_weights=(0.08, 0.26, 0.18, 0.16, 0.12, 0.20),
        alignments=("center", "left", "right", "right", "right", "left"),
        subtitle="질문은 서비스 부문만 대상으로 합니다.",
        worksheet_name="SEGMENT_PROFIT",
        highlight_labels=("서비스 영업이익",),
        total_labels=("합계",),
        muted_columns=(5,),
    )
    appendix_table = _spreadsheet_table(
        element_id="appendix-adjustments",
        title="부문별 정정 내역",
        rect=appendix_layout["main"],
        headers=("No.", "항목", "조정 (억원)", "영향 구간", "설명", "상태"),
        rows=[
            ("01", "서비스 영업이익 조정", f"+{service_adjustment}", "서비스 손익", "취소 충당금 환입", "확정"),
            ("02", "제조 영업이익 조정", f"{manufacturing_adjustment}", "제조 손익", "반품 충당금", "완료"),
            ("03", "공통 판관비 조정", f"-{1 + rng.randint(0, 1)}", "공통 비용", "전표 재분류", "참고"),
            ("04", "순조정", f"+{service_adjustment + manufacturing_adjustment}", "부문 합계", "부록 집계", "참고"),
        ],
        column_weights=(0.08, 0.26, 0.16, 0.16, 0.18, 0.16),
        alignments=("center", "left", "right", "left", "left", "left"),
        subtitle="부문별 손익 조정 로그",
        worksheet_name="SEGMENT_RESTATEMENT",
        highlight_labels=("서비스 영업이익 조정",),
        total_labels=("순조정",),
        muted_columns=(4, 5),
        row_height=42,
    )
    appendix_note = _text_block(
        element_id="scope-note",
        title="질문 범위",
        rect=note_layout["main"],
        lines=("질문이 서비스 부문을 가리키면 서비스 영업이익과 해당 조정만 사용합니다.",),
        style="note",
        subtitle="해석 규칙",
    )
    return _episode(
        episode_id=f"summary_appendix_override_l3_s{seed}",
        family="summary_appendix_override",
        level=3,
        seed=seed,
        question="부록 시트 조정을 반영한 서비스 영업이익은 원 단위로 얼마인가?",
        answer=corrected,
        sheets=[
            _sheet("summary", "요약", [_page(page_id="summary-p1", title="요약 시트", elements=[summary_table])]),
            _sheet("appendix", "부록", [_page(page_id="appendix-p1", title="부록 시트", elements=[appendix_table, appendix_note])]),
        ],
        max_actions=10,
    )


def _chart_to_detail_lookup_level_1(seed: int) -> EpisodeSpec:
    rng = random.Random(seed + 404)
    chart_online = (8.2 + 0.1 * rng.randint(0, 2), 11.1 + 0.1 * rng.randint(0, 2), 9.3 + 0.1 * rng.randint(0, 2))
    chart_offline = (7.4 + 0.1 * rng.randint(0, 2), 8.0 + 0.1 * rng.randint(0, 2), 8.8 + 0.1 * rng.randint(0, 2))
    detail_values = (
        820_000_000 + rng.randint(0, 20_000_000),
        1_130_000_000 + rng.randint(0, 20_000_000),
        940_000_000 + rng.randint(0, 20_000_000),
    )
    answer = detail_values[1]
    chart_layout = _chart_focus_layout()
    detail_layout = _table_focus_layout(height=372)

    chart = _chart(
        element_id="monthly-chart",
        chart_type="bar",
        title="월별 채널 매출 추이",
        rect=chart_layout["chart"],
        categories=("1월", "2월", "3월"),
        series=(
            ChartSeriesSpec(name="온라인", color=PALETTE["blue"], values=chart_online),
            ChartSeriesSpec(name="오프라인", color=PALETTE["orange"], values=chart_offline),
        ),
        y_axis_label="매출 지수",
        subtitle="시각 비교용 요약 차트",
    )
    legend = _legend(
        element_id="monthly-legend",
        title="범례",
        rect=chart_layout["legend"],
        items=(("온라인", PALETTE["blue"]), ("오프라인", PALETTE["orange"])),
    )
    detail_table = _spreadsheet_table(
        element_id="detail-table",
        title="온라인 상세 매출",
        rect=detail_layout["main"],
        headers=("No.", "월", "상세 매출 (원)", "주문수", "객단가", "메모"),
        rows=[
            ("01", "1월", f"{detail_values[0]:,}", f"{3_420 + 20 * rng.randint(0, 3):,}", f"{240_000 + 5_000 * rng.randint(0, 2):,}", "기준월"),
            ("02", "2월", f"{detail_values[1]:,}", f"{4_210 + 20 * rng.randint(0, 3):,}", f"{269_000 + 5_000 * rng.randint(0, 2):,}", "최고 매출"),
            ("03", "3월", f"{detail_values[2]:,}", f"{3_860 + 20 * rng.randint(0, 3):,}", f"{244_000 + 5_000 * rng.randint(0, 2):,}", "프로모션"),
            ("04", "1분기 평균", f"{round(sum(detail_values) / 3):,}", f"{3_830 + 10 * rng.randint(0, 3):,}", f"{251_000 + 5_000 * rng.randint(0, 2):,}", "참고"),
            ("05", "광고비", f"{82_000_000 + 2_000_000 * rng.randint(0, 3):,}", f"{0:,}", f"{0:,}", "예산"),
            ("06", "반품차감", f"-{11_000_000 + 1_000_000 * rng.randint(0, 2):,}", f"{0:,}", f"{0:,}", "정산"),
            ("07", "누적 순매출", f"{sum(detail_values) - 11_000_000:,}", f"{11_490 + 30 * rng.randint(0, 3):,}", f"{251_000 + 3_000 * rng.randint(0, 2):,}", "합산"),
        ],
        column_weights=(0.08, 0.16, 0.26, 0.16, 0.16, 0.18),
        alignments=("center", "left", "right", "right", "right", "left"),
        subtitle="온라인 채널 월별 상세 실적",
        worksheet_name="ONLINE_DETAIL",
        highlight_labels=("2월",),
        total_labels=("누적 순매출",),
        muted_columns=(5,),
        row_height=38,
    )
    return _episode(
        episode_id=f"chart_to_detail_lookup_l1_s{seed}",
        family="chart_to_detail_lookup",
        level=1,
        seed=seed,
        question="막대 차트에서 온라인 매출이 가장 높은 월의 상세 매출은 원 단위로 얼마인가?",
        answer=answer,
        sheets=[
            _sheet(
                "summary",
                "요약",
                [
                    _page(page_id="summary-p1", title="요약 차트", elements=[chart, legend]),
                    _page(page_id="summary-p2", title="상세 표", elements=[detail_table]),
                ],
            )
        ],
        max_actions=8,
    )


def _chart_to_detail_lookup_level_2(seed: int) -> EpisodeSpec:
    rng = random.Random(seed + 505)
    product_a = (3.2 + 0.1 * rng.randint(0, 2), 4.3 + 0.1 * rng.randint(0, 2), 3.8 + 0.1 * rng.randint(0, 2))
    product_b = (2.7 + 0.1 * rng.randint(0, 2), 3.1 + 0.1 * rng.randint(0, 2), 4.8 + 0.1 * rng.randint(0, 2))
    detail_values = (27_000 + 100 * rng.randint(0, 8), 30_000 + 100 * rng.randint(0, 8), 49_000 + 100 * rng.randint(0, 8))
    answer = detail_values[2]
    chart_layout = _chart_focus_layout()
    detail_layout = _table_focus_layout(height=372)

    chart = _chart(
        element_id="quarterly-chart",
        chart_type="bar",
        title="분기별 제품 반응도",
        rect=chart_layout["chart"],
        categories=("1분기", "2분기", "3분기"),
        series=(
            ChartSeriesSpec(name="제품 A", color=PALETTE["teal"], values=product_a),
            ChartSeriesSpec(name="제품 B", color=PALETTE["violet"], values=product_b),
        ),
        y_axis_label="반응 지수",
        subtitle="시리즈별 비교",
    )
    legend = _legend(
        element_id="product-legend",
        title="시리즈",
        rect=chart_layout["legend"],
        items=(("제품 A", PALETTE["teal"]), ("제품 B", PALETTE["violet"])),
    )
    detail_table = _spreadsheet_table(
        element_id="shipment-table",
        title="제품 B 상세 출하량",
        rect=detail_layout["main"],
        headers=("No.", "분기", "출하량 (개)", "반품률", "리드타임", "메모"),
        rows=[
            ("01", "1분기", f"{detail_values[0]:,}", f"{1.4 + 0.1 * rng.randint(0, 2):.1f}%", f"{5 + rng.randint(0, 1)}일", "정상"),
            ("02", "2분기", f"{detail_values[1]:,}", f"{1.2 + 0.1 * rng.randint(0, 2):.1f}%", f"{5 + rng.randint(0, 1)}일", "정상"),
            ("03", "3분기", f"{detail_values[2]:,}", f"{1.1 + 0.1 * rng.randint(0, 2):.1f}%", f"{4 + rng.randint(0, 1)}일", "최고 반응"),
            ("04", "분기 평균", f"{round(sum(detail_values) / 3):,}", f"{1.2 + 0.1 * rng.randint(0, 1):.1f}%", f"{5 + rng.randint(0, 1)}일", "참고"),
            ("05", "안전재고", f"{9_200 + 100 * rng.randint(0, 3):,}", f"{0.0:.1f}%", f"{0}일", "보조"),
            ("06", "누적 출하", f"{sum(detail_values):,}", f"{1.2 + 0.1 * rng.randint(0, 1):.1f}%", f"{14 + rng.randint(0, 2)}일", "합계"),
        ],
        column_weights=(0.08, 0.18, 0.22, 0.14, 0.16, 0.22),
        alignments=("center", "left", "right", "right", "left", "left"),
        subtitle="제품 B 물류 센터 출하 상세",
        worksheet_name="PRODUCT_B_SHIPMENTS",
        highlight_labels=("3분기",),
        total_labels=("누적 출하",),
        muted_columns=(5,),
        row_height=40,
    )
    return _episode(
        episode_id=f"chart_to_detail_lookup_l2_s{seed}",
        family="chart_to_detail_lookup",
        level=2,
        seed=seed,
        question="막대 차트에서 제품 B가 가장 높은 분기의 상세 출하량은 몇 개인가?",
        answer=answer,
        sheets=[
            _sheet("summary", "요약", [_page(page_id="summary-p1", title="요약 차트", elements=[chart, legend])]),
            _sheet("detail", "상세", [_page(page_id="detail-p1", title="상세 표", elements=[detail_table])]),
        ],
        max_actions=9,
        answer_suffix="개",
    )


def _chart_to_detail_lookup_level_3(seed: int) -> EpisodeSpec:
    rng = random.Random(seed + 606)
    platform = (72.0 + rng.randint(0, 2), 76.0 + rng.randint(0, 2), 81.0 + rng.randint(0, 2), 79.0 + rng.randint(0, 2))
    service = (65.0 + rng.randint(0, 2), 68.0 + rng.randint(0, 2), 70.0 + rng.randint(0, 2), 74.0 + rng.randint(0, 2))
    detail_values = (7_200 + 50 * rng.randint(0, 4), 7_600 + 50 * rng.randint(0, 4), 8_350 + 50 * rng.randint(0, 4), 7_900 + 50 * rng.randint(0, 4))
    answer = detail_values[2]
    chart_layout = _chart_focus_layout()
    detail_layout = _table_focus_layout(height=402)

    chart = _chart(
        element_id="line-chart",
        chart_type="line",
        title="월별 플랫폼 지수 추이",
        rect=chart_layout["chart"],
        categories=("1월", "2월", "3월", "4월"),
        series=(
            ChartSeriesSpec(name="플랫폼", color=PALETTE["rose"], values=platform),
            ChartSeriesSpec(name="서비스", color=PALETTE["blue"], values=service),
        ),
        y_axis_label="활성 지수",
        subtitle="기간별 추세",
    )
    legend = _legend(
        element_id="line-legend",
        title="범례",
        rect=chart_layout["legend"],
        items=(("플랫폼", PALETTE["rose"]), ("서비스", PALETTE["blue"])),
    )
    detail_table = _spreadsheet_table(
        element_id="conversion-table",
        title="플랫폼 유료 전환 건수",
        rect=detail_layout["main"],
        headers=("No.", "월", "유료 전환 (건)", "체험 전환율", "CAC", "비고"),
        rows=[
            ("01", "1월", f"{detail_values[0]:,}", f"{4.8 + 0.1 * rng.randint(0, 2):.1f}%", f"{39_000 + 1_000 * rng.randint(0, 2):,}", "기준"),
            ("02", "2월", f"{detail_values[1]:,}", f"{5.0 + 0.1 * rng.randint(0, 2):.1f}%", f"{38_000 + 1_000 * rng.randint(0, 2):,}", "기준"),
            ("03", "3월", f"{detail_values[2]:,}", f"{5.6 + 0.1 * rng.randint(0, 2):.1f}%", f"{36_000 + 1_000 * rng.randint(0, 2):,}", "최고 추세"),
            ("04", "4월", f"{detail_values[3]:,}", f"{5.2 + 0.1 * rng.randint(0, 2):.1f}%", f"{37_000 + 1_000 * rng.randint(0, 2):,}", "유지"),
            ("05", "월평균", f"{round(sum(detail_values) / 4):,}", f"{5.1 + 0.1 * rng.randint(0, 1):.1f}%", f"{37_500 + 500 * rng.randint(0, 2):,}", "참고"),
            ("06", "CRM 전환", f"{2_900 + 50 * rng.randint(0, 2):,}", f"{6.4 + 0.1 * rng.randint(0, 1):.1f}%", f"{21_000 + 1_000 * rng.randint(0, 1):,}", "보조"),
            ("07", "누적 전환", f"{sum(detail_values):,}", f"{5.1 + 0.1 * rng.randint(0, 1):.1f}%", f"{37_000 + 500 * rng.randint(0, 2):,}", "합계"),
        ],
        column_weights=(0.08, 0.14, 0.22, 0.18, 0.16, 0.22),
        alignments=("center", "left", "right", "right", "right", "left"),
        subtitle="월별 플랫폼 전환 퍼널 상세",
        worksheet_name="PAID_CONVERSION",
        highlight_labels=("3월",),
        total_labels=("누적 전환",),
        muted_columns=(5,),
        row_height=38,
    )
    return _episode(
        episode_id=f"chart_to_detail_lookup_l3_s{seed}",
        family="chart_to_detail_lookup",
        level=3,
        seed=seed,
        question="라인 차트에서 플랫폼 추이가 가장 높은 월의 유료 전환 건수는 몇 건인가?",
        answer=answer,
        sheets=[
            _sheet("summary", "요약", [_page(page_id="summary-p1", title="요약 차트", elements=[chart, legend])]),
            _sheet("appendix", "부록", [_page(page_id="appendix-p1", title="상세 표", elements=[detail_table])]),
        ],
        max_actions=9,
        answer_suffix="건",
    )


def _scale_shift_cross_sheet_level_1(seed: int) -> EpisodeSpec:
    rng = random.Random(seed + 707)
    q2_summary = 12 + rng.randint(0, 2)
    q1_detail = 850 + 20 * rng.randint(0, 4)
    answer = (q2_summary * 100_000_000) + (q1_detail * 1_000_000)
    summary_layout = _table_focus_layout(height=334)
    detail_layout = _summary_split_layout()

    summary_table = _spreadsheet_table(
        element_id="summary-scale",
        title="클라우드 매출 요약",
        rect=summary_layout["main"],
        headers=("No.", "지표", "금액 (억원)", "예산", "달성률", "비고"),
        rows=[
            ("01", "1분기 클라우드 예산", str(10 + rng.randint(0, 2)), str(9 + rng.randint(0, 2)), f"{103 + rng.randint(0, 3)}%", "참고"),
            ("02", "2분기 클라우드 매출", str(q2_summary), str(q2_summary - 1), f"{106 + rng.randint(0, 3)}%", "질문 대상"),
            ("03", "상반기 누계", str(q2_summary + 10 + rng.randint(0, 2)), str(q2_summary + 8), f"{104 + rng.randint(0, 3)}%", "요약"),
            ("04", "ARR", str(26 + rng.randint(0, 2)), str(25 + rng.randint(0, 2)), f"{101 + rng.randint(0, 2)}%", "참고"),
            ("05", "신규 계약", str(6 + rng.randint(0, 1)), str(5 + rng.randint(0, 1)), f"{108 + rng.randint(0, 2)}%", "참고"),
            ("06", "해지 차감", f"-{1 + rng.randint(0, 1)}", f"-{1}", f"{96 + rng.randint(0, 2)}%", "참고"),
        ],
        column_weights=(0.08, 0.28, 0.18, 0.16, 0.12, 0.18),
        alignments=("center", "left", "right", "right", "right", "left"),
        subtitle="요약 시트는 억원 단위를 사용합니다.",
        worksheet_name="CLOUD_SUMMARY",
        highlight_labels=("2분기 클라우드 매출",),
        muted_columns=(5,),
        row_height=40,
    )
    detail_table = _spreadsheet_table(
        element_id="detail-scale",
        title="클라우드 상세 실적",
        rect=detail_layout["main"],
        headers=("No.", "지표", "금액 (백만원)", "계약건", "YoY", "비고"),
        rows=[
            ("01", "1분기 클라우드 매출", str(q1_detail), f"{48 + rng.randint(0, 3)}", f"+{8.5 + 0.2 * rng.randint(0, 2):.1f}%", "질문 대상"),
            ("02", "2분기 클라우드 참고값", str(910 + 20 * rng.randint(0, 3)), f"{50 + rng.randint(0, 3)}", f"+{7.2 + 0.2 * rng.randint(0, 2):.1f}%", "참고"),
            ("03", "스토리지 부가매출", str(120 + 10 * rng.randint(0, 2)), f"{11 + rng.randint(0, 2)}", f"+{3.1 + 0.2 * rng.randint(0, 2):.1f}%", "보조"),
            ("04", "전송량 매출", str(86 + 10 * rng.randint(0, 2)), f"{7 + rng.randint(0, 2)}", f"+{2.8 + 0.2 * rng.randint(0, 2):.1f}%", "보조"),
            ("05", "파일럿 차감", f"-{30 + 5 * rng.randint(0, 2)}", f"{0}", f"-{1.1 + 0.1 * rng.randint(0, 1):.1f}%", "참고"),
            ("06", "반기 누계", str(q1_detail + 910), f"{98 + rng.randint(0, 4)}", f"+{7.9 + 0.2 * rng.randint(0, 1):.1f}%", "집계"),
        ],
        column_weights=(0.08, 0.28, 0.18, 0.14, 0.14, 0.18),
        alignments=("center", "left", "right", "right", "right", "left"),
        subtitle="상세 시트는 백만원 단위를 사용합니다.",
        worksheet_name="CLOUD_DETAIL",
        highlight_labels=("1분기 클라우드 매출",),
        total_labels=("반기 누계",),
        muted_columns=(5,),
        row_height=40,
    )
    unit_note = _text_block(
        element_id="detail-unit-note",
        title="단위 안내",
        rect=detail_layout["aside"],
        lines=("상세 시트의 모든 수치는 백만원 단위입니다.",),
        style="note",
        subtitle="주의",
    )
    return _episode(
        episode_id=f"scale_shift_cross_sheet_l1_s{seed}",
        family="scale_shift_cross_sheet",
        level=1,
        seed=seed,
        question="요약 시트의 2분기 값과 상세 시트의 1분기 값을 합친 클라우드 상반기 매출은 원 단위로 얼마인가?",
        answer=answer,
        sheets=[
            _sheet("summary", "요약", [_page(page_id="summary-p1", title="요약 시트", elements=[summary_table])]),
            _sheet("detail", "상세", [_page(page_id="detail-p1", title="상세 시트", elements=[detail_table, unit_note])]),
        ],
        max_actions=9,
    )


def _scale_shift_cross_sheet_level_2(seed: int) -> EpisodeSpec:
    rng = random.Random(seed + 808)
    first_half = 7 + rng.randint(0, 2)
    second_half = 3_800 + 100 * rng.randint(0, 4)
    answer = (first_half * 100_000_000) + (second_half * 10_000)
    table_layout = _table_focus_layout(height=334)

    summary_table = _spreadsheet_table(
        element_id="summary-half",
        title="서비스 실적 요약",
        rect=table_layout["main"],
        headers=("No.", "지표", "금액 (억원)", "예산", "달성률", "비고"),
        rows=[
            ("01", "1분기 서비스 매출", str(3 + rng.randint(0, 1)), str(3), f"{101 + rng.randint(0, 2)}%", "참고"),
            ("02", "2분기 서비스 매출", str(4 + rng.randint(0, 1)), str(4), f"{102 + rng.randint(0, 2)}%", "참고"),
            ("03", "상반기 서비스 매출", str(first_half), str(first_half - 1), f"{104 + rng.randint(0, 2)}%", "질문 대상"),
            ("04", "구독 유지율", str(93 + rng.randint(0, 2)), str(92 + rng.randint(0, 1)), f"{101 + rng.randint(0, 1)}%", "참고"),
            ("05", "업셀 비중", str(17 + rng.randint(0, 2)), str(16 + rng.randint(0, 1)), f"{103 + rng.randint(0, 1)}%", "참고"),
        ],
        column_weights=(0.08, 0.28, 0.18, 0.16, 0.12, 0.18),
        alignments=("center", "left", "right", "right", "right", "left"),
        subtitle="요약 시트는 억원 단위를 사용합니다.",
        worksheet_name="SERVICE_SUMMARY",
        highlight_labels=("상반기 서비스 매출",),
        muted_columns=(5,),
        row_height=44,
    )
    detail_table = _spreadsheet_table(
        element_id="detail-half",
        title="서비스 상세 실적",
        rect=table_layout["main"],
        headers=("No.", "지표", "금액 (만원)", "계약수", "전환율", "비고"),
        rows=[
            ("01", "7월 서비스 매출", f"{1_200 + 50 * rng.randint(0, 2):,}", f"{210 + rng.randint(0, 8)}", f"{4.1 + 0.1 * rng.randint(0, 1):.1f}%", "참고"),
            ("02", "8월 서비스 매출", f"{1_240 + 50 * rng.randint(0, 2):,}", f"{220 + rng.randint(0, 8)}", f"{4.3 + 0.1 * rng.randint(0, 1):.1f}%", "참고"),
            ("03", "9월 서비스 매출", f"{1_360 + 50 * rng.randint(0, 2):,}", f"{236 + rng.randint(0, 8)}", f"{4.5 + 0.1 * rng.randint(0, 1):.1f}%", "참고"),
            ("04", "하반기 서비스 매출", f"{second_half:,}", f"{666 + rng.randint(0, 12)}", f"{4.4 + 0.1 * rng.randint(0, 1):.1f}%", "질문 대상"),
            ("05", "하반기 순증", f"{280 + 10 * rng.randint(0, 2):,}", f"{74 + rng.randint(0, 4)}", f"{2.8 + 0.1 * rng.randint(0, 1):.1f}%", "참고"),
        ],
        column_weights=(0.08, 0.28, 0.18, 0.16, 0.12, 0.18),
        alignments=("center", "left", "right", "right", "right", "left"),
        subtitle="상세 시트는 만원 단위를 사용합니다.",
        worksheet_name="SERVICE_DETAIL",
        highlight_labels=("하반기 서비스 매출",),
        muted_columns=(5,),
        row_height=44,
    )
    return _episode(
        episode_id=f"scale_shift_cross_sheet_l2_s{seed}",
        family="scale_shift_cross_sheet",
        level=2,
        seed=seed,
        question="요약 시트의 상반기 값과 상세 시트의 하반기 값을 합친 서비스 연간 매출은 원 단위로 얼마인가?",
        answer=answer,
        sheets=[
            _sheet("summary", "요약", [_page(page_id="summary-p1", title="요약 시트", elements=[summary_table])]),
            _sheet("detail", "상세", [_page(page_id="detail-p1", title="상세 시트", elements=[detail_table])]),
        ],
        max_actions=9,
    )


def _scale_shift_cross_sheet_level_3(seed: int) -> EpisodeSpec:
    rng = random.Random(seed + 909)
    first_quarter = 4.5 + 0.1 * rng.randint(0, 2)
    second_quarter = 520 + 10 * rng.randint(0, 2)
    pilot_adjustment = 20 + 5 * rng.randint(0, 2)
    answer = int(round((first_quarter * 100_000_000) + ((second_quarter - pilot_adjustment) * 1_000_000)))
    summary_layout = _table_focus_layout(height=330)
    detail_layout = _table_focus_layout(height=330)
    note_layout = _table_focus_layout(height=144)

    summary_table = _spreadsheet_table(
        element_id="summary-quarter",
        title="플랫폼 계약액 요약",
        rect=summary_layout["main"],
        headers=("No.", "지표", "금액 (억원)", "전년", "증감률", "비고"),
        rows=[
            ("01", "1분기 플랫폼 계약액", f"{first_quarter:.1f}", f"{first_quarter - 0.4:.1f}", f"+{9.5 + 0.2 * rng.randint(0, 2):.1f}%", "질문 대상"),
            ("02", "2분기 플랫폼 가이던스", f"{5.0 + 0.1 * rng.randint(0, 2):.1f}", f"{4.7 + 0.1 * rng.randint(0, 2):.1f}", f"+{6.2 + 0.2 * rng.randint(0, 2):.1f}%", "참고"),
            ("03", "ARR", f"{11.2 + 0.2 * rng.randint(0, 2):.1f}", f"{10.6 + 0.2 * rng.randint(0, 2):.1f}", f"+{5.4 + 0.2 * rng.randint(0, 2):.1f}%", "참고"),
            ("04", "순증 계약", f"{1.3 + 0.1 * rng.randint(0, 1):.1f}", f"{1.1 + 0.1 * rng.randint(0, 1):.1f}", f"+{8.1 + 0.2 * rng.randint(0, 2):.1f}%", "참고"),
        ],
        column_weights=(0.08, 0.28, 0.18, 0.16, 0.12, 0.18),
        alignments=("center", "left", "right", "right", "right", "left"),
        subtitle="요약 시트는 억원 단위를 사용합니다.",
        worksheet_name="PLATFORM_SUMMARY",
        highlight_labels=("1분기 플랫폼 계약액",),
        muted_columns=(5,),
        row_height=48,
    )
    detail_table = _spreadsheet_table(
        element_id="detail-quarter",
        title="플랫폼 상세 실적",
        rect=detail_layout["main"],
        headers=("No.", "지표", "금액 (백만원)", "건수", "비중", "비고"),
        rows=[
            ("01", "2분기 플랫폼 계약액", str(second_quarter), f"{31 + rng.randint(0, 2)}", f"{42 + rng.randint(0, 2)}%", "질문 대상"),
            ("02", "기존 고객 증액", str(210 + 10 * rng.randint(0, 2)), f"{9 + rng.randint(0, 1)}", f"{17 + rng.randint(0, 2)}%", "참고"),
            ("03", "신규 로고 매출", str(180 + 10 * rng.randint(0, 2)), f"{7 + rng.randint(0, 1)}", f"{14 + rng.randint(0, 2)}%", "참고"),
            ("04", "파일럿 매출", str(pilot_adjustment), f"{3}", f"{4}%", "제외 대상"),
            ("05", "순계약액", str(second_quarter - pilot_adjustment), f"{28 + rng.randint(0, 2)}", f"{38 + rng.randint(0, 2)}%", "질문용 참고"),
        ],
        column_weights=(0.08, 0.28, 0.18, 0.14, 0.12, 0.20),
        alignments=("center", "left", "right", "right", "right", "left"),
        subtitle="상세 시트는 백만원 단위를 사용합니다.",
        worksheet_name="PLATFORM_DETAIL",
        highlight_labels=("2분기 플랫폼 계약액",),
        accent_labels=("순계약액",),
        muted_columns=(5,),
        row_height=46,
    )
    detail_note = _text_block(
        element_id="detail-adjustment",
        title="2분기 예외",
        rect=note_layout["main"],
        lines=(f"2분기 계약액에는 파일럿 매출 {pilot_adjustment}백만원이 포함되어 있으며 질문에서는 제외합니다.",),
        style="note",
        subtitle="조정 규칙",
    )
    return _episode(
        episode_id=f"scale_shift_cross_sheet_l3_s{seed}",
        family="scale_shift_cross_sheet",
        level=3,
        seed=seed,
        question="1분기 요약값과 조정된 2분기 상세값을 합친 플랫폼 상반기 계약액은 원 단위로 얼마인가?",
        answer=answer,
        sheets=[
            _sheet("summary", "요약", [_page(page_id="summary-p1", title="요약 시트", elements=[summary_table])]),
            _sheet(
                "detail",
                "상세",
                [
                    _page(page_id="detail-p1", title="상세 시트", elements=[detail_table]),
                    _page(page_id="detail-p2", title="상세 부록", elements=[detail_note]),
                ],
            ),
        ],
        max_actions=10,
    )


def _channel_policy_transfer_level_1(seed: int) -> EpisodeSpec:
    example_1_focus = _text_block(
        element_id="example-1-focus",
        title="현재 대상",
        rect=_rect(84, 176, 232, 88),
        lines=("검토 구역",),
        style="callout",
        subtitle="예시 1",
    )
    example_2_focus = _text_block(
        element_id="example-2-focus",
        title="현재 대상",
        rect=_rect(646, 176, 232, 88),
        lines=("기본 구역",),
        style="callout",
        subtitle="예시 2",
    )
    example_1_table = _visual_rule_table(
        element_id="example-1-table",
        title="예시 1",
        rect=_rect(84, 286, 512, 296),
        active_band="검토",
        rows=[
            ("A행", "bottom_left", None, None, "top_right"),
            ("B행", None, None, "bottom_left", None),
            ("C행", "top_right", None, None, None),
        ],
        selected_target=(2, 4),
        subtitle="대상 구역: 검토 · 선택 셀은 테두리로 표시",
    )
    example_2_table = _visual_rule_table(
        element_id="example-2-table",
        title="예시 2",
        rect=_rect(646, 286, 512, 296),
        active_band="기본",
        rows=[
            ("A행", None, None, "top_right", None),
            ("B행", "bottom_left", None, None, None),
            ("C행", None, "top_right", None, "bottom_left"),
        ],
        selected_target=(4, 2),
        subtitle="대상 구역: 기본 · 같은 모양이어도 위치가 다르면 오답",
    )
    examples_hint = _text_block(
        element_id="examples-hint",
        title="관찰 포인트",
        rect=_rect(84, 626, 1074, 118),
        lines=(
            "예시에서는 정답 셀이 얇은 프레임으로 표시됩니다.",
            "상단의 대상 구역과 셀 안의 시각 단서를 함께 읽어야 합니다.",
        ),
        style="note",
        subtitle="텍스트가 아닌 셀 위치 단서",
    )

    query_focus = _text_block(
        element_id="query-focus",
        title="현재 대상",
        rect=_rect(84, 176, 232, 88),
        lines=("검토 구역",),
        style="callout",
        subtitle="질의",
    )
    query_table = _visual_rule_table(
        element_id="query-table",
        title="질의 표",
        rect=_rect(84, 286, 720, 340),
        active_band="검토",
        rows=[
            ("A행", "top_right", None, None, None),
            ("B행", None, "bottom_left", None, None),
            ("C행", None, None, "bottom_left", None),
            ("D행", None, None, None, "top_right"),
        ],
        subtitle="대상 구역: 검토 · 예시와 같은 규칙을 적용",
    )

    choice_specs = [
        ("A", "A행 / 기본 상태", _rect(852, 286, 306, 100)),
        ("B", "B행 / 기본 조치", _rect(852, 398, 306, 100)),
        ("C", "C행 / 검토 상태", _rect(852, 510, 306, 100)),
        ("D", "D행 / 검토 조치", _rect(852, 622, 306, 100)),
    ]
    choice_specs = [
        ("A", "A행", 1, _rect(852, 286, 306, 112)),
        ("B", "B행", 2, _rect(852, 410, 306, 112)),
        ("C", "C행", 3, _rect(852, 534, 306, 112)),
        ("D", "D행", 4, _rect(852, 658, 306, 112)),
    ]
    choice_blocks = [
        _target_choice_preview_table(
            element_id=f"choice-{choice_id.lower()}",
            choice_id=choice_id,
            rect=rect,
            row_label=row_label,
            target_col=target_col,
        )
        for choice_id, row_label, target_col, rect in choice_specs
    ]
    choice_regions = [
        RegionSpec(
            public_id=f"choice-{choice_id.lower()}",
            role="answer_choice",
            label=f"선택지 {choice_id}",
            rect=rect,
            metadata={"choice_id": choice_id, "answer_form": "target_cell_choice"},
        )
        for choice_id, _, _, rect in choice_specs
    ]
    query_note = _text_block(
        element_id="query-note",
        title="질문",
        rect=_rect(84, 648, 720, 102),
        lines=("어느 선택지가 예시와 같은 규칙으로 선택되는 위치인지 고르세요.",),
        style="body",
        subtitle="정답은 선택지 문자로 제출",
    )

    return _choice_episode(
        episode_id="channel_policy_transfer_l1_icon_anchor_pick_v1",
        family="channel_policy_transfer",
        level=1,
        seed=seed,
        question="예시와 같은 규칙을 적용했을 때 선택해야 하는 위치는 어느 선택지인가?",
        answer="D",
        accepted=_accepted_choice_forms("D"),
        sheets=[
            _sheet(
                "examples",
                "예시",
                [
                    _page(
                        page_id="examples-p1",
                        title="예시 시트",
                        elements=[example_1_focus, example_2_focus, example_1_table, example_2_table, examples_hint],
                    )
                ],
            ),
            _sheet(
                "query",
                "질의",
                [
                    _page(
                        page_id="query-p1",
                        title="질의 시트",
                        elements=[query_focus, query_table, *choice_blocks, query_note],
                        regions=choice_regions,
                    )
                ],
            ),
        ],
        max_actions=7,
        metadata={
            "track": "pilot",
            "episode_intent": {
                "primary_operator": "select_scope",
                "support_operator": "transfer_example_rule",
                "primary_visual_cue": "icon_anchor_within_merged_header_band",
                "answer_form": "target_cell_choice",
            },
        },
    )


def _inventory_exception_disambiguation_level_1(seed: int) -> EpisodeSpec:
    examples_hint = _text_block(
        element_id="exception-examples-hint",
        title="관찰 포인트",
        rect=_rect(84, 622, 1074, 118),
        lines=(
            "예시에서는 선택된 행의 상태 셀이 프레임으로 표시됩니다.",
            "줄무늬와 삼각형 중 어떤 표식이 실제 규칙인지 반례 시트에서 좁혀야 합니다.",
        ),
        style="note",
        subtitle="예시만으로는 규칙이 하나로 고정되지 않음",
    )
    example_1_table = _pattern_icon_table(
        element_id="ambiguous-example-1",
        title="예시 1",
        rect=_rect(84, 236, 512, 336),
        rows=[
            ("A행", True, True, True),
            ("B행", False, False, False),
            ("C행", True, True, True),
            ("D행", False, False, False),
        ],
        subtitle="줄무늬 행과 삼각형 행이 우연히 일치",
    )
    example_2_table = _pattern_icon_table(
        element_id="ambiguous-example-2",
        title="예시 2",
        rect=_rect(646, 236, 512, 336),
        rows=[
            ("A행", False, False, False),
            ("B행", True, True, True),
            ("C행", False, False, False),
            ("D행", True, True, True),
        ],
        subtitle="겉으로 보면 줄무늬 규칙도 맞아 보임",
    )

    exception_focus = _text_block(
        element_id="exception-focus",
        title="예외 사례",
        rect=_rect(84, 174, 256, 88),
        lines=("줄무늬 규칙과 삼각형 규칙이 갈라지는 예시",),
        style="callout",
        subtitle="이 시트가 잘못된 가설을 제거",
    )
    exception_table = _pattern_icon_table(
        element_id="exception-table",
        title="예외 표",
        rect=_rect(84, 292, 720, 348),
        rows=[
            ("A행", True, False, False),
            ("B행", False, True, True),
            ("C행", True, True, True),
            ("D행", False, False, False),
        ],
        subtitle="줄무늬는 A행·C행, 삼각형은 B행·C행",
    )
    exception_note = _text_block(
        element_id="exception-note",
        title="해석",
        rect=_rect(852, 292, 306, 212),
        lines=(
            "반례에서는 줄무늬가 있는 행과 프레임이 붙은 행이 서로 다릅니다.",
            "어느 표식이 실제 선택 결과와 일치하는지 표 안에서 직접 비교하세요.",
        ),
        style="body",
        subtitle="반례가 규칙을 확정",
    )

    query_focus = _text_block(
        element_id="statement-query-focus",
        title="질의",
        rect=_rect(84, 174, 256, 88),
        lines=("반례까지 반영한 뒤 맞는 설명을 고르기",),
        style="callout",
        subtitle="statement choice",
    )
    query_table = _pattern_icon_table(
        element_id="statement-query-table",
        title="질의 표",
        rect=_rect(84, 292, 720, 348),
        rows=[
            ("A행", True, False, False),
            ("B행", False, True, False),
            ("C행", False, False, False),
            ("D행", True, True, False),
        ],
        subtitle="줄무늬 행은 A행·D행, 삼각형 행은 B행·D행",
    )
    statement_specs = [
        ("A", "줄무늬가 있는 A행과 D행이 선택 대상이다.", _rect(852, 292, 306, 98)),
        ("B", "삼각형 표식이 있는 B행과 D행이 선택 대상이다.", _rect(852, 402, 306, 98)),
        ("C", "두 표식이 모두 있는 D행만 선택 대상이다.", _rect(852, 512, 306, 98)),
        ("D", "줄무늬나 삼각형 중 하나라도 있으면 선택 대상이다.", _rect(852, 622, 306, 98)),
    ]
    statement_specs = [
        ("A", ("A행", "D행"), _rect(852, 292, 306, 118)),
        ("B", ("B행", "D행"), _rect(852, 422, 306, 118)),
        ("C", ("D행",), _rect(852, 552, 306, 118)),
        ("D", ("A행", "B행", "D행"), _rect(852, 682, 306, 118)),
    ]
    statement_blocks = [
        _statement_choice_preview_table(
            element_id=f"statement-{choice_id.lower()}",
            choice_id=choice_id,
            rect=rect,
            selected_rows=selected_rows,
        )
        for choice_id, selected_rows, rect in statement_specs
    ]
    statement_regions = [
        RegionSpec(
            public_id=f"statement-{choice_id.lower()}",
            role="answer_choice",
            label=f"선택지 {choice_id}",
            rect=rect,
            metadata={"choice_id": choice_id, "answer_form": "statement_choice"},
        )
        for choice_id, _, rect in statement_specs
    ]

    return _choice_episode(
        episode_id="inventory_exception_disambiguation_l1_pattern_vs_icon_statement_v1",
        family="inventory_exception_disambiguation",
        level=1,
        seed=seed,
        question="반례까지 반영했을 때 질의 표에 대한 올바른 설명은 어느 선택지인가?",
        answer="B",
        accepted=_accepted_choice_forms("B"),
        sheets=[
            _sheet(
                "examples",
                "예시",
                [_page(page_id="examples-p1", title="예시 시트", elements=[example_1_table, example_2_table, examples_hint])],
            ),
            _sheet(
                "exception",
                "예외",
                [_page(page_id="exception-p1", title="예외 시트", elements=[exception_focus, exception_table, exception_note])],
            ),
            _sheet(
                "query",
                "질의",
                [
                    _page(
                        page_id="query-p1",
                        title="질의 시트",
                        elements=[query_focus, query_table, *statement_blocks],
                        regions=statement_regions,
                    )
                ],
            ),
        ],
        max_actions=8,
        metadata={
            "track": "pilot",
            "episode_intent": {
                "primary_operator": "verify_statement",
                "support_operator": "disambiguate_by_exception",
                "primary_visual_cue": "pattern_vs_icon",
                "answer_form": "statement_choice",
            },
        },
    )


CANONICAL_FAMILY_LEVELS: dict[str, dict[int, Callable[[int], EpisodeSpec]]] = canonical_level_wrappers()
FAMILY_LEVELS: dict[str, dict[int, Callable[[int], EpisodeSpec]]] = dict(CANONICAL_FAMILY_LEVELS)


def list_families() -> list[str]:
    return sorted(FAMILY_LEVELS)


def list_legacy_families() -> list[str]:
    return []


def list_pilot_families() -> list[str]:
    return []


def list_canonical_families() -> list[str]:
    return sorted(CANONICAL_FAMILY_LEVELS)


def list_levels(family: str) -> list[int]:
    if family not in FAMILY_LEVELS:
        raise KeyError(f"Unknown family: {family}")
    return sorted(FAMILY_LEVELS[family])


def list_templates(family: str, level: int) -> list[str]:
    return _canonical_list_templates(family, level)


def canonical_seed_capacity(family: str, level: int) -> int:
    return _canonical_seed_capacity(family, level)


def benchmark_split_manifest() -> dict[str, list[dict[str, object]]]:
    return _canonical_benchmark_split_manifest()


def benchmark_episode_records(*, split: str | None = None) -> list[dict[str, object]]:
    return _canonical_benchmark_episode_records(split=split)


def canonical_episode_catalog() -> list[dict[str, object]]:
    return _canonical_episode_catalog()


def eval_hard_episode_catalog() -> list[dict[str, object]]:
    return _eval_hard_episode_catalog()


def benchmark_suite_manifest() -> dict[str, list[dict[str, object]]]:
    manifest = _benchmark_suite_manifest()
    for pack in _list_instance_packs():
        manifest[pack.pack_id] = [instance.to_dict() for instance in pack.instances]
    return manifest


def benchmark_suite_records(*, suite: str | None = None) -> list[dict[str, object]]:
    if suite is None:
        records = _benchmark_suite_records(suite=None)
        for pack in _list_instance_packs():
            records.extend(_instance_benchmark_records(pack.pack_id))
        return records
    if suite is not None:
        instance_pack_ids = {pack.pack_id for pack in _list_instance_packs()}
        if suite in instance_pack_ids:
            return _instance_benchmark_records(suite)
    return _benchmark_suite_records(suite=suite)


def list_instance_packs():
    return _list_instance_packs()


def load_instance_pack(pack_id: str):
    return _load_instance_pack(pack_id)


def list_instances(pack_id: str):
    return _list_instances(pack_id)


def load_instance(instance_id: str) -> EpisodeSpec:
    return _load_instance(instance_id)


def instance_benchmark_records(pack_id: str) -> list[dict[str, object]]:
    return _instance_benchmark_records(pack_id)


def generate_episode(family: str, level: int, seed: int = 0, *, template_id: str | None = None) -> EpisodeSpec:
    if family not in FAMILY_LEVELS:
        raise KeyError(f"Unknown family: {family}")
    if level not in FAMILY_LEVELS[family]:
        raise KeyError(f"Unknown level {level} for family {family}")
    return generate_canonical_episode(family, level, seed, template_id=template_id)
