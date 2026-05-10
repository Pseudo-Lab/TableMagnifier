from table_env_bench.baselines import RandomAgent, run_episode
from table_env_bench.env.environment import WorkbookEnv


def test_click_region_logs_answer_choice_resolution_and_random_run_terminates() -> None:
    env = WorkbookEnv(family="k_vis_table_arc", level=1, seed=0, mode="dev", template_id="symbol_rule_induction")
    env.reset()
    observation, _, _, _, _ = env.step({"type": "select_sheet", "sheet": "질의"})
    choice_b = next(region for region in observation["viewport_scene"]["page"]["regions"] if region["label"] == "선택지 B")
    rect = choice_b["rect"]
    viewport = observation["viewport_scene"]["viewport"]
    page_center_x = rect["x"] + rect["width"] / 2
    page_center_y = rect["y"] + rect["height"] / 2
    click_x = ((page_center_x - viewport["x"]) / viewport["width"]) * observation["viewport_width"]
    click_y = ((page_center_y - viewport["y"]) / viewport["height"]) * observation["viewport_height"]
    _, _, _, _, info = env.step(
        {
            "type": "click_region",
            "x": click_x,
            "y": click_y,
        }
    )
    assert info["last_event"]["metadata"]["resolved_region"]["role"] == "answer_choice"
    assert info["last_event"]["metadata"]["resolved_region"]["label"] == "선택지 B"

    result = run_episode(WorkbookEnv(family="k_vis_table_arc", level=3, seed=0), RandomAgent(seed=7))
    assert result.terminated
