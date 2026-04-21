from table_env_bench.data.generators import generate_episode
from table_env_bench.render.renderer import SvgWorkbookRenderer
from table_env_bench.theme import TOKENS, rgba


def test_renderer_is_deterministic_for_workbook_pages() -> None:
    spec = generate_episode("report_scope_reconciliation", 1, seed=0, template_id="merged_scope_cell")
    renderer = SvgWorkbookRenderer()
    first = renderer.render_page(spec.workbook, sheet_index=0, page_index=0)
    second = renderer.render_page(spec.workbook, sheet_index=0, page_index=0)
    assert first == second
    assert "보고표 시트" in first
    assert "상반기" in first
    assert "WORKBOOK REPORT" not in first
    assert "Clinical Observer View" not in first


def test_renderer_emphasizes_dense_hierarchy_tables() -> None:
    spec = generate_episode("report_scope_reconciliation", 2, seed=0, template_id="subtotal_row_label")
    renderer = SvgWorkbookRenderer()
    page_svg = renderer.render_page(spec.workbook, sheet_index=0, page_index=0)

    assert "합계 전체" in page_svg
    assert "상반기" in page_svg
    assert "하반기" in page_svg
    assert rgba(TOKENS.primary_fixed, 0.82) in page_svg
    assert rgba(TOKENS.tertiary_fixed, 0.72) in page_svg
