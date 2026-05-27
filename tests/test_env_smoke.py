from pathlib import Path

from table_agi_bench.env.table_env import TableAGIEnv
from table_agi_bench.generators.rule_tasks import generate_rule_key_rank_task


def test_env_observation_no_raw_answer(tmp_path: Path):
    task = generate_rule_key_rank_task(seed=3)
    env = TableAGIEnv(task, run_dir=tmp_path)
    obs = env.reset().to_agent_payload()
    assert "answer" not in obs
    assert task.answer not in str(obs)
    assert Path(obs["image_path"]).exists()


def test_answer_action_terminal(tmp_path: Path):
    task = generate_rule_key_rank_task(seed=4)
    env = TableAGIEnv(task, run_dir=tmp_path)
    env.reset()
    obs = env.step({"type": "answer", "value": task.answer})
    assert obs.done
    assert env.correct is True
    assert env.action_count == 1


def test_invalid_direction_counts_as_action(tmp_path: Path):
    task = generate_rule_key_rank_task(seed=5)
    env = TableAGIEnv(task, run_dir=tmp_path)
    env.reset()
    obs = env.step({"type": "move_cursor", "direction": "diagonal", "steps": 3})
    assert env.action_count == 1
    assert obs.feedback == "invalid_direction"


def test_invalid_action_type_counts_as_action(tmp_path: Path):
    task = generate_rule_key_rank_task(seed=8)
    env = TableAGIEnv(task, run_dir=tmp_path)
    env.reset()
    obs = env.step({"type": "dance"})
    assert env.action_count == 1
    assert obs.feedback == "invalid_action_type"
    assert env.trace[-1]["action"]["value"] == {"invalid_type": "dance"}


def test_max_action_termination(tmp_path: Path):
    task = generate_rule_key_rank_task(seed=6)
    task.max_actions = 2
    env = TableAGIEnv(task, run_dir=tmp_path)
    env.reset()
    env.step({"type": "noop"})
    obs = env.step({"type": "noop"})
    assert obs.done
    assert obs.feedback == "max_actions_exceeded"
    assert env.correct is False


def test_post_terminal_trace_records_attempted_action(tmp_path: Path):
    task = generate_rule_key_rank_task(seed=7)
    env = TableAGIEnv(task, run_dir=tmp_path)
    env.reset()
    env.step({"type": "answer", "value": task.answer})
    action_count = env.action_count
    obs = env.step({"type": "move_cursor", "direction": "right", "steps": 2})
    assert obs.feedback == "already_done"
    assert env.action_count == action_count
    assert env.trace[-1]["ignored_post_terminal"] is True
    assert env.trace[-1]["action"] == {
        "type": "move_cursor",
        "direction": "right",
        "steps": 2,
        "value": None,
    }
