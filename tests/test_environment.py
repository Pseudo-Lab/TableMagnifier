from table_env_bench.env.environment import WorkbookEnv


def _to_viewport(env: WorkbookEnv, info: dict, page_x: float, page_y: float) -> tuple[float, float]:
    viewbox = info["debug"]["viewbox"]
    x = ((page_x - viewbox["x"]) / viewbox["width"]) * env.renderer.config.viewport_width
    y = ((page_y - viewbox["y"]) / viewbox["height"]) * env.renderer.config.viewport_height
    return x, y


def test_environment_sheet_and_note_click_transitions() -> None:
    env = WorkbookEnv(
        family="marker_position_rule_transfer",
        level=3,
        seed=0,
        mode="dev",
        template_id="corner_anchor_statement",
    )
    observation, info = env.reset()
    assert observation["current_sheet_name"] == "예시"
    assert observation["current_page_index"] == 0
    assert observation["page_count_in_sheet"] == 2
    assert observation["viewport_scene"]["page"]["page_id"] == "examples-p1"
    assert observation["viewport_image_png_base64"]
    assert info["sheet_tabs"] == ["예시", "범례", "반례", "질의"]
    assert info["mode"] == "dev"
    assert info["active_sheet_id"] == "examples"
    assert info["current_page_id"] == "examples-p1"
    assert info["zoom_index"] == 0
    assert info["viewbox"]["width"] > 0

    observation, reward, terminated, truncated, _ = env.step({"type": "select_sheet", "sheet": "반례"})
    assert reward == 0.0
    assert not terminated
    assert not truncated
    assert observation["current_sheet_name"] == "반례"
    assert observation["remaining_action_budget"] == env.spec.max_actions - 1

    env = WorkbookEnv(
        family="marker_position_rule_transfer",
        level=3,
        seed=0,
        mode="dev",
        template_id="corner_anchor_statement",
    )
    _, info = env.reset()
    env.step({"type": "select_sheet", "sheet": "반례"})
    _, _, _, _, info = env.step({"type": "next_page"})
    click_x, click_y = _to_viewport(env, info, page_x=160, page_y=204)
    observation, _, _, _, info = env.step({"type": "click_region", "x": click_x, "y": click_y})
    assert info["last_event"]["metadata"]["opened_note"] == "anchor-scope-note"
    assert info["last_event"]["metadata"]["resolved_region"]["label"] == "적용 범위 메모"
    assert "질의 표에서는 1묶음 행만" in observation["viewport_svg"]


def test_agent_observation_sanitizes_full_scene_arrays() -> None:
    env = WorkbookEnv(
        family="marker_position_rule_transfer",
        level=1,
        seed=0,
        template_id="corner_anchor_statement",
        mode="agent",
    )
    observation, info = env.reset()
    page = observation["viewport_scene"]["page"]
    assert "elements" not in page
    assert "regions" not in page
    assert "notes" not in page
    assert observation["viewport_svg"]
    assert observation["viewport_image_png_base64"]
    assert info["active_sheet_id"] == "examples"
    assert info["current_page_id"] == "examples-p1"
    assert info["zoom_index"] == 0
    assert info["required_navigation"]["required_sheet_ids"] == ["examples", "legend", "exception", "query"]


def test_human_observation_keeps_full_scene_arrays() -> None:
    env = WorkbookEnv(
        family="marker_position_rule_transfer",
        level=1,
        seed=0,
        template_id="corner_anchor_statement",
        mode="human",
    )
    observation, _ = env.reset()
    page = observation["viewport_scene"]["page"]
    assert page["elements"]
    assert page["regions"]
    assert "notes" in page
