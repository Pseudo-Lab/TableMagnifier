from table_env_bench.env.environment import WorkbookEnv


def _to_viewport(env: WorkbookEnv, info: dict, page_x: float, page_y: float) -> tuple[float, float]:
    viewbox = info["debug"]["viewbox"]
    x = ((page_x - viewbox["x"]) / viewbox["width"]) * env.renderer.config.viewport_width
    y = ((page_y - viewbox["y"]) / viewbox["height"]) * env.renderer.config.viewport_height
    return x, y


def test_environment_sheet_and_note_click_transitions() -> None:
    env = WorkbookEnv(
        family="report_scope_reconciliation",
        level=2,
        seed=0,
        mode="dev",
        template_id="evalhard_l2_base",
    )
    observation, info = env.reset()
    assert observation["current_sheet_name"] == "개요"
    assert observation["current_page_index"] == 0
    assert observation["page_count_in_sheet"] == 1
    assert observation["viewport_scene"]["page"]["page_id"] == "overview-p1"
    assert observation["viewport_image_png_base64"]
    assert info["sheet_tabs"] == ["개요", "메모", "질의"]
    assert info["mode"] == "dev"
    assert info["active_sheet_id"] == "overview"
    assert info["current_page_id"] == "overview-p1"
    assert info["zoom_index"] == 0
    assert info["viewbox"]["width"] > 0

    observation, reward, terminated, truncated, _ = env.step({"type": "select_sheet", "sheet": "메모"})
    assert reward == 0.0
    assert not terminated
    assert not truncated
    assert observation["current_sheet_name"] == "메모"
    assert observation["remaining_action_budget"] == env.spec.max_actions - 1

    env = WorkbookEnv(
        family="report_scope_reconciliation",
        level=2,
        seed=0,
        mode="dev",
        template_id="evalhard_l2_base",
    )
    _, info = env.reset()
    env.step({"type": "select_sheet", "sheet": "메모"})
    click_x, click_y = _to_viewport(env, info, page_x=180, page_y=260)
    observation, _, _, _, info = env.step({"type": "click_region", "x": click_x, "y": click_y})
    assert info["last_event"]["metadata"]["opened_note"] == "scope-note"
    assert info["last_event"]["metadata"]["resolved_region"]["label"] == "범위 메모"
    assert "들여쓰기된 팀 행" in observation["viewport_svg"]


def test_agent_observation_sanitizes_full_scene_arrays() -> None:
    env = WorkbookEnv(
        family="report_scope_reconciliation",
        level=1,
        seed=0,
        template_id="merged_scope_cell",
        mode="agent",
    )
    observation, info = env.reset()
    page = observation["viewport_scene"]["page"]
    assert "elements" not in page
    assert "regions" not in page
    assert "notes" not in page
    assert observation["viewport_svg"]
    assert observation["viewport_image_png_base64"]
    assert info["active_sheet_id"] == "overview"
    assert info["current_page_id"] == "overview-p1"
    assert info["zoom_index"] == 0
    assert info["required_navigation"]["required_sheet_ids"] == ["overview", "query"]


def test_human_observation_keeps_full_scene_arrays() -> None:
    env = WorkbookEnv(
        family="report_scope_reconciliation",
        level=1,
        seed=0,
        template_id="merged_scope_cell",
        mode="human",
    )
    observation, _ = env.reset()
    page = observation["viewport_scene"]["page"]
    assert page["elements"]
    assert page["regions"]
    assert "notes" in page
