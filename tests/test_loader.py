from table_env_bench.data.generators import generate_episode
from table_env_bench.data.loader import load_episode_spec, save_episode_spec


def test_load_workbook_episode_spec_from_json(tmp_path) -> None:
    original = generate_episode("marker_position_rule_transfer", 1, seed=0, template_id="corner_anchor_statement")
    spec_path = tmp_path / "hierarchical_sample.json"
    save_episode_spec(original, spec_path)

    spec = load_episode_spec(spec_path)
    assert spec.family == "marker_position_rule_transfer"
    assert spec.family_display_name == "표식 위치 규칙 전이"
    assert spec.level == 1
    assert spec.locale == "ko-KR"
    assert spec.workbook.sheets[0].tab_label == "예시"
    assert spec.workbook.sheets[-1].pages[0].regions[0].role == "answer_choice"
    assert spec.answer.canonical == original.answer.canonical
    assert spec.answer.normalizer == original.answer.normalizer
