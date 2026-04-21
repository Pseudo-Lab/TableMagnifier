import json

from table_env_bench.env.environment import WorkbookEnv


def test_action_logging_and_replay_export(tmp_path) -> None:
    env = WorkbookEnv(family="report_scope_reconciliation", level=2, seed=0, template_id="evalhard_l2_base")
    env.reset()
    env.step({"type": "select_sheet", "sheet": "메모"})
    env.step({"type": "click_region", "x": 500, "y": 320})
    env.step({"type": "submit_answer", "text": env.spec.answer.canonical})

    replay_path = tmp_path / "replay.json"
    env.export_replay(str(replay_path))
    payload = json.loads(replay_path.read_text(encoding="utf-8"))

    assert payload["action_count"] == 3
    assert payload["unique_sheets_visited"] == 2
    assert payload["unique_pages_visited"] == 2
    assert payload["metrics"]["sheet_switch_count"] == 1
    assert payload["metrics"]["page_switch_count"] == 1
    assert payload["metrics"]["note_open_count"] == 1
    assert payload["metrics"]["answer_submit_step"] == 3
    assert payload["events"][0]["action"]["type"] == "select_sheet"
    assert payload["events"][2]["terminated"] is True
