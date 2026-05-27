import json
from pathlib import Path

from table_agi_bench.demo import run_demo
from table_agi_bench.generators.rule_tasks import generate_rule_key_rank_task


FORBIDDEN_PUBLIC_KEYS = {
    "submitted_answer",
    "answer",
    "private_metadata",
    "table",
    "protected_trace_path",
}

def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_no_forbidden_public_content(payload, answer: str):
    encoded = json.dumps(payload, ensure_ascii=False)
    assert answer not in encoded
    assert "protected/traces" not in encoded
    assert "private_metadata" not in encoded
    assert '"table"' not in encoded
    _assert_no_forbidden_public_keys(payload)


def _assert_no_forbidden_public_keys(payload):
    if isinstance(payload, dict):
        for key, value in payload.items():
            assert key not in FORBIDDEN_PUBLIC_KEYS
            _assert_no_forbidden_public_keys(value)
    elif isinstance(payload, list):
        for value in payload:
            _assert_no_forbidden_public_keys(value)


def test_demo_runner_writes_public_and_protected_artifacts(tmp_path: Path):
    summary = run_demo(seeds=[1, 2, 3], run_dir=tmp_path / "demo")
    run_dir = tmp_path / "demo"
    summary_path = run_dir / "summary.json"
    manifest_path = run_dir / "protected" / "manifest.json"

    assert summary["num_tasks"] == 3
    assert summary_path.exists()
    assert (run_dir / "summary.csv").exists()
    assert (run_dir / "index.html").exists()
    assert manifest_path.exists()

    persisted_summary = _load_json(summary_path)
    manifest = _load_json(manifest_path)
    assert len(persisted_summary["task_results"]) == 3
    assert len(manifest["protected_artifacts"]) == 3

    for record in persisted_summary["task_results"]:
        task = generate_rule_key_rank_task(seed=record["seed"])
        assert (run_dir / record["public_trace_path"]).exists()
        assert (run_dir / record["image_dir"]).exists()
        assert list((run_dir / record["image_dir"]).glob("obs_*.png"))
        assert "protected_trace_path" not in record
        _assert_no_forbidden_public_content(record, task.answer)

        public_trace = _load_json(run_dir / record["public_trace_path"])
        _assert_no_forbidden_public_content(public_trace, task.answer)
        answer_events = [
            event
            for event in public_trace["events"]
            if (event.get("action") or {}).get("type") == "answer"
        ]
        assert answer_events
        assert "value" not in answer_events[-1]["action"]

    for record in manifest["protected_artifacts"]:
        assert (run_dir / record["protected_trace_path"]).exists()
        assert (run_dir / record["protected_result_path"]).exists()

    for seed in [1, 2, 3]:
        _assert_no_forbidden_public_content(
            persisted_summary,
            generate_rule_key_rank_task(seed=seed).answer,
        )
        _assert_no_forbidden_public_content(
            (run_dir / "index.html").read_text(encoding="utf-8"),
            generate_rule_key_rank_task(seed=seed).answer,
        )


def test_demo_runner_is_deterministic_for_public_outputs(tmp_path: Path):
    run_demo(seeds=[1, 2, 3], run_dir=tmp_path / "demo_a")
    run_demo(seeds=[1, 2, 3], run_dir=tmp_path / "demo_b")

    summary_a = _load_json(tmp_path / "demo_a" / "summary.json")
    summary_b = _load_json(tmp_path / "demo_b" / "summary.json")
    assert summary_a == summary_b

    for record in summary_a["task_results"]:
        trace_a = _load_json(tmp_path / "demo_a" / record["public_trace_path"])
        trace_b = _load_json(tmp_path / "demo_b" / record["public_trace_path"])
        assert trace_a == trace_b
        hashes_a = [event["image_sha256"] for event in trace_a["events"]]
        hashes_b = [event["image_sha256"] for event in trace_b["events"]]
        assert hashes_a == hashes_b
