from __future__ import annotations

import argparse
import csv
import html
import json
from pathlib import Path
from typing import Any

from table_agi_bench.agents.dev_oracles.scripted_demo import ScriptedDemoOraclePolicy
from table_agi_bench.env.table_env import TableAGIEnv
from table_agi_bench.eval.metrics import accuracy, efficiency_score, mean
from table_agi_bench.generators.rule_tasks import (
    generate_rule_key_rank_task,
    generate_symbol_adjusted_score_task,
)
from table_agi_bench.generators.v3_tasks import V3_TASK_FAMILIES, generate_v3_task


def _relative_to(path: str | Path, root: Path) -> str:
    return Path(path).resolve().relative_to(root.resolve()).as_posix()


def _safe_action(action: dict[str, Any] | None) -> dict[str, Any] | None:
    if action is None:
        return None
    safe: dict[str, Any] = {"type": action.get("type")}
    if action.get("direction") is not None:
        safe["direction"] = action.get("direction")
    if action.get("steps") is not None:
        safe["steps"] = action.get("steps")
    return safe


def _safe_observation(observation: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    safe = dict(observation)
    if "image_path" in safe:
        safe["image_path"] = _relative_to(safe["image_path"], run_dir)
    return safe


def _public_trace(env: TableAGIEnv, run_id: str, agent_id: str, run_dir: Path) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    for event in env.trace:
        public_event: dict[str, Any] = {
            "turn": event["turn"],
            "image_path": _relative_to(event["image_path"], run_dir),
            "image_sha256": event["image_sha256"],
            "observation": _safe_observation(event["observation"], run_dir),
            "action": _safe_action(event.get("action")),
            "done": event.get("done", False),
            "feedback": event.get("feedback"),
        }
        if event.get("ignored_post_terminal"):
            public_event["ignored_post_terminal"] = True
        events.append(public_event)

    return {
        "run_id": run_id,
        "task_id": env.task.task_id,
        "agent_id": agent_id,
        "events": events,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    return path


def _write_csv(path: Path, records: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "task_id",
        "seed",
        "correct",
        "action_count",
        "efficiency",
        "public_trace_path",
        "image_dir",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow({field: record[field] for field in fields})
    return path


def _write_index_html(path: Path, summary: dict[str, Any], run_dir: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    sections: list[str] = []
    for record in summary["task_results"]:
        image_dir = run_dir / record["image_dir"]
        images = sorted(image_dir.glob("obs_*.png"))
        image_tags = "\n".join(
            (
                '<figure class="frame">'
                f'<img src="{html.escape(record["image_dir"] + "/" + image.name)}" '
                f'alt="{html.escape(record["task_id"] + " " + image.stem)}">'
                f"<figcaption>{html.escape(image.stem)}</figcaption>"
                "</figure>"
            )
            for image in images
        )
        sections.append(
            f"""
      <section class="task">
        <header>
          <h2>{html.escape(record["task_id"])}</h2>
          <dl>
            <div><dt>Seed</dt><dd>{record["seed"]}</dd></div>
            <div><dt>Correct</dt><dd>{str(record["correct"]).lower()}</dd></div>
            <div><dt>Actions</dt><dd>{record["action_count"]}</dd></div>
            <div><dt>Efficiency</dt><dd>{record["efficiency"]:.4f}</dd></div>
          </dl>
          <a href="{html.escape(record["public_trace_path"])}">public trace</a>
        </header>
        <div class="frames">
          {image_tags}
        </div>
      </section>
"""
        )

    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Table-AGI Demo Run</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Arial, sans-serif;
      background: #f4f5f7;
      color: #1f2937;
    }}
    body {{
      margin: 0;
    }}
    main {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 24px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 28px;
    }}
    .summary {{
      margin-bottom: 24px;
      color: #4b5563;
    }}
    .task {{
      margin: 0 0 28px;
      padding: 16px;
      background: #ffffff;
      border: 1px solid #d8dee8;
      border-radius: 8px;
    }}
    .task header {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px 20px;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 14px;
    }}
    h2 {{
      margin: 0;
      font-size: 18px;
    }}
    dl {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: 0;
    }}
    dl div {{
      min-width: 92px;
      padding: 6px 8px;
      background: #f8fafc;
      border: 1px solid #e5e7eb;
      border-radius: 6px;
    }}
    dt {{
      font-size: 11px;
      text-transform: uppercase;
      color: #6b7280;
    }}
    dd {{
      margin: 2px 0 0;
      font-weight: 700;
    }}
    a {{
      color: #1d4ed8;
      font-weight: 700;
    }}
    .frames {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 12px;
    }}
    .frame {{
      margin: 0;
      border: 1px solid #d8dee8;
      background: #ffffff;
      border-radius: 6px;
      overflow: hidden;
    }}
    .frame img {{
      display: block;
      width: 100%;
      height: auto;
    }}
    figcaption {{
      padding: 6px 8px;
      font-size: 12px;
      color: #4b5563;
      border-top: 1px solid #e5e7eb;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Table-AGI Demo Run</h1>
    <p class="summary">
      Run {html.escape(str(summary["run_id"]))}: {summary["num_tasks"]} tasks,
      accuracy {summary["accuracy"]:.4f}, efficiency {summary["efficiency_mean_human"]:.4f}.
      Public page: no answers, private metadata, or protected trace paths.
    </p>
    {''.join(sections)}
  </main>
</body>
</html>
"""
    path.write_text(document, encoding="utf-8")
    return path


def _generate_task(task_family: str, seed: int, level: int) -> Any:
    if task_family == "rule_key_rank":
        return generate_rule_key_rank_task(seed=seed)
    if task_family == "symbol_adjusted_score":
        return generate_symbol_adjusted_score_task(seed=seed, level=level)
    if task_family in V3_TASK_FAMILIES:
        return generate_v3_task(task_family=task_family, seed=seed, level=level)
    raise ValueError(f"unknown task family: {task_family}")


def run_demo(
    seeds: list[int],
    run_dir: str | Path,
    run_id: str = "demo",
    task_family: str = "rule_key_rank",
    level: int = 2,
) -> dict[str, Any]:
    run_dir = Path(run_dir).resolve()
    policy = ScriptedDemoOraclePolicy()
    task_results: list[dict[str, Any]] = []
    protected_records: list[dict[str, Any]] = []

    for seed in seeds:
        task = _generate_task(task_family=task_family, seed=seed, level=level)
        env = TableAGIEnv(task, run_dir=run_dir / "images", viewport_rows=12, viewport_cols=6)
        policy.run_private(task, env)

        score = efficiency_score(
            action_count=env.action_count,
            human_baseline_actions=task.human_mean_actions,
            correct=bool(env.correct),
        )

        public_trace_path = run_dir / "public_traces" / f"{task.task_id}.json"
        protected_trace_path = run_dir / "protected" / "traces" / f"{task.task_id}.json"
        protected_result_path = run_dir / "protected" / "results" / f"{task.task_id}.json"
        _write_json(
            public_trace_path,
            _public_trace(env, run_id=run_id, agent_id=policy.agent_id, run_dir=run_dir),
        )
        env.save_trace(
            protected_trace_path,
            agent_id=policy.agent_id,
            run_id=run_id,
            efficiency_score=score,
        )
        _write_json(
            protected_result_path,
            {
                "run_id": run_id,
                "task_id": task.task_id,
                "agent_id": policy.agent_id,
                "seed": seed,
                "submitted_answer": env.submitted_answer,
                "reference_answer": task.answer,
                "correct": env.correct,
                "action_count": env.action_count,
                "efficiency_score": score,
            },
        )

        image_dir = run_dir / "images" / task.task_id
        task_results.append(
            {
                "task_id": task.task_id,
                "seed": seed,
                "correct": bool(env.correct),
                "action_count": env.action_count,
                "efficiency": score,
                "public_trace_path": _relative_to(public_trace_path, run_dir),
                "image_dir": _relative_to(image_dir, run_dir),
            }
        )
        protected_records.append(
            {
                "task_id": task.task_id,
                "seed": seed,
                "protected_trace_path": _relative_to(protected_trace_path, run_dir),
                "protected_result_path": _relative_to(protected_result_path, run_dir),
            }
        )

    summary = {
        "run_id": run_id,
        "agent_id": policy.agent_id,
        "task_family": task_family,
        "level": level if task_family in V3_TASK_FAMILIES else None,
        "num_tasks": len(task_results),
        "accuracy": accuracy(record["correct"] for record in task_results),
        "efficiency_mean_human": mean(record["efficiency"] for record in task_results),
        "task_results": task_results,
    }
    manifest = {
        "run_id": run_id,
        "agent_id": policy.agent_id,
        "protected_artifacts": protected_records,
    }

    _write_json(run_dir / "summary.json", summary)
    _write_csv(run_dir / "summary.csv", task_results)
    _write_json(run_dir / "protected" / "manifest.json", manifest)
    _write_index_html(run_dir / "index.html", summary, run_dir)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Table-AGI agent-facing demo MVP.")
    parser.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3], help="Deterministic task seeds.")
    parser.add_argument("--run-dir", type=Path, default=Path("runs/demo"), help="Output directory.")
    parser.add_argument("--run-id", default="demo", help="Stable run identifier written into artifacts.")
    parser.add_argument(
        "--task-family",
        choices=["rule_key_rank", *V3_TASK_FAMILIES],
        default="rule_key_rank",
        help="Task generator family to run.",
    )
    parser.add_argument("--level", type=int, choices=[1, 2, 3], default=2, help="V3 template level.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    summary = run_demo(
        seeds=args.seeds,
        run_dir=args.run_dir,
        run_id=args.run_id,
        task_family=args.task_family,
        level=args.level,
    )
    print(
        json.dumps(
            {
                "run_id": summary["run_id"],
                "num_tasks": summary["num_tasks"],
                "accuracy": summary["accuracy"],
                "efficiency_mean_human": summary["efficiency_mean_human"],
                "index_path": str(args.run_dir / "index.html"),
                "summary_path": str(args.run_dir / "summary.json"),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
