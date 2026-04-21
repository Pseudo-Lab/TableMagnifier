from table_env_bench.data.families import list_manifests
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

_BANNED_TUTORIAL_COPY = ("관찰 포인트", "판단 기준", "예시와 같은 규칙")


def _collect_visible_copy(spec) -> str:
    chunks: list[str] = [spec.question, spec.workbook.title]
    for sheet in spec.workbook.sheets:
        chunks.append(sheet.tab_label)
        for page in sheet.pages:
            chunks.append(page.title)
            for note in page.notes:
                chunks.extend((note.title, note.text))
            for element in page.elements:
                if isinstance(element, TableElementSpec):
                    chunks.append(element.title)
                    chunks.extend(cell.text for cell in element.cells if cell.text)
                    subtitle = element.metadata.get("subtitle")
                    if subtitle:
                        chunks.append(str(subtitle))
                else:
                    chunks.append(getattr(element, "title", ""))
                    chunks.extend(getattr(element, "lines", ()))
                    metadata = getattr(element, "metadata", {})
                    subtitle = metadata.get("subtitle")
                    if subtitle:
                        chunks.append(str(subtitle))
    return "\n".join(chunk for chunk in chunks if chunk)


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


def test_registered_canonical_families_match_expected_registry() -> None:
    expected = sorted(
        [
            "inventory_exception_disambiguation",
            "channel_policy_transfer",
            "report_scope_reconciliation",
        ]
    )
    assert list_families() == expected
    assert list_canonical_families() == expected

    for level in (1, 2, 3):
        assert len(list_templates("inventory_exception_disambiguation", level)) == 1
        assert canonical_seed_capacity("inventory_exception_disambiguation", level) == 8

    for level in (1, 2, 3):
        assert len(list_templates("channel_policy_transfer", level)) == 1
        assert canonical_seed_capacity("channel_policy_transfer", level) == 8

    for level in (1, 2, 3):
        assert len(list_templates("report_scope_reconciliation", level)) == 3
        assert canonical_seed_capacity("report_scope_reconciliation", level) == 24


def test_canonical_catalog_and_split_manifest_match_registry_quota() -> None:
    split_manifest = benchmark_split_manifest()
    assert len(split_manifest["dev_public"]) == 12
    assert len(split_manifest["test_holdout"]) == 3

    all_records = benchmark_episode_records()
    dev_records = benchmark_episode_records(split="dev_public")
    holdout_records = benchmark_episode_records(split="test_holdout")
    assert len(all_records) == 120
    assert len(dev_records) == 96
    assert len(holdout_records) == 24
    assert len({record["episode_id"] for record in all_records}) == 120


def test_hierarchical_family_generates_renderable_level_three_episode() -> None:
    spec = generate_episode("report_scope_reconciliation", 3, seed=23)
    assert spec.metadata["track"] == "canonical_real_tableqa"
    assert spec.metadata["benchmark_track"] == "canonical_real_tableqa"
    assert spec.metadata["template_id"] in set(list_templates("report_scope_reconciliation", 3))
    assert spec.metadata["answer_form"] in {"cell_choice", "statement_choice", "row_label_choice"}
    svg = SvgWorkbookRenderer().render_page(spec.workbook, sheet_index=0, page_index=0)
    assert "<svg " in svg


def test_hierarchical_family_uses_dense_grouped_tables_and_level_progression() -> None:
    l1 = generate_episode("report_scope_reconciliation", 1, seed=0, template_id="merged_scope_cell")
    l2 = generate_episode("report_scope_reconciliation", 2, seed=0, template_id="subtotal_row_label")

    l1_overview = next(element for element in l1.workbook.sheets[0].pages[0].elements if isinstance(element, TableElementSpec))
    l2_overview = next(element for element in l2.workbook.sheets[0].pages[0].elements if isinstance(element, TableElementSpec))

    assert l1_overview.n_cols == 7
    assert l1_overview.n_rows == 18
    assert l2_overview.n_cols == 7
    assert l2_overview.n_rows == 18

    l1_team_labels = [cell.text.strip() for cell in l1_overview.cells if cell.text.strip() in {"1팀", "2팀", "3팀"}]
    assert l1_team_labels.count("1팀") == 3
    assert l1_team_labels.count("2팀") == 3
    assert l1_team_labels.count("3팀") == 3

    assert [sheet.sheet_id for sheet in l1.workbook.sheets] == ["overview", "query"]
    assert [sheet.sheet_id for sheet in l2.workbook.sheets] == ["overview", "notes", "query"]
    assert any(cell.text == "합계 전체" for cell in l2_overview.cells)


def test_channel_policy_transfer_family_uses_examples_and_support_surface_progression() -> None:
    l1 = generate_episode("channel_policy_transfer", 1, seed=0, template_id="icon_scope_cell")
    l2 = generate_episode("channel_policy_transfer", 2, seed=0, template_id="icon_scope_cell")
    l3 = generate_episode("channel_policy_transfer", 3, seed=0, template_id="icon_scope_cell")

    assert [sheet.sheet_id for sheet in l1.workbook.sheets] == ["examples", "query"]
    assert [page.page_id for page in l1.workbook.sheets[0].pages] == ["examples-p1"]

    assert [sheet.sheet_id for sheet in l2.workbook.sheets] == ["examples", "query"]
    assert [page.page_id for page in l2.workbook.sheets[0].pages] == ["examples-p1", "examples-p2"]

    assert [sheet.sheet_id for sheet in l3.workbook.sheets] == ["examples", "appendix", "query"]
    assert [page.page_id for page in l3.workbook.sheets[0].pages] == ["examples-p1", "examples-p2"]
    assert l3.workbook.sheets[1].pages[0].notes
    assert "must_open_note" in l3.metadata["required_actions"]


def test_inventory_exception_disambiguation_family_uses_exception_and_note_progression() -> None:
    l1 = generate_episode("inventory_exception_disambiguation", 1, seed=0, template_id="pattern_vs_icon_statement")
    l2 = generate_episode("inventory_exception_disambiguation", 2, seed=0, template_id="pattern_vs_icon_statement")
    l3 = generate_episode("inventory_exception_disambiguation", 3, seed=0, template_id="pattern_vs_icon_statement")

    assert [sheet.sheet_id for sheet in l1.workbook.sheets] == ["examples", "exception", "query"]
    assert [page.page_id for page in l1.workbook.sheets[1].pages] == ["exception-p1"]
    assert "must_visit_exception" in l1.metadata["required_actions"]
    assert "must_open_note" not in l1.metadata["required_actions"]
    assert "no_exception" in l1.metadata["shortcut_probes"]
    assert "no_exception_note" not in l1.metadata["shortcut_probes"]

    assert [page.page_id for page in l2.workbook.sheets[1].pages] == ["exception-p1", "exception-p2"]
    assert l2.workbook.sheets[1].pages[1].notes
    assert "must_open_note" in l2.metadata["required_actions"]
    assert "no_exception" in l2.metadata["shortcut_probes"]
    assert "no_exception_note" in l2.metadata["shortcut_probes"]
    assert any(
        region.role == "note_marker" and region.linked_note_id == "scope-note"
        for region in l2.workbook.sheets[1].pages[1].regions
    )

    assert [page.page_id for page in l3.workbook.sheets[1].pages] == ["exception-p1", "exception-p2"]
    assert "no_exception_note" in l3.metadata["shortcut_probes"]
    assert any(
        region.role == "note_marker" and region.linked_note_id == "scope-note"
        for region in l3.workbook.sheets[1].pages[1].regions
    )
    assert any(page.title == "선택 시트" for page in l3.workbook.sheets[2].pages)
    assert l3.answer.canonical == "C"


def test_inventory_exception_disambiguation_reserves_space_for_table_headings() -> None:
    heading_offset = 44
    minimum_gap = 20

    l1 = generate_episode("inventory_exception_disambiguation", 1, seed=0, template_id="pattern_vs_icon_statement")
    example_page = l1.workbook.sheets[0].pages[0]
    example_tables = {element.element_id: element for element in example_page.elements if isinstance(element, TableElementSpec)}
    hint_table = example_tables["counter-l1-example-hint"]
    upper_examples_bottom = max(
        example_tables["counter-l1-example-1"].rect.y + example_tables["counter-l1-example-1"].rect.height,
        example_tables["counter-l1-example-2"].rect.y + example_tables["counter-l1-example-2"].rect.height,
    )
    assert hint_table.rect.y - heading_offset >= upper_examples_bottom + minimum_gap

    for level in (1, 2, 3):
        episode = generate_episode("inventory_exception_disambiguation", level, seed=0, template_id="pattern_vs_icon_statement")
        query_page = episode.workbook.sheets[2].pages[0]
        query_tables = [element for element in query_page.elements if isinstance(element, TableElementSpec)]
        main_query_table = next(element for element in query_tables if element.element_id.endswith("-query"))
        choice_tables = [element for element in query_tables if element.element_id.startswith(f"counter-l{level}-choice-")]

        assert len(choice_tables) == 4
        for choice_table in choice_tables:
            assert choice_table.rect.y - heading_offset >= main_query_table.rect.y + main_query_table.rect.height + minimum_gap
        sorted_choice_tables = sorted(choice_tables, key=lambda element: (element.rect.y, element.rect.x))
        first_row = sorted_choice_tables[:2]
        second_row = sorted_choice_tables[2:]
        assert len(first_row) == 2
        assert len(second_row) == 2
        first_row_bottom = max(element.rect.y + element.rect.height for element in first_row)
        for lower_table in second_row:
            assert lower_table.rect.y - heading_offset >= first_row_bottom + minimum_gap


def test_canonical_manifests_include_quality_contract_metadata() -> None:
    expected_ranges = {1: (2, 4), 2: (3, 4), 3: (4, 5)}

    for level in (1, 2, 3):
        for family in ("inventory_exception_disambiguation", "report_scope_reconciliation"):
            for manifest in list_manifests(family, level):
                assert manifest.primary_operator in manifest.operator_tags
                if manifest.support_operator is not None:
                    assert manifest.support_operator in manifest.operator_tags

                assert manifest.required_visual_cues
                assert set(manifest.required_visual_cues).issubset(set(manifest.cue_tags))
                assert manifest.level_rationale
                assert manifest.text_only_failure_modes
                assert manifest.distractor_failure_modes
                assert manifest.required_actions
                assert manifest.required_evidence
                assert manifest.task_archetype in {"review_verification", "exception_audit", "scope_reconciliation"}
                assert manifest.scenario_context
                assert manifest.benchmark_track == "canonical_real_tableqa"
                assert manifest.reasoning_archetype in {"induce_apply", "compose_apply", "disambiguate_apply"}
                assert manifest.abstraction_tier == "abstract_worksheet"
                assert manifest.support_surface_policy == "optional"
                assert manifest.qa_dependency == "hybrid_induction_tableqa"
                assert manifest.generalization_group

                min_steps, max_steps = manifest.expected_reasoning_steps
                expected_min, expected_max = expected_ranges[level]
                assert expected_min <= min_steps <= max_steps <= expected_max
                assert manifest.expected_min_steps == min_steps

                assert "query" in manifest.required_sheet_ids
                assert any(
                    tag in manifest.cue_tags
                    for tag in ("merged_header_scope", "subtotal_block", "indentation_depth", "pattern_marker", "icon_anchor")
                )


def test_canonical_catalog_records_propagate_quality_metadata() -> None:
    catalog = canonical_episode_catalog()
    assert catalog
    sample = catalog[0]
    assert sample["family"] in {
        "inventory_exception_disambiguation",
        "channel_policy_transfer",
        "report_scope_reconciliation",
    }
    assert "primary_operator" in sample
    assert "required_visual_cues" in sample
    assert "task_archetype" in sample
    assert "scenario_context" in sample
    assert sample["track"] == "canonical_real_tableqa"
    assert sample["benchmark_track"] == "canonical_real_tableqa"
    assert sample["reasoning_archetype"] in {"induce_apply", "compose_apply", "disambiguate_apply"}
    assert sample["abstraction_tier"] == "abstract_worksheet"
    assert sample["generalization_group"]
    assert "required_actions" in sample
    assert "required_evidence" in sample
    assert "expected_reasoning_steps" in sample

    benchmark_records = benchmark_episode_records(split="dev_public")
    assert benchmark_records
    benchmark_sample = benchmark_records[0]
    assert "primary_operator" in benchmark_sample
    assert "support_operator" in benchmark_sample
    assert "required_visual_cues" in benchmark_sample
    assert "task_archetype" in benchmark_sample
    assert "scenario_context" in benchmark_sample
    assert benchmark_sample["benchmark_track"] == "canonical_real_tableqa"
    assert benchmark_sample["generalization_group"]
    assert "level_rationale" in benchmark_sample

    suite_records = benchmark_suite_records(suite="eval_hard_dev")
    assert suite_records
    suite_sample = suite_records[0]
    assert suite_sample["family"] in {"channel_policy_transfer", "report_scope_reconciliation"}
    assert "primary_operator" in suite_sample
    assert "required_visual_cues" in suite_sample
    assert "task_archetype" in suite_sample
    assert "scenario_context" in suite_sample
    assert suite_sample["benchmark_track"] == "canonical_real_tableqa"
    assert "required_actions" in suite_sample
    assert "expected_reasoning_steps" in suite_sample


def test_canonical_families_avoid_overt_tutorial_scaffolding_copy() -> None:
    for family in list_canonical_families():
        for level in (1, 2, 3):
            for template_id in list_templates(family, level):
                spec = generate_episode(family, level, seed=0, template_id=template_id)
                visible_copy = _collect_visible_copy(spec)
                for banned in _BANNED_TUTORIAL_COPY:
                    assert banned not in visible_copy
