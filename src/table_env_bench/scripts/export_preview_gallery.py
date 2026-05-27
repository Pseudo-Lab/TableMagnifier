"""Export representative scene/PNG previews for workbook benchmark pages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from table_env_bench.data.generators import FAMILY_LABELS, generate_episode, list_families, list_instance_packs, list_instances, list_levels, load_instance
from table_env_bench.render.image_renderer import SceneImageRenderer
from table_env_bench.render.layout import make_outer_viewbox
from table_env_bench.render.renderer import RenderConfig
from table_env_bench.render.scene import build_page_scene
from table_env_bench.theme import preview_gallery_css


def export_preview_gallery(
    out_dir: str | Path,
    *,
    seed: int = 0,
    families: list[str] | None = None,
    levels: list[int] | None = None,
    template_id: str | None = None,
    pack: str | None = None,
    instance_ids: list[str] | None = None,
) -> dict[str, object]:
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    config = RenderConfig()
    image_renderer = SceneImageRenderer()
    previews: list[dict[str, object]] = []

    selected_specs: list[tuple[str | None, object]] = []
    if pack is not None or instance_ids is not None:
        default_pack = pack
        if default_pack is None:
            packs = list_instance_packs()
            if not packs:
                raise ValueError("No frozen instance packs are available.")
            default_pack = packs[0].pack_id
        selected_instance_ids = instance_ids or [instance.instance_id for instance in list_instances(default_pack)]
        selected_specs = [(instance_id, load_instance(instance_id)) for instance_id in selected_instance_ids]
    else:
        selected_families = families or list_families()
        for family in selected_families:
            family_levels = levels if levels is not None else list_levels(family)
            for level in family_levels:
                if level not in list_levels(family):
                    continue
                selected_specs.append((None, generate_episode(family, level, seed=seed, template_id=template_id)))

    for instance_id, spec in selected_specs:
        family = spec.family
        level = spec.level
        surface_prefix = instance_id or f"{family}_l{level}"
        for sheet_index, sheet in enumerate(spec.workbook.sheets):
            for page_index, page in enumerate(sheet.pages):
                stem = f"{surface_prefix}_{sheet.sheet_id}_{page.page_id}"
                scene = build_page_scene(
                    spec.workbook,
                    sheet_index=sheet_index,
                    page_index=page_index,
                    viewport=make_outer_viewbox(page, config.viewport_width / config.viewport_height),
                    config=config,
                )
                scene_path = output_dir / f"{stem}.scene.json"
                scene_path.write_text(json.dumps(scene, ensure_ascii=False, indent=2), encoding="utf-8")
                png_path = output_dir / f"{stem}.png"
                png_path.write_bytes(image_renderer.render_png_bytes(scene))
                answer_region_count = sum(1 for region in page.regions if region.role == "answer_choice")
                surface_kind = "exception" if sheet.sheet_id == "query" and answer_region_count == 0 else sheet.sheet_id
                preview_record = {
                    "surface_id": f"{surface_prefix}-{sheet.sheet_id}-{page.page_id}",
                    "family": family,
                    "family_label": FAMILY_LABELS.get(family, family),
                    "level": str(level),
                    "kind": surface_kind,
                    "sheet": sheet.tab_label,
                    "sheet_id": sheet.sheet_id,
                    "page": page.title,
                    "page_id": page.page_id,
                    "required_navigation": dict(spec.metadata.get("required_navigation", {})),
                    "png": png_path.name,
                    "scene": scene_path.name,
                }
                if instance_id is not None:
                    preview_record["instance_id"] = instance_id
                    preview_record["pack_id"] = spec.metadata.get("pack_id")
                    preview_record["instance_label"] = spec.metadata.get("instance_label")
                previews.append(preview_record)

                if page.notes:
                    note = page.notes[0]
                    overlay_stem = f"{stem}__note_{note.id}"
                    overlay_scene = build_page_scene(
                        spec.workbook,
                        sheet_index=sheet_index,
                        page_index=page_index,
                        viewport=make_outer_viewbox(page, config.viewport_width / config.viewport_height),
                        config=config,
                        overlay_note=note,
                    )
                    overlay_scene_path = output_dir / f"{overlay_stem}.scene.json"
                    overlay_scene_path.write_text(json.dumps(overlay_scene, ensure_ascii=False, indent=2), encoding="utf-8")
                    overlay_png_path = output_dir / f"{overlay_stem}.png"
                    overlay_png_path.write_bytes(image_renderer.render_png_bytes(overlay_scene))
                    overlay_record = {
                        "surface_id": f"{surface_prefix}-{sheet.sheet_id}-{page.page_id}-note-{note.id}",
                        "family": family,
                        "family_label": FAMILY_LABELS.get(family, family),
                        "level": str(level),
                        "kind": "note_overlay",
                        "sheet": sheet.tab_label,
                        "sheet_id": sheet.sheet_id,
                        "page": f"{page.title} · 메모 {note.id}",
                        "page_id": page.page_id,
                        "required_navigation": dict(spec.metadata.get("required_navigation", {})),
                        "png": overlay_png_path.name,
                        "scene": overlay_scene_path.name,
                    }
                    if instance_id is not None:
                        overlay_record["instance_id"] = instance_id
                        overlay_record["pack_id"] = spec.metadata.get("pack_id")
                        overlay_record["instance_label"] = spec.metadata.get("instance_label")
                    previews.append(overlay_record)

    manifest_path = output_dir / "manifest.json"
    manifest_payload: dict[str, object] = {"seed": seed, "previews": previews}
    if pack is not None:
        manifest_payload["pack_id"] = pack
    if instance_ids is not None:
        manifest_payload["instance_ids"] = list(instance_ids)
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    index_path = output_dir / "index.html"
    index_path.write_text(_gallery_html(previews), encoding="utf-8")
    review_path = output_dir / "review.html"
    review_path.write_text(_review_html(previews), encoding="utf-8")
    return {
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "index": str(index_path),
        "review": str(review_path),
        "count": len(previews),
    }


def _gallery_html(previews: list[dict[str, object]]) -> str:
    cards = []
    for preview in previews:
        cards.append(
            f"""
            <article class="preview-card">
              <div class="preview-meta">
                <p>{preview['family_label']} · level {preview['level']}</p>
                <strong>{preview['sheet']} / {preview['page']}</strong>
              </div>
              <img src="{preview['png']}" alt="{preview['family_label']} {preview['page']}"/>
            </article>
            """
        )
    return f"""
    <!doctype html>
    <html lang="ko">
      <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <title>table-env-bench preview gallery</title>
        <style>{preview_gallery_css()}</style>
      </head>
      <body>
        <header>
          <p>table-env-bench renderer review</p>
          <h1>Workbook Preview Gallery</h1>
          <p>scene 기반 canvas/PNG preview를 빠르게 비교하기 위한 정적 gallery입니다.</p>
        </header>
        <section class="gallery-grid">
          {''.join(cards)}
        </section>
      </body>
    </html>
    """


def _review_html(previews: list[dict[str, object]]) -> str:
    previews_json = json.dumps(previews, ensure_ascii=False)
    config = RenderConfig()
    options = []
    for index, preview in enumerate(previews):
        label = f"{preview['family_label']} · L{preview['level']} · {preview['sheet']} / {preview['page']}"
        selected = " selected" if index == 0 else ""
        options.append(f'<option value="{preview["surface_id"]}"{selected}>{label}</option>')

    first_surface_id = previews[0]["surface_id"] if previews else ""
    return f"""
    <!doctype html>
    <html lang="ko">
      <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <title>table-env-bench preview review</title>
        <style>
          {preview_gallery_css()}
          body {{
            padding: 20px;
          }}
          .review-shell {{
            display: grid;
            grid-template-columns: 340px minmax(0, 1fr);
            gap: 18px;
            max-width: 1660px;
            margin: 0 auto;
          }}
          .review-panel {{
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid var(--teb-ghost-border);
            border-radius: var(--teb-radius-lg);
            box-shadow: var(--teb-ambient-shadow);
            padding: 16px;
          }}
          .review-select {{
            width: 100%;
            padding: 10px 12px;
            border-radius: var(--teb-radius-md);
            border: 1px solid var(--teb-ghost-border-strong);
            background: #fff;
            color: var(--teb-on-surface);
          }}
          .review-toggles {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 14px;
            font-size: 13px;
            color: var(--teb-muted);
          }}
          .surface-frame {{
            background: rgba(255, 255, 255, 0.92);
            border: 1px solid var(--teb-ghost-border);
            border-radius: var(--teb-radius-lg);
            box-shadow: var(--teb-ambient-shadow);
            padding: 20px;
          }}
          .surface-frame img {{
            width: {config.viewport_width}px;
            height: {config.viewport_height}px;
            display: block;
            margin: 0 auto;
            border-radius: var(--teb-radius-md);
            background: #fff;
          }}
        </style>
      </head>
      <body>
        <section class="review-shell">
          <aside class="review-panel">
            <h2>Surface Review</h2>
            <p>PNG로 export된 workbook surface를 검수하기 위한 정적 페이지입니다.</p>
            <select id="surface-select" class="review-select">
              {''.join(options)}
            </select>
            <label class="review-toggles">
              <input id="debug-toggle" type="checkbox"/>
              <span>debug overlay</span>
            </label>
          </aside>
          <main class="surface-frame">
            <img id="surface-image" width="{config.viewport_width}" height="{config.viewport_height}" alt="selected workbook surface"/>
          </main>
        </section>
        <script>
          const previews = {previews_json};
          const select = document.getElementById('surface-select');
          const debugToggle = document.getElementById('debug-toggle');
          const image = document.getElementById('surface-image');
          const byId = new Map(previews.map((preview) => [preview.surface_id, preview]));
          window.__TABLE_ENV_DEBUG__ = null;

          function currentDebugFlag() {{
            return new URLSearchParams(window.location.search).get('debug') === '1';
          }}

          function syncUrl(surfaceId, debug) {{
            const url = new URL(window.location.href);
            url.searchParams.set('surface', surfaceId);
            if (debug) {{
              url.searchParams.set('debug', '1');
            }} else {{
              url.searchParams.delete('debug');
            }}
            window.history.replaceState(null, '', url.toString());
          }}

          async function loadScene(surfaceId) {{
            const preview = byId.get(surfaceId);
            if (!preview) {{
              throw new Error(`Unknown surface: ${{surfaceId}}`);
            }}
            document.body.dataset.surfaceLoaded = 'pending';
            image.src = preview.png;
            document.body.dataset.surfaceLoaded = preview.surface_id;
          }}

          const initialParams = new URLSearchParams(window.location.search);
          const initialSurfaceId = initialParams.get('surface') || '{first_surface_id}';
          const initialDebug = currentDebugFlag();
          if (select && byId.has(initialSurfaceId)) {{
            select.value = initialSurfaceId;
          }}
          if (debugToggle) {{
            debugToggle.checked = initialDebug;
          }}

          if ('{first_surface_id}') {{
            loadScene(select?.value || '{first_surface_id}');
          }}

          select?.addEventListener('change', () => {{
            syncUrl(select.value, Boolean(debugToggle?.checked));
            loadScene(select.value);
          }});
          debugToggle?.addEventListener('change', () => {{
            const surfaceId = select?.value || '{first_surface_id}';
            syncUrl(surfaceId, debugToggle.checked);
            loadScene(surfaceId);
          }});
        </script>
      </body>
    </html>
    """


def main() -> None:
    parser = argparse.ArgumentParser(description="Export scene/PNG previews for workbook benchmark pages.")
    parser.add_argument("--out", default="artifacts/previews")
    parser.add_argument("--seed", default=0, type=int)
    parser.add_argument("--family", action="append", dest="families")
    parser.add_argument("--level", action="append", type=int, dest="levels")
    parser.add_argument("--template-id")
    parser.add_argument("--pack")
    parser.add_argument("--instance-id", action="append", dest="instance_ids")
    args = parser.parse_args()

    result = export_preview_gallery(
        args.out,
        seed=args.seed,
        families=args.families,
        levels=args.levels,
        template_id=args.template_id,
        pack=args.pack,
        instance_ids=args.instance_ids,
    )
    print(f"Wrote {result['count']} previews to {result['output_dir']}")
    print(f"index={result['index']}")
    print(f"review={result['review']}")
    print(f"manifest={result['manifest']}")


if __name__ == "__main__":
    main()
