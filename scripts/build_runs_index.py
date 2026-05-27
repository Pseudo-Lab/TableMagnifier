from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


def _load_summary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt_float(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{float(value):.4f}"
    return "n/a"


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _task_cards(run_dir: Path, runs_root: Path, summary: dict[str, Any]) -> str:
    cards: list[str] = []
    for record in summary.get("task_results", []):
        image_dir = run_dir / str(record.get("image_dir", ""))
        first_image = image_dir / "obs_0000.png"
        trace_path = run_dir / str(record.get("public_trace_path", ""))
        image_tag = ""
        if first_image.exists():
            image_tag = (
                f'<img src="{html.escape(_rel(first_image, runs_root))}" '
                f'alt="{html.escape(str(record.get("task_id", "task")))} initial observation">'
            )

        trace_link = ""
        if trace_path.exists():
            trace_link = f'<a href="{html.escape(_rel(trace_path, runs_root))}">trace</a>'

        cards.append(
            f"""
        <article class="task-card">
          <div class="shot">{image_tag}</div>
          <div class="task-meta">
            <h3>{html.escape(str(record.get("task_id", "unknown_task")))}</h3>
            <dl>
              <div><dt>Seed</dt><dd>{html.escape(str(record.get("seed", "n/a")))}</dd></div>
              <div><dt>Correct</dt><dd>{html.escape(str(record.get("correct", "n/a")).lower())}</dd></div>
              <div><dt>Actions</dt><dd>{html.escape(str(record.get("action_count", "n/a")))}</dd></div>
              <div><dt>Efficiency</dt><dd>{_fmt_float(record.get("efficiency"))}</dd></div>
            </dl>
            {trace_link}
          </div>
        </article>
"""
        )
    return "\n".join(cards)


def build_index(runs_root: Path, out_path: Path) -> Path:
    runs_root = runs_root.resolve()
    summaries = sorted(runs_root.glob("*/summary.json"))
    sections: list[str] = []

    for summary_path in summaries:
        run_dir = summary_path.parent
        summary = _load_summary(summary_path)
        run_index = run_dir / "index.html"
        run_link = ""
        if run_index.exists():
            run_link = f'<a href="{html.escape(_rel(run_index, runs_root))}">run index</a>'

        family = summary.get("task_family") or "rule_key_rank"
        level = summary.get("level")
        level_text = "" if level is None else f" / level {level}"
        sections.append(
            f"""
    <section class="run">
      <header class="run-head">
        <div>
          <p class="eyebrow">{html.escape(str(family))}{html.escape(level_text)}</p>
          <h2>{html.escape(run_dir.name)}</h2>
        </div>
        <dl>
          <div><dt>Tasks</dt><dd>{html.escape(str(summary.get("num_tasks", 0)))}</dd></div>
          <div><dt>Accuracy</dt><dd>{_fmt_float(summary.get("accuracy"))}</dd></div>
          <div><dt>Efficiency</dt><dd>{_fmt_float(summary.get("efficiency_mean_human"))}</dd></div>
        </dl>
        <nav>
          {run_link}
          <a href="{html.escape(_rel(summary_path, runs_root))}">summary</a>
        </nav>
      </header>
      <div class="tasks">
        {_task_cards(run_dir, runs_root, summary)}
      </div>
    </section>
"""
        )

    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Table-AGI Run Gallery</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Arial, sans-serif;
      background: #f5f7fb;
      color: #18212f;
    }}
    body {{
      margin: 0;
    }}
    main {{
      width: min(1480px, calc(100% - 40px));
      margin: 0 auto;
      padding: 24px 0 40px;
    }}
    h1 {{
      margin: 0 0 6px;
      font-size: 28px;
      letter-spacing: 0;
    }}
    .intro {{
      margin: 0 0 20px;
      color: #526071;
    }}
    .run {{
      margin: 0 0 26px;
      padding: 16px;
      background: #ffffff;
      border: 1px solid #d7dee9;
      border-radius: 8px;
    }}
    .run-head {{
      display: grid;
      grid-template-columns: minmax(220px, 1fr) auto auto;
      gap: 16px;
      align-items: center;
      margin-bottom: 14px;
    }}
    .eyebrow {{
      margin: 0 0 4px;
      font-size: 12px;
      color: #667085;
      text-transform: uppercase;
    }}
    h2, h3 {{
      margin: 0;
      letter-spacing: 0;
    }}
    h2 {{
      font-size: 20px;
    }}
    h3 {{
      font-size: 14px;
    }}
    dl {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 0;
    }}
    dl div {{
      min-width: 82px;
      padding: 6px 8px;
      background: #f8fafc;
      border: 1px solid #e3e8ef;
      border-radius: 6px;
    }}
    dt {{
      font-size: 10px;
      color: #667085;
      text-transform: uppercase;
    }}
    dd {{
      margin: 2px 0 0;
      font-weight: 700;
    }}
    nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }}
    a {{
      color: #185abc;
      font-weight: 700;
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    .tasks {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 12px;
    }}
    .task-card {{
      display: grid;
      grid-template-rows: auto 1fr;
      overflow: hidden;
      background: #ffffff;
      border: 1px solid #dbe2ec;
      border-radius: 7px;
    }}
    .shot {{
      min-height: 176px;
      background: #eef2f7;
      border-bottom: 1px solid #dbe2ec;
    }}
    .shot img {{
      display: block;
      width: 100%;
      height: auto;
    }}
    .task-meta {{
      padding: 10px;
    }}
    .task-meta dl {{
      margin: 10px 0;
    }}
    @media (max-width: 860px) {{
      .run-head {{
        grid-template-columns: 1fr;
      }}
      nav {{
        justify-content: flex-start;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>Table-AGI Run Gallery</h1>
    <p class="intro">Public run summaries and initial observation images. Protected traces, answers, private metadata, and raw tables are not embedded here.</p>
    {''.join(sections)}
  </main>
</body>
</html>
"""
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(document, encoding="utf-8")
    return out_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a static gallery for generated Table-AGI runs.")
    parser.add_argument("--runs-root", type=Path, default=Path("runs"))
    parser.add_argument("--out", type=Path, default=Path("runs/index.html"))
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    path = build_index(args.runs_root, args.out)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
