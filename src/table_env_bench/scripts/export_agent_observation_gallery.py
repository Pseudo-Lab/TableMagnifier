"""Export agent-mode observation images for benchmark review."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
from typing import Any

from table_env_bench.data.generators import benchmark_episode_records, benchmark_suite_manifest, generate_episode
from table_env_bench.env.environment import TableEnv
from table_env_bench.theme import preview_gallery_css


def _safe_name(value: object) -> str:
    return "".join(char if char.isalnum() or char in "._-" else "_" for char in str(value))


def _episode_refs_from_suite(suite: str) -> list[dict[str, Any]]:
    manifest = benchmark_suite_manifest()
    if suite not in manifest:
        known = ", ".join(sorted(manifest))
        raise ValueError(f"Unknown benchmark suite: {suite}. Known suites: {known}")

    refs: list[dict[str, Any]] = []
    for template in manifest[suite]:
        if "seed_slots" not in template:
            continue
        for seed in template["seed_slots"]:
            refs.append(
                {
                    "family": template["family"],
                    "level": int(template["level"]),
                    "template_id": template["template_id"],
                    "seed": int(seed),
                }
            )
    return refs


def _episode_refs_from_benchmark_records() -> list[dict[str, Any]]:
    refs = []
    seen = set()
    for record in benchmark_episode_records():
        key = (record["family"], int(record["level"]), record.get("template_id"), int(record["seed"]))
        if key in seen:
            continue
        seen.add(key)
        refs.append(
            {
                "family": record["family"],
                "level": int(record["level"]),
                "template_id": record.get("template_id"),
                "seed": int(record["seed"]),
            }
        )
    return refs


def _episode_refs_from_filters(
    *,
    family: str,
    levels: list[int],
    seeds: list[int],
    template_id: str | None,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for level in levels:
        for seed in seeds:
            refs.append({"family": family, "level": level, "template_id": template_id, "seed": seed})
    return refs


def _capture_current_observation(
    *,
    output_dir: Path,
    records: list[dict[str, Any]],
    ref: dict[str, Any],
    observation: dict[str, Any],
    info: dict[str, Any],
    surface_index: int,
) -> None:
    family = str(info["family"])
    level = int(info["level"])
    seed = int(info["seed"])
    template_id = str(info.get("template_id") or ref.get("template_id") or "default")
    sheet_index = int(observation["current_sheet_index"])
    page_index = int(observation["current_page_index"])
    sheet_name = str(observation["current_sheet_name"])
    scene = observation["viewport_scene"]
    page = scene.get("page", {}) if isinstance(scene, dict) else {}
    sheet_id = str(page.get("sheet_id") or sheet_name)
    page_id = str(page.get("page_id") or f"page-{page_index + 1}")
    surface_id = "__".join(
        [
            _safe_name(family),
            f"l{level}",
            _safe_name(template_id),
            f"s{seed}",
            _safe_name(sheet_id),
            _safe_name(page_id),
            f"v{surface_index}",
        ]
    )
    png_name = f"{surface_id}.png"
    json_name = f"{surface_id}.observation.json"
    png_bytes = base64.b64decode(str(observation["viewport_image_png_base64"]))
    (output_dir / png_name).write_bytes(png_bytes)
    (output_dir / json_name).write_text(
        json.dumps(
            {
                "info": info,
                "observation": {
                    key: value
                    for key, value in observation.items()
                    if key not in {"viewport_image_png_base64", "viewport_svg"}
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    records.append(
        {
            "surface_id": surface_id,
            "family": family,
            "level": level,
            "template_id": template_id,
            "seed": seed,
            "episode_id": info.get("episode_id"),
            "sheet": sheet_name,
            "sheet_id": sheet_id,
            "sheet_index": sheet_index,
            "page_id": page_id,
            "page_index": page_index,
            "question": observation.get("question"),
            "png": png_name,
            "observation": json_name,
        }
    )


def export_agent_observation_gallery(
    out_dir: str | Path,
    *,
    suite: str | None = "canonical_dev",
    all_benchmark_records: bool = False,
    family: str | None = None,
    levels: list[int] | None = None,
    seeds: list[int] | None = None,
    template_id: str | None = None,
) -> dict[str, object]:
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if all_benchmark_records:
        refs = _episode_refs_from_benchmark_records()
    elif family:
        refs = _episode_refs_from_filters(
            family=family,
            levels=levels or [1],
            seeds=seeds or [0],
            template_id=template_id,
        )
    else:
        refs = _episode_refs_from_suite(suite or "canonical_dev")

    records: list[dict[str, Any]] = []
    for ref in refs:
        spec = generate_episode(
            str(ref["family"]),
            int(ref["level"]),
            int(ref["seed"]),
            template_id=str(ref["template_id"]) if ref.get("template_id") else None,
        )
        surface_index = 0
        for sheet_index, sheet in enumerate(spec.workbook.sheets):
            env = TableEnv(episode_spec=spec, mode="agent")
            observation, info = env.reset()
            if sheet_index != 0:
                observation, _reward, _terminated, _truncated, info = env.step(
                    {"type": "select_sheet", "sheet": sheet.sheet_id}
                )
            for page_index, _page in enumerate(sheet.pages):
                if page_index > 0:
                    observation, _reward, _terminated, _truncated, info = env.step({"type": "next_page"})
                _capture_current_observation(
                    output_dir=output_dir,
                    records=records,
                    ref=ref,
                    observation=observation,
                    info=info,
                    surface_index=surface_index,
                )
                surface_index += 1

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "mode": "agent_observation",
                "suite": None if all_benchmark_records else suite,
                "all_benchmark_records": all_benchmark_records,
                "surfaces": records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    index_path = output_dir / "index.html"
    index_path.write_text(_index_html(records), encoding="utf-8")
    review_path = output_dir / "review.html"
    review_path.write_text(_review_html(records), encoding="utf-8")
    return {"output_dir": str(output_dir), "manifest": str(manifest_path), "index": str(index_path), "review": str(review_path), "count": len(records)}


def _index_html(records: list[dict[str, Any]]) -> str:
    cards = []
    for record in records:
        cards.append(
            f"""
            <article class="preview-card">
              <div class="preview-meta">
                <p>{record['family']} · L{record['level']} · {record['template_id']} · seed {record['seed']}</p>
                <strong>{record['sheet']} / {record['page_id']}</strong>
              </div>
              <img src="{record['png']}" alt="{record['surface_id']}"/>
            </article>
            """
        )
    return f"""
    <!doctype html>
    <html lang="ko">
      <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <title>Agent Observation Gallery</title>
        <style>{preview_gallery_css()}</style>
      </head>
      <body>
        <header>
          <p>table-env-bench agent-mode observation review</p>
          <h1>Agent Observation Gallery</h1>
          <p>agent API observation.viewport_image_png_base64 기준으로 저장한 화면입니다.</p>
        </header>
        <section class="gallery-grid">
          {''.join(cards)}
        </section>
      </body>
    </html>
    """


def _review_html(records: list[dict[str, Any]]) -> str:
    records_json = json.dumps(records, ensure_ascii=False)
    options = []
    for index, record in enumerate(records):
        selected = " selected" if index == 0 else ""
        label = f"{record['family']} · L{record['level']} · {record['template_id']} · seed {record['seed']} · {record['sheet']} / {record['page_id']}"
        options.append(f'<option value="{record["surface_id"]}"{selected}>{label}</option>')
    first_surface_id = records[0]["surface_id"] if records else ""
    return f"""
    <!doctype html>
    <html lang="ko">
      <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <title>Agent Observation Review</title>
        <style>
          {preview_gallery_css()}
          body {{ padding: 20px; }}
          .review-shell {{
            display: grid;
            grid-template-columns: 360px minmax(0, 1fr);
            gap: 18px;
            max-width: 1580px;
            margin: 0 auto;
          }}
          .review-panel {{
            background: #fff;
            border: 1px solid var(--teb-ghost-border);
            border-radius: var(--teb-radius-lg);
            padding: 16px;
          }}
          select {{
            width: 100%;
            padding: 10px 12px;
            border: 1px solid var(--teb-ghost-border-strong);
            border-radius: var(--teb-radius-md);
          }}
          .surface-frame {{
            background: #fff;
            border: 1px solid var(--teb-ghost-border);
            border-radius: var(--teb-radius-lg);
            padding: 20px;
          }}
          #agent-observation {{
            display: block;
            width: 1120px;
            height: 780px;
            margin: 0 auto;
            background: #fff;
          }}
        </style>
      </head>
      <body>
        <section class="review-shell">
          <aside class="review-panel">
            <h2>Agent Observation</h2>
            <select id="surface-select">{''.join(options)}</select>
            <p id="surface-meta"></p>
          </aside>
          <main class="surface-frame">
            <img id="agent-observation" alt="agent observation"/>
          </main>
        </section>
        <script>
          const records = {records_json};
          const select = document.getElementById('surface-select');
          const image = document.getElementById('agent-observation');
          const meta = document.getElementById('surface-meta');
          function loadSurface(surfaceId) {{
            const record = records.find((item) => item.surface_id === surfaceId) || records[0];
            if (!record) return;
            image.src = record.png;
            document.body.dataset.surfaceLoaded = 'pending';
            image.onload = () => {{
              document.body.dataset.surfaceLoaded = record.surface_id;
            }};
            meta.textContent = `${{record.family}} · L${{record.level}} · ${{record.template_id}} · seed ${{record.seed}} · ${{record.sheet}} / ${{record.page_id}}`;
          }}
          const params = new URLSearchParams(window.location.search);
          const initial = params.get('surface') || '{first_surface_id}';
          if (select) {{
            select.value = initial;
            select.addEventListener('change', () => loadSurface(select.value));
          }}
          loadSurface(initial);
        </script>
      </body>
    </html>
    """


def main() -> None:
    parser = argparse.ArgumentParser(description="Export agent-mode observation PNGs for benchmark pages.")
    parser.add_argument("--out", default="artifacts/agent_observations_active")
    parser.add_argument("--suite", default="canonical_dev")
    parser.add_argument("--all-benchmark-records", action="store_true")
    parser.add_argument("--family")
    parser.add_argument("--level", action="append", type=int, dest="levels")
    parser.add_argument("--seed", action="append", type=int, dest="seeds")
    parser.add_argument("--template-id")
    args = parser.parse_args()

    result = export_agent_observation_gallery(
        args.out,
        suite=args.suite,
        all_benchmark_records=args.all_benchmark_records,
        family=args.family,
        levels=args.levels,
        seeds=args.seeds,
        template_id=args.template_id,
    )
    print(f"Wrote {result['count']} agent observation previews to {result['output_dir']}")
    print(f"index={result['index']}")
    print(f"review={result['review']}")
    print(f"manifest={result['manifest']}")


if __name__ == "__main__":
    main()
