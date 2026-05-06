from table_env_bench.data.families import CANONICAL_FAMILY_ADAPTERS, CANONICAL_FAMILY_LABELS, list_manifests
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
            "excel_viewport_sheet_navigation",
            "marker_position_rule_transfer",
        ]
    )
    assert list_families() == expected
    assert list_canonical_families() == expected

    for level in (1, 2, 3):
        assert len(list_templates("marker_position_rule_transfer", level)) == 1
        assert canonical_seed_capacity("marker_position_rule_transfer", level) == 8

    for level in (1, 2, 3):
        assert len(list_templates("excel_viewport_sheet_navigation", level)) == 1
        assert canonical_seed_capacity("excel_viewport_sheet_navigation", level) == 8


def test_canonical_family_adapters_are_the_registry_source() -> None:
    adapter_ids = sorted(adapter.family for adapter in CANONICAL_FAMILY_ADAPTERS)

    assert adapter_ids == list_canonical_families()
    assert len(adapter_ids) == len(set(adapter_ids))

    for adapter in CANONICAL_FAMILY_ADAPTERS:
        assert CANONICAL_FAMILY_LABELS[adapter.family] == adapter.label
        for level in adapter.levels:
            manifests = adapter.list_manifests(level)
            assert manifests == list_manifests(adapter.family, level)
            assert all(manifest.family == adapter.family for manifest in manifests)
            assert all(manifest.level == level for manifest in manifests)
            spec = adapter.build_episode(level, 0, template_id=manifests[0].template_id)
            assert spec.family == adapter.family
            assert spec.metadata["template_id"] == manifests[0].template_id


def test_canonical_catalog_and_split_manifest_match_registry_quota() -> None:
    split_manifest = benchmark_split_manifest()
    assert len(split_manifest["dev_public"]) == 6
    assert len(split_manifest["test_holdout"]) == 0

    all_records = benchmark_episode_records()
    dev_records = benchmark_episode_records(split="dev_public")
    holdout_records = benchmark_episode_records(split="test_holdout")
    assert len(all_records) == 48
    assert len(dev_records) == 48
    assert len(holdout_records) == 0
    assert len({record["episode_id"] for record in all_records}) == 48


def test_marker_position_rule_transfer_uses_legend_exception_and_note_progression() -> None:
    l1 = generate_episode("marker_position_rule_transfer", 1, seed=0, template_id="corner_anchor_statement")
    l2 = generate_episode("marker_position_rule_transfer", 2, seed=0, template_id="corner_anchor_statement")
    l3 = generate_episode("marker_position_rule_transfer", 3, seed=0, template_id="corner_anchor_statement")

    assert [sheet.sheet_id for sheet in l1.workbook.sheets] == ["examples", "legend", "exception", "query"]
    assert [page.page_id for page in l1.workbook.sheets[0].pages] == ["examples-p1"]
    assert [page.page_id for page in l1.workbook.sheets[1].pages] == ["legend-p1"]
    assert [page.page_id for page in l1.workbook.sheets[2].pages] == ["exception-p1"]
    assert "must_visit_legend" in l1.metadata["required_actions"]
    assert "must_visit_exception" in l1.metadata["required_actions"]
    assert "must_open_note" not in l1.metadata["required_actions"]
    assert l1.metadata["answer_form"] == "statement_choice"
    assert l1.answer.canonical == "C"
    assert [
        generate_episode("marker_position_rule_transfer", 1, seed=seed, template_id="corner_anchor_statement").answer.canonical
        for seed in range(3)
    ] == ["C", "D", "B"]

    assert [page.page_id for page in l2.workbook.sheets[0].pages] == ["examples-p1", "examples-p2"]
    assert "must_visit_examples_page2" in l2.metadata["required_actions"]
    assert "exception_skip" in l2.metadata["shortcut_probes"]

    assert [page.page_id for page in l3.workbook.sheets[2].pages] == ["exception-p1", "exception-p2"]
    assert "must_open_note" in l3.metadata["required_actions"]
    assert "note_skip" in l3.metadata["shortcut_probes"]
    assert any(
        region.role == "note_marker" and region.linked_note_id == "anchor-scope-note"
        for region in l3.workbook.sheets[2].pages[1].regions
    )
    note_support = next(element for element in l3.workbook.sheets[2].pages[1].elements if element.element_id == "marker-l3-note-support")
    assert all(cell.metadata.get("frame") is None for cell in note_support.cells)
    assert all("가람" not in cell.text and "나래" not in cell.text for cell in note_support.cells)


def test_excel_viewport_sheet_navigation_requires_pan_zoom_and_cross_sheet_reasoning() -> None:
    l1 = generate_episode("excel_viewport_sheet_navigation", 1, seed=0, template_id="wide_sheet_rule_transfer")
    l2 = generate_episode("excel_viewport_sheet_navigation", 2, seed=0, template_id="wide_sheet_rule_transfer")
    l3 = generate_episode("excel_viewport_sheet_navigation", 3, seed=0, template_id="wide_sheet_rule_transfer")

    assert [sheet.sheet_id for sheet in l1.workbook.sheets] == ["examples", "query"]
    assert [page.page_id for page in l2.workbook.sheets[0].pages] == ["examples-p1", "examples-p2"]
    assert [sheet.sheet_id for sheet in l3.workbook.sheets] == ["examples", "operators", "query"]

    required_navigation = l1.metadata["required_navigation"]
    assert required_navigation["required_viewport_states"][0]["required_action_types"] == ["zoom_in", "pan_right"]
    assert required_navigation["required_viewport_states"][0]["sheet_id"] == "query"
    assert "must_zoom" in l1.metadata["required_actions"]
    assert "must_pan" in l1.metadata["required_actions"]
    assert "initial_viewport_only" in required_navigation["forbidden_shortcuts"]
    assert l1.metadata["difficulty_tier"] == "canonical"
    assert l1.workbook.sheets[1].pages[0].width == 1280
    assert l1.workbook.sheets[1].pages[0].height == 900


def test_marker_position_rule_transfer_counterfactual_records_pair_variant() -> None:
    from table_env_bench.data.families.marker_position_rule_transfer import build_counterfactual_episode

    base = generate_episode("marker_position_rule_transfer", 1, seed=0, template_id="corner_anchor_statement")
    counterfactual = build_counterfactual_episode(1, 0)

    assert [sheet.sheet_id for sheet in base.workbook.sheets] == [sheet.sheet_id for sheet in counterfactual.workbook.sheets]
    assert base.answer.canonical == "C"
    assert counterfactual.answer.canonical == "B"
    assert base.answer.canonical != counterfactual.answer.canonical
    assert counterfactual.metadata["pair_group"] == "marker_position_rule_transfer:l1:s0"
    assert counterfactual.metadata["variant"] == "counterfactual"


def test_canonical_manifests_include_quality_contract_metadata() -> None:
    expected_ranges = {1: (2, 4), 2: (3, 5), 3: (4, 6)}

    for level in (1, 2, 3):
        for family in list_canonical_families():
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
                assert manifest.task_archetype in {"marker_position_transfer", "excel_viewport_transfer"}
                assert manifest.scenario_context
                assert manifest.benchmark_track == "canonical_real_tableqa"
                assert manifest.reasoning_archetype in {"induce_apply", "compose_apply", "disambiguate_apply"}
                assert manifest.abstraction_tier == "abstract_worksheet"
                assert manifest.support_surface_policy in {"optional", "required"}
                assert manifest.qa_dependency == "hybrid_induction_tableqa"
                assert manifest.generalization_group

                min_steps, max_steps = manifest.expected_reasoning_steps
                expected_min, expected_max = expected_ranges[level]
                assert expected_min <= min_steps <= max_steps <= expected_max
                assert manifest.expected_min_steps == min_steps

                assert "query" in manifest.required_sheet_ids
                assert any(
                    tag in manifest.cue_tags
                    for tag in ("pattern_marker", "icon_anchor_position", "viewport_window", "column_offset")
                )



def test_template_manifest_normalizes_required_navigation_and_legacy_mirrors() -> None:
    from table_env_bench.data.families.shared import TemplateManifest

    manifest = TemplateManifest(
        family="demo_family",
        level=2,
        template_id="demo_template",
        template_label="Demo",
        latent_rule="demo",
        operator_tags=("select",),
        cue_tags=("merged_header_scope",),
        answer_form="cell_choice",
        primary_operator="select",
        support_operator=None,
        required_visual_cues=("merged_header_scope",),
        required_surfaces=("examples", "legend", "exception", "query"),
        capability_axes=("navigation",),
        required_sheet_ids=("examples",),
        required_page_refs=("examples:examples-p1",),
        required_navigation={
            "required_sheet_ids": ["legend", "exception", "query"],
            "required_page_refs": ["legend:legend-p1", "exception:exception-p1", "examples:examples-p2", "query:query-p1"],
            "required_notes": [{"sheet_id": "exception", "page_id": "exception-p1", "note_id": "scope-note"}],
            "required_viewport_states": [
                {
                    "state_id": "query-zoom-pan-evidence",
                    "sheet_id": "query",
                    "page_id": "query-p1",
                    "min_zoom_index": 1,
                    "required_action_types": ["zoom_in", "pan_right"],
                    "match": "target_center_in_viewbox",
                    "target_rects": [],
                }
            ],
            "forbidden_shortcuts": ["initial_viewport_only", "no_pan_zoom", "sheet_skip"],
        },
        allowed_cue_variants=("demo",),
        distractor_policy="demo",
        level_rationale="demo",
        text_only_failure_modes=("demo",),
        distractor_failure_modes=("demo",),
        required_evidence=({"surface": "query:query-p1"},),
    )

    serialized = manifest.to_dict()
    assert serialized["required_navigation"]["required_sheet_ids"] == ["examples", "legend", "exception", "query"]
    assert serialized["required_sheet_ids"] == serialized["required_navigation"]["required_sheet_ids"]
    assert serialized["required_page_refs"] == serialized["required_navigation"]["required_page_refs"]
    assert serialized["required_actions"] == [
        "must_switch_sheet",
        "must_open_note",
        "must_visit_exception",
        "must_visit_legend",
        "must_visit_examples_page2",
        "must_zoom",
        "must_pan",
    ]


def test_canonical_catalog_records_propagate_quality_metadata() -> None:
    catalog = canonical_episode_catalog()
    assert catalog
    sample = catalog[0]
    assert sample["family"] in {"excel_viewport_sheet_navigation", "marker_position_rule_transfer"}
    assert "primary_operator" in sample
    assert "required_visual_cues" in sample
    assert "task_archetype" in sample
    assert "scenario_context" in sample
    assert sample["track"] == "canonical_real_tableqa"
    assert sample["benchmark_track"] == "canonical_real_tableqa"
    assert sample["reasoning_archetype"] in {"induce_apply", "compose_apply", "disambiguate_apply"}
    assert sample["abstraction_tier"] == "abstract_worksheet"
    assert sample["generalization_group"]
    assert "required_navigation" in sample
    assert sample["required_sheet_ids"] == sample["required_navigation"]["required_sheet_ids"]
    assert sample["required_page_refs"] == sample["required_navigation"]["required_page_refs"]
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
    assert "required_navigation" in benchmark_sample

    suite_records = benchmark_suite_records(suite="canonical_dev")
    assert suite_records
    suite_sample = suite_records[0]
    assert suite_sample["family"] in {"excel_viewport_sheet_navigation", "marker_position_rule_transfer"}
    assert "primary_operator" in suite_sample
    assert "required_visual_cues" in suite_sample
    assert "task_archetype" in suite_sample
    assert "scenario_context" in suite_sample
    assert suite_sample["benchmark_track"] == "canonical_real_tableqa"
    assert "required_navigation" in suite_sample
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
