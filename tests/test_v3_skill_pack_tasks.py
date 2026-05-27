import json
from pathlib import Path

from PIL import Image

from table_agi_bench.demo import run_demo
from table_agi_bench.env.table_env import TableAGIEnv
from table_agi_bench.generators import V3_TASK_FAMILIES, generate_symbol_adjusted_score_task, generate_v3_task
from table_agi_bench.generators.v3_contract import validate_v3_task
from table_agi_bench.generators.v3_contract import visible_text


TIER_RANGES = {
    "A": range(5, 13),
    "B": range(13, 26),
    "C": range(26, 61),
    "D": range(61, 10_001),
}


def _make_task(family: str, seed: int, level: int):
    if family == "symbol_adjusted_score":
        return generate_symbol_adjusted_score_task(seed=seed, level=level)
    return generate_v3_task(task_family=family, seed=seed, level=level)


def _assert_public_payload_safe(payload) -> None:
    encoded = json.dumps(payload, ensure_ascii=False)
    assert "private_metadata" not in encoded
    assert "protected/traces" not in encoded
    assert "submitted_answer" not in encoded
    assert "reference_answer" not in encoded
    assert '"table"' not in encoded


def test_recommended_v3_mvp_templates_validate_for_20_seeds_per_level():
    for family in V3_TASK_FAMILIES:
        for level in [1, 2, 3]:
            for seed in range(20):
                task = _make_task(family, seed=seed, level=level)
                validation = validate_v3_task(task)
                metadata = task.private_metadata
                action = metadata["action_contract"]

                assert validation["status"] == "pass", (family, level, seed, validation)
                assert metadata["validation"]["status"] == "pass"
                assert metadata["template_id"] == family
                assert metadata["skill_ids"]
                assert metadata["visual_extensions_used"]
                assert metadata["gold_evidence_path"]
                assert metadata["diagnostics"]["reasoning_level"] == level
                assert metadata["diagnostics"]["nav_tier"] == action["nav_tier"]
                assert action["estimated_action_floor"] in TIER_RANGES[action["nav_tier"]]
                assert action["required_evidence_cells"]
                assert action["action_model"] in {"cell_step", "viewport_step", "page_jump", "mixed"}
                assert len(metadata["shortcut_traps"]) >= metadata["minimum_trap_count"]
                assert str(task.answer) not in {
                    str(item["value"]) for item in metadata["distractor_derivations"]
                }


def test_v3_demo_runner_writes_public_index_for_each_mvp_family(tmp_path: Path):
    for family in V3_TASK_FAMILIES:
        summary = run_demo(
            seeds=[7],
            run_dir=tmp_path / family,
            run_id=family,
            task_family=family,
            level=3,
        )
        run_dir = tmp_path / family

        assert summary["task_family"] == family
        assert summary["level"] == 3
        assert summary["num_tasks"] == 1
        assert (run_dir / "index.html").exists()
        _assert_public_payload_safe(summary)
        _assert_public_payload_safe((run_dir / "index.html").read_text(encoding="utf-8"))

        record = summary["task_results"][0]
        public_trace = json.loads((run_dir / record["public_trace_path"]).read_text(encoding="utf-8"))
        _assert_public_payload_safe(public_trace)
        assert list((run_dir / record["image_dir"]).glob("obs_*.png"))


def test_v3_renderer_draws_visual_extensions_without_icon_id_leakage(tmp_path: Path):
    icon_task = generate_v3_task(task_family="cell_icon_legend_count", seed=7, level=3)
    media_items = icon_task.private_metadata["cell_media"]
    text = visible_text(icon_task.table)
    for item in media_items:
        assert item["icon_id"] not in text

    page_task = generate_v3_task(task_family="multipage_index_rule_lookup", seed=7, level=3)
    env = TableAGIEnv(page_task, run_dir=tmp_path / "page_render")
    obs = env.reset()
    image = Image.open(obs.image_path)
    assert image.size == (620, 390)
    assert len(image.convert("RGB").getcolors(maxcolors=1_000_000)) > 10
