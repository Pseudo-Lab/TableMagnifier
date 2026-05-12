from table_env_bench.data.families import CANONICAL_FAMILY_ADAPTERS, CANONICAL_FAMILY_LABELS
from table_env_bench.data.generators import (
    benchmark_episode_records,
    benchmark_split_manifest,
    benchmark_suite_records,
    canonical_episode_catalog,
    canonical_seed_capacity,
    generate_episode,
    list_canonical_families,
    list_families,
    list_templates,
)
from table_env_bench.data.models import PageSpec, RectSpec, SheetSpec, TableCellSpec, TableElementSpec, WorkbookSpec
from table_env_bench.render.renderer import SvgWorkbookRenderer


def test_table_cell_metadata_round_trips() -> None:
    cell = TableCellSpec(
        row=2,
        col=3,
        text="",
        metadata={
            "icon": {"kind": "triangle", "anchor": "top_right", "color": "#118866"},
            "pattern": {"kind": "diagonal_stripe", "color": "#ff8800"},
            "frame": {"kind": "selection", "color": "#118866"},
        },
    )
    assert TableCellSpec.from_dict(cell.to_dict()) == cell


def test_renderer_supports_cell_icon_pattern_and_frame() -> None:
    table = TableElementSpec(
        element_id="pilot-render-table",
        rect=RectSpec(x=96, y=180, width=440, height=210),
        title="Renderer Pilot",
        n_rows=3,
        n_cols=3,
        column_widths=(120, 160, 160),
        row_heights=(42, 48, 48),
        cells=(
            TableCellSpec(row=0, col=0, text="No.", style="header"),
            TableCellSpec(row=0, col=1, text="기본", col_span=2, style="header"),
            TableCellSpec(row=1, col=0, text="A행", style="row_label", align="left"),
            TableCellSpec(
                row=1,
                col=1,
                text="",
                metadata={"pattern": {"kind": "diagonal_stripe", "color": "#ff8800", "opacity": 0.8}},
            ),
            TableCellSpec(
                row=1,
                col=2,
                text="",
                metadata={
                    "icon": {"kind": "triangle", "anchor": "top_right", "color": "#118866"},
                    "frame": {"kind": "selection", "color": "#118866"},
                },
            ),
        ),
        metadata={"excel_chrome": True, "freeze_columns": 1},
    )
    workbook = WorkbookSpec(
        workbook_id="pilot-render",
        title="Pilot Render Workbook",
        sheets=(
            SheetSpec(
                sheet_id="sheet-1",
                tab_label="시트 1",
                pages=(
                    PageSpec(
                        page_id="page-1",
                        title="렌더러 테스트",
                        width=1280,
                        height=900,
                        elements=(table,),
                        regions=(),
                    ),
                ),
            ),
        ),
    )

    svg = SvgWorkbookRenderer().render_page(workbook, sheet_index=0, page_index=0)

    assert "<polygon " in svg
    assert "#ff8800" in svg
    assert 'stroke="#118866"' in svg
    assert "Renderer Pilot" in svg


def test_registered_canonical_family_is_k_vis_table_arc() -> None:
    assert list_families() == ["k_vis_table_arc"]
    assert list_canonical_families() == ["k_vis_table_arc"]
    assert CANONICAL_FAMILY_LABELS == {"k_vis_table_arc": "K-VisTable-ARC 파일럿"}
    assert [adapter.family for adapter in CANONICAL_FAMILY_ADAPTERS] == ["k_vis_table_arc"]
    for level in (1, 2, 3):
        assert list_templates("k_vis_table_arc", level) == [
            "symbol_rule_induction",
            "merged_header_scope",
            "abbrev_doc_reference",
            "wide_table_navigation",
            "color_condition_rule_induction",
            "legend_color_exception_scope",
            "wide_table_viewport_trace",
            "merged_header_pan_scope",
            "zoom_micro_marker_exception",
        ]
        assert canonical_seed_capacity("k_vis_table_arc", level) == 72


def test_k_vis_table_arc_templates_cover_agentic_axes() -> None:
    expectations = {
        "symbol_rule_induction": ("examples", "query", "induce_symbol_rule"),
        "merged_header_scope": ("examples", "query", "resolve_header_scope"),
        "abbrev_doc_reference": ("main", "glossary", "lookup_document_rule"),
        "wide_table_navigation": ("directory", "wide", "navigate_wide_table"),
        "color_condition_rule_induction": ("examples", "query", "filter_members"),
        "legend_color_exception_scope": ("legend", "query", "classify_state"),
        "wide_table_viewport_trace": ("examples", "wide", "match_column_offset"),
        "merged_header_pan_scope": ("examples", "wide", "resolve_header_scope"),
        "zoom_micro_marker_exception": ("examples", "query", "exception_by_icon_anchor"),
    }
    for template_id, (first_sheet, support_sheet, operator) in expectations.items():
        episode = generate_episode("k_vis_table_arc", 2, seed=0, template_id=template_id)
        assert episode.family == "k_vis_table_arc"
        assert episode.metadata["benchmark_track"] == "korean_visual_table_agent_reasoning"
        assert episode.metadata["primary_operator"] == operator
        assert first_sheet in [sheet.sheet_id for sheet in episode.workbook.sheets]
        assert support_sheet in episode.metadata["required_navigation"]["required_sheet_ids"]
        assert episode.answer.normalizer == "ko_answer"


def test_k_vis_table_arc_answer_choices_are_shuffled_and_scorable() -> None:
    labels_by_template: dict[str, list[str]] = {}
    leak_phrases = ("계산 규칙과 단위를 모두 반영", "건너뛴 후보", "유사 열/행을 고른 후보")
    for template_id in list_templates("k_vis_table_arc", 1):
        labels: list[str] = []
        for seed in range(8):
            episode = generate_episode("k_vis_table_arc", 1, seed=seed, template_id=template_id)
            accepted_choice_ids = [value for value in episode.answer.accepted if value in {"A", "B", "C", "D"}]
            assert len(accepted_choice_ids) == 1
            labels.append(accepted_choice_ids[0])

            query_sheet = next(sheet for sheet in episode.workbook.sheets if sheet.sheet_id == "query")
            choice_blocks = [element for element in query_sheet.pages[0].elements if element.type == "text_block" and element.title.startswith("선택지 ")]
            assert len(choice_blocks) == 4
            visible_text = "\n".join(line for block in choice_blocks for line in (block.title, *block.lines))
            assert not any(phrase in visible_text for phrase in leak_phrases)
        labels_by_template[template_id] = labels

    assert all(len(set(labels)) > 1 for labels in labels_by_template.values())


def test_catalog_records_use_interactive_track() -> None:
    catalog = canonical_episode_catalog()
    assert catalog
    assert {record["family"] for record in catalog} == {"k_vis_table_arc"}
    assert {record["benchmark_track"] for record in catalog} == {"korean_visual_table_agent_reasoning"}

    split_manifest = benchmark_split_manifest()
    assert sorted(split_manifest) == ["dev_public", "test_holdout"]
    assert benchmark_episode_records(split="dev_public")
    suite_records = benchmark_suite_records(suite="canonical_dev")
    assert suite_records
    assert {record["family"] for record in suite_records} == {"k_vis_table_arc"}
