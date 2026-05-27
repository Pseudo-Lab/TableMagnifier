import json
from pathlib import Path

from table_agi_bench.demo import run_demo
from table_agi_bench.generators.rule_tasks import (
    generate_symbol_adjusted_score_task,
    validate_symbol_adjusted_score_task,
)


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_symbol_adjusted_score_is_deterministic():
    first = generate_symbol_adjusted_score_task(seed=11, level=2).to_private_dict()
    second = generate_symbol_adjusted_score_task(seed=11, level=2).to_private_dict()
    assert first == second


def test_symbol_adjusted_score_validation_across_levels():
    for level in [1, 2, 3]:
        for seed in range(20):
            task = generate_symbol_adjusted_score_task(seed=seed, level=level)
            validation = validate_symbol_adjusted_score_task(task)
            metadata = task.private_metadata

            assert validation["status"] == "pass"
            assert metadata["validation"]["status"] == "pass"
            assert metadata["skill_plan"]["primary_template_id"] == "symbol_adjusted_score"
            assert metadata["skill_plan"]["selected_skill_ids"] == ["symbolic_cells"]
            assert metadata["shortcut_traps"] == [
                item["trap_id"] for item in metadata["distractor_derivations"]
            ]
            assert str(task.answer) not in {
                str(item["value"]) for item in metadata["distractor_derivations"]
            }


def test_symbol_adjusted_score_public_artifacts_do_not_expose_private_data(tmp_path: Path):
    summary = run_demo(
        seeds=[4, 5],
        run_dir=tmp_path / "symbol_demo",
        run_id="symbol_demo",
        task_family="symbol_adjusted_score",
        level=3,
    )
    run_dir = tmp_path / "symbol_demo"

    assert summary["num_tasks"] == 2
    assert summary["task_family"] == "symbol_adjusted_score"
    assert summary["level"] == 3
    assert (run_dir / "index.html").exists()

    public_text = (run_dir / "summary.json").read_text(encoding="utf-8")
    public_text += (run_dir / "index.html").read_text(encoding="utf-8")
    assert "private_metadata" not in public_text
    assert "protected/traces" not in public_text
    assert '"table"' not in public_text

    manifest = _load_json(run_dir / "protected" / "manifest.json")
    assert len(manifest["protected_artifacts"]) == 2

    for record in summary["task_results"]:
        public_trace = _load_json(run_dir / record["public_trace_path"])
        trace_text = json.dumps(public_trace, ensure_ascii=False)
        assert "private_metadata" not in trace_text
        assert '"table"' not in trace_text
        assert "protected/traces" not in trace_text
        answer_events = [
            event
            for event in public_trace["events"]
            if (event.get("action") or {}).get("type") == "answer"
        ]
        assert answer_events
        assert "value" not in answer_events[-1]["action"]
        assert list((run_dir / record["image_dir"]).glob("obs_*.png"))
