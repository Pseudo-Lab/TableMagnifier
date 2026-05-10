from table_env_bench.env.environment import WorkbookEnv


def test_environment_sheet_transitions_for_k_vis_table_arc() -> None:
    env = WorkbookEnv(
        family="k_vis_table_arc",
        level=1,
        seed=0,
        mode="dev",
        template_id="symbol_rule_induction",
    )
    observation, info = env.reset()
    assert observation["current_sheet_name"] == "예시"
    assert observation["current_page_index"] == 0
    assert observation["viewport_scene"]["page"]["page_id"] == "examples-p1"
    assert observation["viewport_image_png_base64"]
    assert info["sheet_tabs"] == ["예시", "질의"]
    assert info["mode"] == "dev"
    assert info["active_sheet_id"] == "examples"
    assert info["zoom_index"] == 0
    assert info["viewbox"]["width"] > 0

    observation, reward, terminated, truncated, _ = env.step({"type": "select_sheet", "sheet": "질의"})
    assert reward == 0.0
    assert not terminated
    assert not truncated
    assert observation["current_sheet_name"] == "질의"
    assert observation["remaining_action_budget"] == env.spec.max_actions - 1


def test_agent_observation_sanitizes_full_scene_arrays() -> None:
    env = WorkbookEnv(
        family="k_vis_table_arc",
        level=1,
        seed=0,
        template_id="symbol_rule_induction",
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
    assert info["required_navigation"]["required_sheet_ids"] == ["examples", "query"]


def test_human_observation_keeps_full_scene_arrays() -> None:
    env = WorkbookEnv(
        family="k_vis_table_arc",
        level=1,
        seed=0,
        template_id="symbol_rule_induction",
        mode="human",
    )
    observation, _ = env.reset()
    page = observation["viewport_scene"]["page"]
    assert page["elements"]
    assert "regions" in page
    assert "notes" in page


def test_page_initial_view_metadata_sets_agent_viewport_on_sheet_switch() -> None:
    env = WorkbookEnv(
        family="k_vis_table_arc",
        level=3,
        seed=0,
        template_id="wide_table_navigation",
        mode="agent",
    )
    _observation, _info = env.reset()
    observation, _reward, _terminated, _truncated, info = env.step({"type": "select_sheet", "sheet": "wide"})

    viewbox = info["viewbox"]
    assert info["zoom_index"] == 2
    assert info["current_page_id"] == "wide-p1"
    assert viewbox["x"] == 0.0
    assert viewbox["width"] < 1200.0
    assert observation["viewport_scene"]["viewport"]["x"] == 0.0
