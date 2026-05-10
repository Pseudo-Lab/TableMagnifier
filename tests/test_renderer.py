from table_env_bench.data.generators import generate_episode
from table_env_bench.render.renderer import SvgWorkbookRenderer


def test_renderer_is_deterministic_for_workbook_pages() -> None:
    spec = generate_episode("k_vis_table_arc", 1, seed=0, template_id="symbol_rule_induction")
    renderer = SvgWorkbookRenderer()
    first = renderer.render_page(spec.workbook, sheet_index=0, page_index=0)
    second = renderer.render_page(spec.workbook, sheet_index=0, page_index=0)
    assert first == second
    assert "완성 행에서 기호 규칙 찾기" in first
    assert "★" in first
    assert "WORKBOOK REPORT" not in first
    assert "Clinical Observer View" not in first


def test_renderer_emphasizes_dense_hierarchy_tables() -> None:
    spec = generate_episode("k_vis_table_arc", 2, seed=0, template_id="merged_header_scope")
    renderer = SvgWorkbookRenderer()
    page_svg = renderer.render_page(spec.workbook, sheet_index=0, page_index=0)

    assert "권역·채널 병합 헤더" in page_svg
    assert "2025 상반기" in page_svg
    assert "반품률" in page_svg
