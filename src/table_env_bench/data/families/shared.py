"""Shared helpers for canonical family generation."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Iterable

from table_env_bench.data.models import (
    AnswerSpec,
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
CANONICAL_SEEDS_PER_TEMPLATE = 8


def _dedupe_strings(values: Iterable[Any]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in seen:
            seen.add(text)
            ordered.append(text)
    return tuple(ordered)


def _copy_jsonish(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _copy_jsonish(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_copy_jsonish(item) for item in value]
    return value


def _normalize_required_navigation(
    navigation: dict[str, Any] | None,
    *,
    required_sheet_ids: Iterable[str] = (),
    required_page_refs: Iterable[str] = (),
) -> dict[str, Any]:
    raw = dict(navigation or {})
    normalized: dict[str, Any] = {}
    normalized["required_sheet_ids"] = list(
        _dedupe_strings((*required_sheet_ids, *raw.get("required_sheet_ids", ())))
    )
    normalized["required_page_refs"] = list(
        _dedupe_strings((*required_page_refs, *raw.get("required_page_refs", ())))
    )
    normalized["required_notes"] = [dict(item) for item in raw.get("required_notes", ())]
    normalized["required_viewport_states"] = [
        _copy_jsonish(item) for item in raw.get("required_viewport_states", ())
    ]
    normalized["forbidden_shortcuts"] = list(
        _dedupe_strings(raw.get("forbidden_shortcuts", ()))
    )
    for key, value in raw.items():
        if key not in normalized:
            normalized[str(key)] = _copy_jsonish(value)
    return normalized


def _derive_required_actions(required_navigation: dict[str, Any]) -> tuple[str, ...]:
    actions: list[str] = []
    sheet_ids = list(required_navigation.get("required_sheet_ids", ()))
    page_refs = list(required_navigation.get("required_page_refs", ()))
    notes = list(required_navigation.get("required_notes", ()))
    viewport_states = list(required_navigation.get("required_viewport_states", ()))

    if len(sheet_ids) > 1:
        actions.append("must_switch_sheet")
    if notes:
        actions.append("must_open_note")
    if any(str(page_ref).split(":", 1)[0] == "exception" for page_ref in page_refs):
        actions.append("must_visit_exception")
    if any(str(page_ref).split(":", 1)[0] == "legend" for page_ref in page_refs):
        actions.append("must_visit_legend")
    if any("examples-p2" in str(page_ref) for page_ref in page_refs):
        actions.append("must_visit_examples_page2")

    required_action_types: list[str] = []
    for state in viewport_states:
        if isinstance(state, dict):
            required_action_types.extend(str(item) for item in state.get("required_action_types", ()))
    if any(action == "zoom_in" for action in required_action_types):
        actions.append("must_zoom")
    if any(action.startswith("pan_") for action in required_action_types):
        actions.append("must_pan")
    return _dedupe_strings(actions)


def navigation_compatibility_mirrors(required_navigation: dict[str, Any]) -> dict[str, list[str]]:
    normalized = _normalize_required_navigation(required_navigation)
    return {
        "required_sheet_ids": list(normalized["required_sheet_ids"]),
        "required_page_refs": list(normalized["required_page_refs"]),
        "required_actions": list(_derive_required_actions(normalized)),
    }

@dataclass(frozen=True)
class TemplateManifest:
    family: str
    level: int
    template_id: str
    template_label: str
    latent_rule: str
    operator_tags: tuple[str, ...]
    cue_tags: tuple[str, ...]
    answer_form: str
    primary_operator: str
    support_operator: str | None
    required_visual_cues: tuple[str, ...]
    required_surfaces: tuple[str, ...]
    capability_axes: tuple[str, ...]
    required_sheet_ids: tuple[str, ...]
    required_page_refs: tuple[str, ...]
    allowed_cue_variants: tuple[str, ...]
    distractor_policy: str
    level_rationale: str
    text_only_failure_modes: tuple[str, ...]
    distractor_failure_modes: tuple[str, ...]
    task_archetype: str = "review_verification"
    scenario_context: str = ""
    benchmark_track: str = "canonical_real_tableqa"
    reasoning_archetype: str = "induce_apply"
    abstraction_tier: str = "abstract_worksheet"
    support_surface_policy: str = "optional"
    qa_dependency: str = "hybrid_induction_tableqa"
    generalization_group: str | None = None
    level_knobs: dict[str, Any] = field(default_factory=dict)
    max_actions: int = 10
    difficulty_tier: str = "canonical"
    required_capabilities: tuple[str, ...] = ()
    required_actions: tuple[str, ...] = ()
    required_navigation: dict[str, Any] = field(default_factory=dict)
    required_evidence: tuple[dict[str, Any], ...] = ()
    expected_min_steps: int = 3
    expected_reasoning_steps: tuple[int, int] = (2, 3)
    shortcut_probes: tuple[str, ...] = ()
    holdout_group: str | None = None
    pair_group: str | None = None
    variant: str | None = None

    def __post_init__(self) -> None:
        normalized_navigation = _normalize_required_navigation(
            self.required_navigation,
            required_sheet_ids=self.required_sheet_ids,
            required_page_refs=self.required_page_refs,
        )
        derived_actions = _derive_required_actions(normalized_navigation)
        legacy_extra_actions = tuple(action for action in self.required_actions if action not in derived_actions)
        object.__setattr__(self, "required_navigation", normalized_navigation)
        object.__setattr__(self, "required_sheet_ids", tuple(normalized_navigation["required_sheet_ids"]))
        object.__setattr__(self, "required_page_refs", tuple(normalized_navigation["required_page_refs"]))
        object.__setattr__(self, "required_actions", (*derived_actions, *legacy_extra_actions))

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "level": self.level,
            "template_id": self.template_id,
            "template_label": self.template_label,
            "latent_rule": self.latent_rule,
            "operator_tags": list(self.operator_tags),
            "cue_tags": list(self.cue_tags),
            "answer_form": self.answer_form,
            "primary_operator": self.primary_operator,
            "support_operator": self.support_operator,
            "required_visual_cues": list(self.required_visual_cues),
            "required_surfaces": list(self.required_surfaces),
            "capability_axes": list(self.capability_axes),
            "required_sheet_ids": list(self.required_sheet_ids),
            "required_page_refs": list(self.required_page_refs),
            "task_archetype": self.task_archetype,
            "scenario_context": self.scenario_context,
            "benchmark_track": self.benchmark_track,
            "reasoning_archetype": self.reasoning_archetype,
            "abstraction_tier": self.abstraction_tier,
            "support_surface_policy": self.support_surface_policy,
            "qa_dependency": self.qa_dependency,
            "generalization_group": self.generalization_group,
            "required_navigation": _copy_jsonish(self.required_navigation),
            "allowed_cue_variants": list(self.allowed_cue_variants),
            "distractor_policy": self.distractor_policy,
            "level_rationale": self.level_rationale,
            "text_only_failure_modes": list(self.text_only_failure_modes),
            "distractor_failure_modes": list(self.distractor_failure_modes),
            "level_knobs": dict(self.level_knobs),
            "seed_slots": list(range(CANONICAL_SEEDS_PER_TEMPLATE)),
            "max_actions": self.max_actions,
            "difficulty_tier": self.difficulty_tier,
            "required_capabilities": list(self.required_capabilities or self.capability_axes),
            "required_actions": list(self.required_actions),
            "required_evidence": [dict(item) for item in self.required_evidence],
            "expected_min_steps": self.expected_min_steps,
            "expected_reasoning_steps": list(self.expected_reasoning_steps),
            "shortcut_probes": list(self.shortcut_probes),
            "holdout_group": self.holdout_group,
            "pair_group": self.pair_group,
            "variant": self.variant,
        }


@dataclass(frozen=True)
class ChoiceCardSpec:
    choice_id: str
    title: str
    lines: tuple[str, ...]
    style: str = "body"
    metadata: dict[str, Any] = field(default_factory=dict)


def rect(x: float, y: float, width: float, height: float) -> RectSpec:
    return RectSpec(x=x, y=y, width=width, height=height)


def note(note_id: str, title: str, text: str) -> NoteSpec:
    return NoteSpec(id=note_id, title=title, text=text)


def region(
    public_id: str,
    role: str,
    label: str,
    box: RectSpec,
    *,
    linked_note_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> RegionSpec:
    return RegionSpec(
        public_id=public_id,
        role=role,
        label=label,
        rect=box,
        linked_note_id=linked_note_id,
        metadata=metadata or {},
    )


def cell(
    row: int,
    col: int,
    text: str,
    *,
    row_span: int = 1,
    col_span: int = 1,
    style: str = "body",
    align: str = "center",
    metadata: dict[str, Any] | None = None,
) -> TableCellSpec:
    return TableCellSpec(
        row=row,
        col=col,
        text=text,
        row_span=row_span,
        col_span=col_span,
        style=style,
        align=align,
        metadata=metadata or {},
    )


def text_block(
    element_id: str,
    title: str,
    box: RectSpec,
    lines: Iterable[str],
    *,
    style: str = "body",
    subtitle: str | None = None,
) -> TextBlockElementSpec:
    metadata: dict[str, Any] = {}
    if subtitle:
        metadata["subtitle"] = subtitle
    return TextBlockElementSpec(
        element_id=element_id,
        rect=box,
        title=title,
        lines=tuple(lines),
        style=style,
        metadata=metadata,
    )


def legend(
    element_id: str,
    title: str,
    box: RectSpec,
    items: Iterable[tuple[str, str]],
    *,
    subtitle: str | None = None,
) -> LegendElementSpec:
    metadata: dict[str, Any] = {}
    if subtitle:
        metadata["subtitle"] = subtitle
    return LegendElementSpec(
        element_id=element_id,
        rect=box,
        title=title,
        items=tuple(LegendItemSpec(label=label, color=color) for label, color in items),
        metadata=metadata,
    )


def _column_widths(total_width: float, weights: tuple[float, ...]) -> tuple[int, ...]:
    total = sum(weights)
    scaled = [int(round(total_width * (weight / total))) for weight in weights]
    scaled[-1] += int(total_width) - sum(scaled)
    return tuple(scaled)


def table_from_cells(
    element_id: str,
    title: str,
    box: RectSpec,
    *,
    n_rows: int,
    n_cols: int,
    cells: Iterable[TableCellSpec],
    column_weights: tuple[float, ...] | None = None,
    row_heights: tuple[int, ...] | None = None,
    subtitle: str | None = None,
    worksheet_name: str | None = None,
) -> TableElementSpec:
    weights = column_weights or tuple(1.0 for _ in range(n_cols))
    heights = row_heights or tuple(40 if row_index < 2 else 38 for row_index in range(n_rows))
    metadata = {
        "subtitle": subtitle or "시각 단서가 포함된 표",
        "worksheet_name": worksheet_name or element_id.upper().replace("-", "_"),
        "excel_chrome": True,
        "freeze_columns": 1,
    }
    return TableElementSpec(
        element_id=element_id,
        rect=box,
        title=title,
        n_rows=n_rows,
        n_cols=n_cols,
        column_widths=_column_widths(box.width, weights),
        row_heights=heights,
        cells=tuple(cells),
        metadata=metadata,
    )


def _normalize_value(value: str | dict[str, Any], default_align: str) -> dict[str, Any]:
    if isinstance(value, dict):
        payload = dict(value)
        payload.setdefault("text", "")
        payload.setdefault("style", "body")
        payload.setdefault("align", default_align)
        payload.setdefault("metadata", {})
        return payload
    return {"text": value, "style": "body", "align": default_align, "metadata": {}}


def make_banded_table(
    *,
    element_id: str,
    title: str,
    box: RectSpec,
    band_labels: tuple[str, ...],
    sub_headers: tuple[str, ...],
    row_labels: tuple[str, ...],
    values: list[list[list[str | dict[str, Any]]]],
    subtitle: str,
    column_weights: tuple[float, ...] | None = None,
    row_height: int = 38,
) -> TableElementSpec:
    n_bands = len(band_labels)
    n_cols = 1 + (n_bands * len(sub_headers))
    cells: list[TableCellSpec] = [
        cell(0, 0, "항목", row_span=2, style="header"),
    ]
    for band_index, band_label in enumerate(band_labels):
        start_col = 1 + (band_index * len(sub_headers))
        cells.append(cell(0, start_col, band_label, col_span=len(sub_headers), style="header"))
        for sub_index, sub_header in enumerate(sub_headers):
            cells.append(cell(1, start_col + sub_index, sub_header, style="header"))

    for row_index, row_label in enumerate(row_labels, start=2):
        body_row = values[row_index - 2]
        row_style = "row_label"
        if row_label.startswith("합계") or row_label.startswith("소계"):
            row_style = "total_label"
        cells.append(cell(row_index, 0, row_label, style=row_style, align="left"))
        for band_index, band_cells in enumerate(body_row):
            for sub_index, raw_value in enumerate(band_cells):
                resolved = _normalize_value(raw_value, default_align="center")
                style = resolved["style"]
                if row_style == "total_label" and style == "body":
                    style = "total"
                cells.append(
                    cell(
                        row_index,
                        1 + (band_index * len(sub_headers)) + sub_index,
                        str(resolved["text"]),
                        style=style,
                        align=str(resolved["align"]),
                        metadata=dict(resolved["metadata"]),
                    )
                )

    return table_from_cells(
        element_id,
        title,
        box,
        n_rows=2 + len(row_labels),
        n_cols=n_cols,
        cells=cells,
        column_weights=column_weights or ((1.85,) + tuple(1.0 for _ in range(n_cols - 1))),
        row_heights=(38, 34) + tuple(row_height for _ in row_labels),
        subtitle=subtitle,
    )


def choice_cards(
    *,
    prefix: str,
    cards: Iterable[ChoiceCardSpec],
    y: float = 566,
    answer_form: str,
    subtitle: str | None = None,
    columns: int = 4,
    width: float = 250.0,
    height: float = 118.0,
    gap_x: float = 18.0,
    gap_y: float = 18.0,
    x0: float = 84.0,
) -> tuple[tuple[TextBlockElementSpec, ...], tuple[RegionSpec, ...]]:
    card_list = list(cards)
    if columns <= 0:
        raise ValueError("columns must be positive")
    elements: list[TextBlockElementSpec] = []
    regions: list[RegionSpec] = []
    for index, card_spec in enumerate(card_list):
        row_index, col_index = divmod(index, columns)
        box = rect(x0 + (width + gap_x) * col_index, y + (height + gap_y) * row_index, width, height)
        lines = (card_spec.title, *card_spec.lines)
        element_id = f"{prefix}-{card_spec.choice_id.lower()}"
        elements.append(
            text_block(
                element_id,
                f"선택지 {card_spec.choice_id}",
                box,
                lines,
                style=card_spec.style,
                subtitle=subtitle,
            )
        )
        metadata = {"choice_id": card_spec.choice_id, "answer_form": answer_form}
        metadata.update(card_spec.metadata)
        regions.append(region(element_id, "answer_choice", f"선택지 {card_spec.choice_id}", box, metadata=metadata))
    return tuple(elements), tuple(regions)


def query_choice_cards(
    *,
    prefix: str,
    cards: Iterable[ChoiceCardSpec],
    answer_form: str,
    y: float = 248.0,
    subtitle: str | None = None,
    columns: int = 2,
    width: float = 514.0,
    height: float = 126.0,
    gap_x: float = 26.0,
    gap_y: float = 20.0,
    x0: float = 84.0,
) -> tuple[tuple[TextBlockElementSpec, ...], tuple[RegionSpec, ...]]:
    return choice_cards(
        prefix=prefix,
        cards=cards,
        y=y,
        answer_form=answer_form,
        subtitle=subtitle,
        columns=columns,
        width=width,
        height=height,
        gap_x=gap_x,
        gap_y=gap_y,
        x0=x0,
    )


def _estimate_wrapped_line_count(lines: Iterable[str], width: float) -> int:
    max_chars = max(18, int((width - 36) / 14))
    total = 0
    for line in lines:
        total += max(1, math.ceil(len(line) / max_chars))
    return total


def _query_block_height(line_count: int) -> float:
    # Query header blocks render into a scaled viewport while text line-height stays fixed
    # in the canvas renderer, so these boxes need extra vertical slack to avoid clipping.
    return 78.0 + max(0, line_count - 1) * 22.0


def query_header_blocks(
    *,
    target_title: str,
    target_lines: tuple[str, ...],
    guidance_title: str,
    guidance_lines: tuple[str, ...],
    mode: str = "auto",
) -> tuple[tuple[TextBlockElementSpec, TextBlockElementSpec], float]:
    if mode not in {"auto", "compact", "stacked"}:
        raise ValueError(f"Unsupported query header layout mode: {mode}")

    compact_width = 532.0
    stacked_x = 72.0
    stacked_width = 1136.0
    target_compact_lines = _estimate_wrapped_line_count(target_lines, compact_width)
    guidance_compact_lines = _estimate_wrapped_line_count(guidance_lines, compact_width)
    resolved_mode = mode
    if mode == "auto":
        resolved_mode = "compact" if max(target_compact_lines, guidance_compact_lines) <= 2 else "stacked"

    if resolved_mode == "compact":
        target_box = rect(84, 164, compact_width, _query_block_height(target_compact_lines))
        guidance_box = rect(644, 164, compact_width, _query_block_height(guidance_compact_lines))
        next_y = max(target_box.y + target_box.height, guidance_box.y + guidance_box.height) + 28
    else:
        target_stacked_lines = _estimate_wrapped_line_count(target_lines, stacked_width)
        guidance_stacked_lines = _estimate_wrapped_line_count(guidance_lines, stacked_width)
        target_box = rect(stacked_x, 164, stacked_width, _query_block_height(target_stacked_lines))
        guidance_box = rect(
            stacked_x,
            target_box.y + target_box.height + 20,
            stacked_width,
            _query_block_height(guidance_stacked_lines),
        )
        next_y = guidance_box.y + guidance_box.height + 28

    return (
        (
            text_block("query-target", target_title, target_box, target_lines, style="callout"),
            text_block("query-guidance", guidance_title, guidance_box, guidance_lines, style="note"),
        ),
        next_y,
    )


def page(
    page_id: str,
    title: str,
    *,
    elements: Iterable[Any],
    regions: Iterable[RegionSpec] = (),
    notes: Iterable[NoteSpec] = (),
    metadata: dict[str, Any] | None = None,
) -> PageSpec:
    return PageSpec(
        page_id=page_id,
        title=title,
        width=PAGE_WIDTH,
        height=PAGE_HEIGHT,
        elements=tuple(elements),
        regions=tuple(regions),
        notes=tuple(notes),
        metadata=metadata or {},
    )


def sheet(sheet_id: str, tab_label: str, pages: Iterable[PageSpec], *, metadata: dict[str, Any] | None = None) -> SheetSpec:
    return SheetSpec(sheet_id=sheet_id, tab_label=tab_label, pages=tuple(pages), metadata=metadata or {})


def build_episode_metadata(
    manifest: TemplateManifest,
    *,
    seed_slot: int,
    relevant_region_ids: Iterable[str] = (),
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = manifest.to_dict()
    metadata.update(
        {
            "track": manifest.benchmark_track,
            "family": manifest.family,
            "level": manifest.level,
            "template_id": manifest.template_id,
            "seed_slot": seed_slot,
            "relevant_region_ids": list(relevant_region_ids),
            "difficulty_tier": manifest.difficulty_tier,
            "primary_operator": manifest.primary_operator,
            "support_operator": manifest.support_operator,
            "required_visual_cues": list(manifest.required_visual_cues),
            "task_archetype": manifest.task_archetype,
            "scenario_context": manifest.scenario_context,
            "benchmark_track": manifest.benchmark_track,
            "reasoning_archetype": manifest.reasoning_archetype,
            "abstraction_tier": manifest.abstraction_tier,
            "support_surface_policy": manifest.support_surface_policy,
            "qa_dependency": manifest.qa_dependency,
            "generalization_group": manifest.generalization_group or f"{manifest.family}:{manifest.template_id}:l{manifest.level}",
            "level_rationale": manifest.level_rationale,
            "text_only_failure_modes": list(manifest.text_only_failure_modes),
            "distractor_failure_modes": list(manifest.distractor_failure_modes),
            "required_capabilities": list(manifest.required_capabilities or manifest.capability_axes),
            "required_navigation": _copy_jsonish(manifest.required_navigation),
            "required_sheet_ids": list(manifest.required_sheet_ids),
            "required_page_refs": list(manifest.required_page_refs),
            "required_actions": list(manifest.required_actions),
            "required_evidence": [dict(item) for item in manifest.required_evidence],
            "expected_min_steps": manifest.expected_min_steps,
            "expected_reasoning_steps": list(manifest.expected_reasoning_steps),
            "shortcut_probes": list(manifest.shortcut_probes),
            "holdout_group": manifest.holdout_group,
            "pair_group": manifest.pair_group,
            "variant": manifest.variant,
        }
    )
    if extra:
        metadata.update(extra)
    return metadata


def episode(
    *,
    manifest: TemplateManifest,
    family_display_name: str,
    question: str,
    workbook_title: str,
    sheets: Iterable[SheetSpec],
    answer: str | AnswerSpec,
    seed_slot: int,
    metadata_extra: dict[str, Any] | None = None,
) -> EpisodeSpec:
    answer_spec = answer if isinstance(answer, AnswerSpec) else AnswerSpec(canonical=str(answer), normalizer="ko_answer")
    workbook = WorkbookSpec(
        workbook_id=f"{manifest.family}-{manifest.level}-{manifest.template_id}",
        title=workbook_title,
        sheets=tuple(sheets),
        metadata={"track": manifest.benchmark_track, "template_id": manifest.template_id, "benchmark_track": manifest.benchmark_track},
    )
    metadata = build_episode_metadata(
        manifest,
        seed_slot=seed_slot,
        relevant_region_ids=(metadata_extra or {}).pop("relevant_region_ids", ()),
        extra=metadata_extra,
    )
    return EpisodeSpec(
        episode_id=f"{manifest.family}_{manifest.template_id}_l{manifest.level}_s{seed_slot}",
        family=manifest.family,
        family_display_name=family_display_name,
        level=manifest.level,
        seed=seed_slot,
        locale="ko-KR",
        question=question,
        workbook=workbook,
        answer=answer_spec,
        max_actions=manifest.max_actions,
        metadata=metadata,
    )


def resolve_template_seed(
    manifests: tuple[TemplateManifest, ...],
    seed: int,
    *,
    template_id: str | None = None,
) -> tuple[TemplateManifest, int]:
    if template_id is not None:
        for manifest in manifests:
            if manifest.template_id == template_id:
                return manifest, seed % CANONICAL_SEEDS_PER_TEMPLATE
        raise KeyError(f"Unknown template_id: {template_id}")

    template_index = (seed // CANONICAL_SEEDS_PER_TEMPLATE) % len(manifests)
    seed_slot = seed % CANONICAL_SEEDS_PER_TEMPLATE
    return manifests[template_index], seed_slot


def rotate(items: tuple[str, ...], amount: int) -> tuple[str, ...]:
    if not items:
        return items
    step = amount % len(items)
    return items[step:] + items[:step]
