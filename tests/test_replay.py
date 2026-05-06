import json

from table_env_bench.env.environment import WorkbookEnv
from table_env_bench.env.replay import ReplayEvent, ReplayTrace, viewport_state_matches_event, viewport_target_matches


def test_action_logging_and_replay_export(tmp_path) -> None:
    env = WorkbookEnv(family="marker_position_rule_transfer", level=3, seed=0, template_id="corner_anchor_statement")
    env.reset()
    env.step({"type": "select_sheet", "sheet": "반례"})
    env.step({"type": "next_page"})
    env.step({"type": "click_region", "x": 120, "y": 120})
    env.step({"type": "submit_answer", "text": env.spec.answer.canonical})

    replay_path = tmp_path / "replay.json"
    env.export_replay(str(replay_path))
    payload = json.loads(replay_path.read_text(encoding="utf-8"))

    assert payload["action_count"] == 4
    assert payload["unique_sheets_visited"] == 2
    assert payload["unique_pages_visited"] == 3
    assert payload["metrics"]["sheet_switch_count"] == 1
    assert payload["metrics"]["page_switch_count"] == 2
    assert payload["metrics"]["note_open_count"] == 0
    assert payload["metrics"]["answer_submit_step"] == 4
    assert payload["events"][0]["action"]["type"] == "select_sheet"
    assert payload["events"][3]["terminated"] is True


def _event(step: int, action_type: str, *, sheet_id: str = "query", page_id: str = "query-p1", zoom_index: int = 1, viewbox=None) -> ReplayEvent:
    return ReplayEvent(
        step_index=step,
        action={"type": action_type},
        before={},
        after={
            "sheet_id": sheet_id,
            "page_id": page_id,
            "zoom_index": zoom_index,
            "viewbox": viewbox or {"x": 0, "y": 0, "width": 100, "height": 100},
        },
        reward=0.0,
        terminated=False,
        truncated=False,
    )


def test_viewport_target_match_boundaries() -> None:
    viewbox = {"x": 0, "y": 0, "width": 100, "height": 100}

    assert viewport_target_matches(
        viewbox=viewbox,
        target_rect={"x": 90, "y": 20, "width": 20, "height": 20},
        match="viewbox_intersects_target",
    )
    assert not viewport_target_matches(
        viewbox=viewbox,
        target_rect={"x": 100, "y": 20, "width": 20, "height": 20},
        match="viewbox_intersects_target",
    )
    assert viewport_target_matches(
        viewbox=viewbox,
        target_rect={"x": 80, "y": 80, "width": 40, "height": 40},
        match="target_center_in_viewbox",
    )
    assert not viewport_target_matches(
        viewbox=viewbox,
        target_rect={"x": 101, "y": 80, "width": 40, "height": 40},
        match="target_center_in_viewbox",
    )


def test_viewport_state_match_requires_actions_zoom_and_all_targets() -> None:
    required = {
        "state_id": "query-zoom-pan-evidence",
        "sheet_id": "query",
        "page_id": "query-p1",
        "min_zoom_index": 1,
        "required_action_types": ["zoom_in", "pan_right"],
        "match": "target_center_in_viewbox",
        "target_rects": [
            {"target_id": "a", "rect": {"x": 40, "y": 40, "width": 10, "height": 10}},
            {"target_id": "b", "rect": {"x": 80, "y": 80, "width": 10, "height": 10}},
        ],
    }
    event_state = {
        "sheet_id": "query",
        "page_id": "query-p1",
        "zoom_index": 1,
        "viewbox": {"x": 0, "y": 0, "width": 100, "height": 100},
    }

    assert viewport_state_matches_event(required, event_state, {"zoom_in", "pan_right"})
    assert not viewport_state_matches_event({**required, "min_zoom_index": 2}, event_state, {"zoom_in", "pan_right"})
    assert not viewport_state_matches_event(required, event_state, {"zoom_in"})
    assert not viewport_state_matches_event(
        {
            **required,
            "target_rects": [
                {"target_id": "a", "rect": {"x": 40, "y": 40, "width": 10, "height": 10}},
                {"target_id": "missing", "rect": {"x": 400, "y": 400, "width": 10, "height": 10}},
            ],
        },
        event_state,
        {"zoom_in", "pan_right"},
    )


def test_replay_metrics_reports_visited_and_missing_required_viewport_states() -> None:
    trace = ReplayTrace(
        episode_id="episode",
        family="family",
        level=1,
        seed=0,
        workbook_id="workbook",
        workbook_title="Workbook",
        initial_sheet_id="examples",
        initial_page_id="examples-p1",
    )
    trace.append(_event(1, "select_sheet", zoom_index=0))
    trace.append(_event(2, "zoom_in", zoom_index=1))
    trace.append(_event(3, "pan_right", zoom_index=1, viewbox={"x": 50, "y": 0, "width": 100, "height": 100}))

    metrics = trace.metrics(
        {
            "required_navigation": {
                "required_sheet_ids": ["examples", "query"],
                "required_page_refs": ["query:query-p1"],
                "required_viewport_states": [
                    {
                        "state_id": "hit",
                        "sheet_id": "query",
                        "page_id": "query-p1",
                        "min_zoom_index": 1,
                        "required_action_types": ["zoom_in", "pan_right"],
                        "match": "target_center_in_viewbox",
                        "target_rects": [{"target_id": "target", "rect": {"x": 80, "y": 20, "width": 10, "height": 10}}],
                    },
                    {
                        "state_id": "miss",
                        "sheet_id": "query",
                        "page_id": "query-p1",
                        "min_zoom_index": 1,
                        "required_action_types": ["zoom_in", "pan_right"],
                        "match": "target_center_in_viewbox",
                        "target_rects": [{"target_id": "target", "rect": {"x": 500, "y": 20, "width": 10, "height": 10}}],
                    },
                ],
            }
        }
    )

    assert metrics["visited_viewport_states"] == ["hit"]
    assert metrics["missed_required_navigation"]["viewport_state_ids"] == ["miss"]
    assert metrics["support_surface_compliance"] is False
