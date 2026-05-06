from table_env_bench.data.generators import generate_episode
from table_env_bench.render.renderer import SvgWorkbookRenderer


def test_renderer_is_deterministic_for_workbook_pages() -> None:
    spec = generate_episode("marker_position_rule_transfer", 1, seed=0, template_id="corner_anchor_statement")
    renderer = SvgWorkbookRenderer()
    first = renderer.render_page(spec.workbook, sheet_index=0, page_index=0)
    second = renderer.render_page(spec.workbook, sheet_index=0, page_index=0)
    assert first == second
    assert "예시 시트" in first
    assert "작동 예시" in first
    assert "WORKBOOK REPORT" not in first
    assert "Clinical Observer View" not in first


def test_renderer_emphasizes_dense_hierarchy_tables() -> None:
    spec = generate_episode("marker_position_rule_transfer", 2, seed=0, template_id="corner_anchor_statement")
    renderer = SvgWorkbookRenderer()
    page_svg = renderer.render_page(spec.workbook, sheet_index=0, page_index=0)

    assert "보강 예시" in page_svg or "예시 시트" in page_svg
    assert "1묶음" in page_svg
    assert "결과" in page_svg
    assert "<polygon " in page_svg
