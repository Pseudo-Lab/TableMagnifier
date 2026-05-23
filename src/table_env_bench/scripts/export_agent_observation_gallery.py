"""Export agent-mode observation images for benchmark review."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import shutil
from typing import Any

from PIL import Image, ImageDraw

from table_env_bench.data.generators import benchmark_episode_records, benchmark_suite_manifest, generate_episode
from table_env_bench.env.environment import TableEnv
from table_env_bench.render.image_renderer import RENDER_TEXT_SIZES, TABLE_STYLE
from table_env_bench.render.layout import Rect
from table_env_bench.render.renderer import RenderConfig
from table_env_bench.render.scene import build_page_scene
from table_env_bench.theme import preview_gallery_css

EXPECTED_ALL_BENCHMARK_SURFACES = 624
REVIEW_CONTRACT_VERSION = 1
METRIC_SOURCE = "exporter_full_scene"
DEFAULT_RENDER_CONFIG = RenderConfig()
AGENT_IMAGE_SIZE = (DEFAULT_RENDER_CONFIG.viewport_width, DEFAULT_RENDER_CONFIG.viewport_height)
PROHIBITED_VISIBLE_TERMS = (
    "k_vis_table_arc",
    "symbol_rule_induction",
    "abbrev_doc_reference",
    "color_condition_rule_induction",
    "legend_color_exception_scope",
    "merged_header_scope",
    "merged_header_pan_scope",
    "wide_table_navigation",
    "wide_table_viewport_trace",
    "zoom_micro_marker_exception",
    "examples-p",
    "query-p",
    "template_id",
    "episode_id",
    "surface_id",
    "gold_answer",
    "rationale",
    "oracle",
    "debug",
    "seed",
    "distractor",
    "synthetic",
    "generated",
    "benchmark",
    "agent",
    "hidden",
    "hidden_grid_text",
    "계산 경로는 포함하지 않습니다",
    "case routing",
    "참조 경로",
    "검토 항목",
    "확인 위치",
    "필요 시",
    "Level 3",
    "규정 상태 요약",
)


def _safe_name(value: object) -> str:
    return "".join(char if char.isalnum() or char in "._-" else "_" for char in str(value))


def _clean_generated_output(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for pattern in ("*.png", "*.json", "*.observation.json", "*.html"):
        for path in output_dir.glob(pattern):
            path.unlink()
    for path in (output_dir / "contact_sheets",):
        if path.exists():
            shutil.rmtree(path)


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
    full_scene: dict[str, Any],
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
    semantic_name = f"{surface_id}.semantic.json"
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
    semantic_snapshot = _semantic_snapshot(
        surface_id=surface_id,
        scene=full_scene,
        info=info,
        observation=observation,
    )
    (output_dir / semantic_name).write_text(
        json.dumps(semantic_snapshot, ensure_ascii=False, indent=2),
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
            "semantic_snapshot": semantic_name,
            "metric_source": METRIC_SOURCE,
            "review_contract_version": REVIEW_CONTRACT_VERSION,
            "visible_text": _scene_visible_text(full_scene),
            "choice_values": _scene_choice_values(full_scene),
            "non_wide_scrollbar_tables": _scene_non_wide_scrollbar_tables(full_scene),
            "semantic_metrics": semantic_snapshot["metrics"],
        }
    )


def _map_rect(scene: dict[str, Any], rect: dict[str, Any]) -> dict[str, float]:
    viewport = scene["viewport"]
    surface = scene["surface"]
    x = (float(rect["x"]) - float(viewport["x"])) / float(viewport["width"]) * float(surface["width"])
    y = (float(rect["y"]) - float(viewport["y"])) / float(viewport["height"]) * float(surface["height"])
    width = float(rect["width"]) / float(viewport["width"]) * float(surface["width"])
    height = float(rect["height"]) / float(viewport["height"]) * float(surface["height"])
    return {"x": x, "y": y, "width": width, "height": height}


def _rect_bottom(rect: dict[str, float]) -> float:
    return float(rect["y"]) + float(rect["height"])


def _rect_right(rect: dict[str, float]) -> float:
    return float(rect["x"]) + float(rect["width"])


def _overlap_amount(a: dict[str, float], b: dict[str, float]) -> tuple[float, float]:
    overlap_x = max(0.0, min(_rect_right(a), _rect_right(b)) - max(float(a["x"]), float(b["x"])))
    overlap_y = max(0.0, min(_rect_bottom(a), _rect_bottom(b)) - max(float(a["y"]), float(b["y"])))
    return overlap_x, overlap_y


def _semantic_snapshot(
    *,
    surface_id: str,
    scene: dict[str, Any],
    info: dict[str, Any],
    observation: dict[str, Any],
) -> dict[str, Any]:
    page = scene.get("page", {}) if isinstance(scene, dict) else {}
    surface = scene.get("surface", {}) if isinstance(scene, dict) else {}
    viewport = scene.get("viewport", {}) if isinstance(scene, dict) else {}
    surface_width = float(surface.get("width", AGENT_IMAGE_SIZE[0]))
    surface_height = float(surface.get("height", AGENT_IMAGE_SIZE[1]))
    content_frame = {"x": 32.0, "y": 24.0, "width": surface_width - 64.0, "height": surface_height - 48.0}
    elements: list[dict[str, Any]] = []
    table_bottoms: list[float] = []
    content_top: float | None = None
    content_bottom: float | None = None
    for element in page.get("elements", ()):
        if not isinstance(element, dict):
            continue
        rect = element.get("rect")
        if not isinstance(rect, dict):
            continue
        mapped = _map_rect(scene, rect)
        content_top = mapped["y"] if content_top is None else min(content_top, mapped["y"])
        content_bottom = _rect_bottom(mapped) if content_bottom is None else max(content_bottom, _rect_bottom(mapped))
        element_metrics: dict[str, Any] = {
            "id": element.get("element_id"),
            "type": element.get("type"),
            "title": element.get("title"),
            "rect": mapped,
        }
        if element.get("type") == "table":
            visual_top = max(0.0, mapped["y"] - 50.0)
            content_top = visual_top if content_top is None else min(content_top, visual_top)
            table_bottoms.append(_rect_bottom(mapped))
            element_metrics["cellOverflowCount"] = 0
            element_metrics["tableBodyFontMin"] = min(int(TABLE_STYLE.get(str(cell.get("style", "body")), TABLE_STYLE["body"]).get("size", 0)) for cell in element.get("cells", ())) if element.get("cells") else 0
        elif element.get("type") == "text_block":
            element_id = str(element.get("element_id", ""))
            element_metrics["padding"] = 18
            element_metrics["overflowY"] = False
            element_metrics["bodyFontSize"] = RENDER_TEXT_SIZES["answer_body"] if element_id.startswith("answer-") else RENDER_TEXT_SIZES["text_block_body"]
            element_metrics["titleFontSize"] = RENDER_TEXT_SIZES["answer_title"] if element_id.startswith("answer-") else RENDER_TEXT_SIZES["text_block_title"]
        elements.append(element_metrics)
    regions = []
    for region in page.get("regions", ()):
        if not isinstance(region, dict):
            continue
        rect = region.get("rect")
        if not isinstance(rect, dict):
            continue
        regions.append(
            {
                "publicId": region.get("public_id"),
                "role": region.get("role"),
                "label": region.get("label"),
                "rect": _map_rect(scene, rect),
            }
        )
    content_top_value = content_top if content_top is not None else 0.0
    content_bottom_value = content_bottom if content_bottom is not None else 0.0
    content_height = max(0.0, content_bottom_value - content_top_value)
    bottom_blank = max(0.0, surface_height - 48.0 - content_bottom_value)
    layout_errors: list[dict[str, Any]] = []
    for left_index, left in enumerate(elements):
        left_rect = left.get("rect")
        if not isinstance(left_rect, dict):
            continue
        for right in elements[left_index + 1 :]:
            right_rect = right.get("rect")
            if not isinstance(right_rect, dict):
                continue
            overlap_x, overlap_y = _overlap_amount(left_rect, right_rect)
            if overlap_x > 0.5 and overlap_y > 0.5:
                layout_errors.append(
                    {
                        "code": "element_rect_overlap",
                        "elementId": left.get("id"),
                        "overlappingElementId": right.get("id"),
                        "overlapX": round(overlap_x, 2),
                        "overlapY": round(overlap_y, 2),
                    }
                )
    for table in (element for element in elements if element.get("type") == "table"):
        table_rect = table.get("rect")
        if not isinstance(table_rect, dict):
            continue
        heading_rect = {
            "x": float(table_rect["x"]),
            "y": float(table_rect["y"]) - 50.0,
            "width": float(table_rect["width"]),
            "height": 50.0,
        }
        for other in elements:
            if other is table:
                continue
            other_rect = other.get("rect")
            if not isinstance(other_rect, dict):
                continue
            overlap_x, overlap_y = _overlap_amount(heading_rect, other_rect)
            if overlap_x > 0.5 and overlap_y > 0.5:
                layout_errors.append(
                    {
                        "code": "table_heading_element_overlap",
                        "elementId": table.get("id"),
                        "overlappingElementId": other.get("id"),
                        "overlapX": round(overlap_x, 2),
                        "overlapY": round(overlap_y, 2),
                    }
                )
    return {
        "schema_version": "1.0",
        "metric_source": METRIC_SOURCE,
        "surface_id": surface_id,
        "episode_id": info.get("episode_id"),
        "family": info.get("family"),
        "level": info.get("level"),
        "template_id": info.get("template_id"),
        "seed": info.get("seed"),
        "sheet_id": page.get("sheet_id"),
        "page_id": page.get("page_id"),
        "sheet_index": observation.get("current_sheet_index"),
        "page_index": observation.get("current_page_index"),
        "canvas_size": {"width": surface.get("width", AGENT_IMAGE_SIZE[0]), "height": surface.get("height", AGENT_IMAGE_SIZE[1])},
        "viewbox": dict(viewport),
        "content_frame": content_frame,
        "page_title_box": {"x": 48.0, "y": 96.0, "width": 260.0, "height": 30.0},
        "page_meta_box": {"x": 320.0, "y": 104.0, "width": 360.0, "height": 18.0},
        "elements": elements,
        "regions": regions,
        "overlay_note": scene.get("overlay_note"),
        "required_navigation": info.get("required_navigation", {}),
        "metrics": {
            "invalidLayout": bool(layout_errors),
            "layoutErrors": layout_errors,
            "consoleErrors": [],
            "uniqueColors": 0,
            "nonBackgroundRatio": 0.0,
            "content_top_px": round(content_top_value, 2),
            "content_bottom_px": round(content_bottom_value, 2),
            "bottom_blank_px": round(bottom_blank, 2),
            "content_area_ratio": round(content_height / max(surface_height, 1.0), 4),
            "table_bottom_px": round(max(table_bottoms), 2) if table_bottoms else None,
        },
    }


def _scene_visible_text(scene: dict[str, Any]) -> str:
    chunks: list[str] = []
    workbook = scene.get("workbook", {})
    page = scene.get("page", {})
    if isinstance(workbook, dict):
        chunks.append(str(workbook.get("title", "")))
        chunks.extend(str(item) for item in workbook.get("sheet_tabs", ()))
    if isinstance(page, dict):
        chunks.append(str(page.get("title", "")))
        for element in page.get("elements", ()):
            if not isinstance(element, dict):
                continue
            chunks.append(str(element.get("title", "")))
            metadata = element.get("metadata", {})
            if isinstance(metadata, dict):
                chunks.append(str(metadata.get("subtitle", "")))
            if element.get("type") == "text_block":
                chunks.extend(str(line) for line in element.get("lines", ()))
            if element.get("type") == "table":
                for cell in element.get("cells", ()):
                    if isinstance(cell, dict):
                        chunks.append(str(cell.get("text", "")))
    return "\n".join(item for item in chunks if item)


def _scene_choice_values(scene: dict[str, Any]) -> list[str]:
    page = scene.get("page", {})
    if not isinstance(page, dict):
        return []
    values: list[str] = []
    for element in page.get("elements", ()):
        if not isinstance(element, dict) or element.get("type") != "text_block":
            continue
        if not str(element.get("title", "")).startswith("선택지 "):
            continue
        lines = [str(line) for line in element.get("lines", ()) if str(line).strip()]
        if lines:
            values.append(lines[0])
    return values


def _scene_non_wide_scrollbar_tables(scene: dict[str, Any]) -> list[str]:
    page = scene.get("page", {})
    if not isinstance(page, dict):
        return []
    metadata = page.get("metadata", {})
    if isinstance(metadata, dict) and metadata.get("wide_table"):
        return []
    offenders: list[str] = []
    for element in page.get("elements", ()):
        if not isinstance(element, dict) or element.get("type") != "table":
            continue
        element_metadata = element.get("metadata", {})
        if isinstance(element_metadata, dict) and element_metadata.get("excel_chrome"):
            offenders.append(str(element.get("element_id", "")))
    return offenders


def _has_dark_left_rail(image: Image.Image) -> bool:
    sample = image.crop((0, 0, 44, image.height)).convert("RGB")
    data = sample.tobytes()
    pixel_count = len(data) // 3
    if not pixel_count:
        return False
    dark = 0
    for offset in range(0, len(data), 3):
        r, g, b = data[offset], data[offset + 1], data[offset + 2]
        if r < 60 and g < 70 and b < 85:
            dark += 1
    return dark / pixel_count > 0.25


def _default_artifacts_root(output_dir: Path) -> Path:
    """Infer the artifacts root for an agent observation output directory."""

    if output_dir.name == "agent_observations_active":
        return output_dir.parent
    return output_dir


def _write_legacy_debug_pages(output_dir: Path, records: list[dict[str, Any]]) -> dict[str, str]:
    """Write compatibility-only pages kept outside the canonical dashboard contract."""

    index_path = output_dir / "index.html"
    review_path = output_dir / "review.html"
    index_path.write_text(_index_html(records), encoding="utf-8")
    review_path.write_text(_review_html(records, output_dir=output_dir), encoding="utf-8")
    return {"index": str(index_path), "review": str(review_path)}


def _generate_canonical_dashboard(
    *,
    output_dir: Path,
    manifest_path: Path,
    artifacts_root: Path | None,
    human_dir: Path | None,
) -> dict[str, Any]:
    """Delegate final static HTML/shared assets to export_review_dashboard when possible.

    The dashboard exporter is developed as the canonical owner of index.html pages.
    This agent-observation exporter still supports isolated fixture/temp-dir exports by
    keeping the legacy pages when the canonical dashboard inputs are not present.
    """

    resolved_artifacts_root = artifacts_root or _default_artifacts_root(output_dir)
    resolved_human_dir = human_dir or (resolved_artifacts_root / "ui-design-review" / "all-problems")
    dashboard = {
        "artifacts_root": str(resolved_artifacts_root),
        "human_dir": str(resolved_human_dir),
        "agent_dir": str(output_dir),
        "agent_manifest": str(manifest_path),
    }

    try:
        from table_env_bench.scripts.export_review_dashboard import export_review_dashboard
    except ModuleNotFoundError as exc:
        if exc.name == "table_env_bench.scripts.export_review_dashboard":
            dashboard.update({"status": "skipped", "reason": "dashboard_exporter_unavailable"})
            return dashboard
        raise

    result = export_review_dashboard(
        artifacts_root=resolved_artifacts_root,
        human_dir=resolved_human_dir,
        agent_dir=output_dir,
        agent_manifest=manifest_path,
    )
    if resolved_human_dir.exists():
        dashboard.update({"status": "generated", "result": result})
    else:
        dashboard.update({"status": "skipped", "reason": "missing_human_screenshot_dir", "result": result})
    return dashboard


def _validate_exported_gallery(
    output_dir: Path,
    records: list[dict[str, Any]],
    *,
    expected_count: int | None,
    contact_sheets: dict[str, Any] | None = None,
) -> dict[str, Any]:
    referenced_png = {str(record["png"]) for record in records}
    referenced_json = {str(record["observation"]) for record in records}
    referenced_semantic = {str(record["semantic_snapshot"]) for record in records}
    existing_png = {path.name for path in output_dir.glob("*.png")}
    existing_json = {path.name for path in output_dir.glob("*.observation.json")}
    existing_semantic = {path.name for path in output_dir.glob("*.semantic.json")}
    missing_png = sorted(referenced_png - existing_png)
    missing_json = sorted(referenced_json - existing_json)
    missing_semantic = sorted(referenced_semantic - existing_semantic)
    stale_png = sorted(existing_png - referenced_png)
    stale_json = sorted(existing_json - referenced_json)
    stale_semantic = sorted(existing_semantic - referenced_semantic)
    bad_dimensions: list[str] = []
    dark_left_rail_hits: list[str] = []
    prohibited_hits: list[dict[str, str]] = []
    duplicate_choice_hits: list[dict[str, Any]] = []
    non_wide_scrollbar_hits: list[dict[str, Any]] = []
    metric_source_mismatch: list[str] = []
    readability_hits: list[dict[str, Any]] = []
    small_table_font_styles = [
        name
        for name, style in TABLE_STYLE.items()
        if int(style.get("size", 0)) < 15
    ]
    small_text_sizes = [
        name
        for name, size in RENDER_TEXT_SIZES.items()
        if name not in {"footer", "page_meta", "status"} and int(size) < 14
    ]
    missing_contact_sheets: list[str] = []

    for record in records:
        png_path = output_dir / str(record["png"])
        if png_path.exists():
            with Image.open(png_path) as image:
                if image.size != AGENT_IMAGE_SIZE:
                    bad_dimensions.append(f"{record['surface_id']}:{image.size[0]}x{image.size[1]}")
                if _has_dark_left_rail(image):
                    dark_left_rail_hits.append(str(record["surface_id"]))
        visible_text = str(record.get("visible_text", ""))
        for term in PROHIBITED_VISIBLE_TERMS:
            if term in visible_text:
                prohibited_hits.append({"surface_id": str(record["surface_id"]), "term": term})
        choice_values = [str(value) for value in record.get("choice_values", ()) if str(value).strip()]
        if choice_values and len(set(choice_values)) != len(choice_values):
            duplicate_choice_hits.append(
                {
                    "surface_id": str(record["surface_id"]),
                    "values": choice_values,
                }
            )
        non_wide_scrollbar_tables = list(record.get("non_wide_scrollbar_tables", ()))
        if non_wide_scrollbar_tables:
            non_wide_scrollbar_hits.append(
                {
                    "surface_id": str(record["surface_id"]),
                    "tables": non_wide_scrollbar_tables,
                }
            )
        if record.get("metric_source") != METRIC_SOURCE:
            metric_source_mismatch.append(str(record["surface_id"]))
        metrics = record.get("semantic_metrics", {})
        if isinstance(metrics, dict) and str(record.get("template_id")) == "symbol_rule_induction" and int(record.get("seed", -1)) == 0:
            threshold_top = 145.0 if str(record.get("sheet_id")) == "query" else 130.0
            content_top = float(metrics.get("content_top_px", 9999.0) or 9999.0)
            bottom_blank = float(metrics.get("bottom_blank_px", 9999.0) or 9999.0)
            area_ratio = float(metrics.get("content_area_ratio", 0.0) or 0.0)
            reasons: list[str] = []
            if content_top > threshold_top:
                reasons.append(f"content_top_px={content_top:.1f}>{threshold_top:.1f}")
            if bottom_blank > 190.0:
                reasons.append(f"bottom_blank_px={bottom_blank:.1f}>190.0")
            if area_ratio < 0.56:
                reasons.append(f"content_area_ratio={area_ratio:.3f}<0.56")
            if reasons:
                readability_hits.append({"surface_id": str(record["surface_id"]), "reasons": reasons})

    count_ok = expected_count is None or len(records) == expected_count
    for item in (contact_sheets or {}).get("files", ()):
        contact_path = output_dir / str(item)
        if not contact_path.exists():
            missing_contact_sheets.append(str(item))

    ok = not (
        missing_png
        or missing_json
        or missing_semantic
        or stale_png
        or stale_json
        or stale_semantic
        or bad_dimensions
        or dark_left_rail_hits
        or prohibited_hits
        or duplicate_choice_hits
        or non_wide_scrollbar_hits
        or small_table_font_styles
        or small_text_sizes
        or metric_source_mismatch
        or readability_hits
        or missing_contact_sheets
    ) and count_ok
    return {
        "ok": ok,
        "active_count": len(records),
        "expected_count": expected_count,
        "missing_png_count": len(missing_png),
        "missing_json_count": len(missing_json),
        "missing_semantic_snapshot_count": len(missing_semantic),
        "stale_png_count": len(stale_png),
        "stale_json_count": len(stale_json),
        "stale_semantic_snapshot_count": len(stale_semantic),
        "bad_dimensions": bad_dimensions[:20],
        "dark_left_rail": dark_left_rail_hits[:20],
        "prohibited_visible_text": prohibited_hits[:20],
        "duplicate_choice_values": duplicate_choice_hits[:20],
        "non_wide_scrollbar_tables": non_wide_scrollbar_hits[:20],
        "small_table_font_styles": small_table_font_styles,
        "small_text_sizes": small_text_sizes,
        "metric_source_mismatch": metric_source_mismatch[:20],
        "readability_metric_failures": readability_hits[:20],
        "missing_contact_sheets": missing_contact_sheets[:20],
    }


def _write_contact_sheets(output_dir: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    contact_dir = output_dir / "contact_sheets"
    if contact_dir.exists():
        shutil.rmtree(contact_dir)
    contact_dir.mkdir(parents=True, exist_ok=True)
    by_level: dict[str, list[dict[str, Any]]] = {}
    by_template: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_level.setdefault(f"level_{record['level']}", []).append(record)
        by_template.setdefault(str(record["template_id"]), []).append(record)

    written: list[str] = []
    groups = {**by_level, **by_template}
    for group_name, group_records in groups.items():
        chosen = _representative_records(group_records, limit=12)
        if not chosen:
            continue
        path = contact_dir / f"{_safe_name(group_name)}.png"
        _write_contact_sheet_image(output_dir, path, chosen, title=group_name)
        written.append(str(path.relative_to(output_dir)))
    l3_representatives = _l3_representative_records(records)
    if l3_representatives:
        path = contact_dir / "l3_representative_pages.png"
        _write_contact_sheet_image(output_dir, path, l3_representatives, title="l3_representative_pages")
        written.append(str(path.relative_to(output_dir)))
    return {"dir": "contact_sheets", "count": len(written), "files": written}


def _representative_records(records: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    ordered = sorted(records, key=lambda item: (str(item["template_id"]), int(item["seed"]), str(item["sheet_id"]), str(item["page_id"])))
    selected: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for record in ordered:
        key = (str(record["template_id"]), str(record["sheet_id"]), str(record["page_id"]))
        if key in seen:
            continue
        selected.append(record)
        seen.add(key)
        if len(selected) >= limit:
            break
    return selected


def _l3_representative_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    requested = (
        ("abbrev_doc_reference", "query", "query-p1"),
        ("abbrev_doc_reference", "main", "main-p1"),
        ("abbrev_doc_reference", "glossary", "glossary-p1"),
        ("abbrev_doc_reference", "query", "query-p2"),
        ("symbol_rule_induction", "examples", "examples-p1"),
        ("symbol_rule_induction", "query", "query-p1"),
        ("symbol_rule_induction", "query", "query-p2"),
        ("color_condition_rule_induction", "examples", "examples-p1"),
        ("color_condition_rule_induction", "query", "query-p1"),
        ("color_condition_rule_induction", "query", "query-p2"),
        ("merged_header_scope", "examples", "examples-p1"),
        ("merged_header_scope", "notes", "notes-p1"),
        ("merged_header_scope", "query", "query-p1"),
        ("merged_header_pan_scope", "wide", "wide-p1"),
        ("merged_header_pan_scope", "query", "query-p1"),
        ("merged_header_pan_scope", "query", "query-p2"),
        ("wide_table_navigation", "directory", "directory-p1"),
        ("wide_table_navigation", "wide", "wide-p1"),
        ("wide_table_navigation", "query", "query-p1"),
        ("wide_table_navigation", "query", "query-p2"),
        ("wide_table_viewport_trace", "examples", "examples-p1"),
        ("wide_table_viewport_trace", "wide", "wide-p1"),
        ("wide_table_viewport_trace", "query", "query-p1"),
        ("zoom_micro_marker_exception", "examples", "examples-p1"),
        ("zoom_micro_marker_exception", "query", "query-p1"),
        ("zoom_micro_marker_exception", "query", "query-p2"),
    )
    l3_records = [record for record in records if int(record["level"]) == 3]
    selected: list[dict[str, Any]] = []
    for template_id, sheet_id, page_id in requested:
        matches = [
            record
            for record in l3_records
            if str(record["template_id"]) == template_id
            and str(record["sheet_id"]) == sheet_id
            and str(record["page_id"]) == page_id
        ]
        if matches:
            selected.append(sorted(matches, key=lambda item: int(item["seed"]))[0])
    return selected


def _write_contact_sheet_image(output_dir: Path, path: Path, records: list[dict[str, Any]], *, title: str) -> None:
    thumb_w = 320
    thumb_h = round(thumb_w * AGENT_IMAGE_SIZE[1] / AGENT_IMAGE_SIZE[0])
    label_h = 18
    cols = 3
    rows = (len(records) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * thumb_w, 30 + rows * (thumb_h + label_h)), "#f4f6f8")
    draw = ImageDraw.Draw(canvas)
    draw.text((10, 8), title, fill="#64748b")
    for index, record in enumerate(records):
        row, col = divmod(index, cols)
        x = col * thumb_w
        y = 30 + row * (thumb_h + label_h)
        with Image.open(output_dir / str(record["png"])) as image:
            thumb = image.resize((thumb_w, thumb_h))
            canvas.paste(thumb, (x, y))
        label = f"L{record['level']} · {record['sheet_id']}/{record['page_id']}"
        draw.rectangle((x, y + thumb_h, x + thumb_w, y + thumb_h + label_h), fill="#f8fafc")
        draw.text((x + 6, y + thumb_h + 4), label[:36], fill="#64748b")
    canvas.save(path)


def export_agent_observation_gallery(
    out_dir: str | Path,
    *,
    suite: str | None = "canonical_dev",
    all_benchmark_records: bool = False,
    family: str | None = None,
    levels: list[int] | None = None,
    seeds: list[int] | None = None,
    template_id: str | None = None,
    dashboard_artifacts_root: str | Path | None = None,
    dashboard_human_dir: str | Path | None = None,
    generate_dashboard: bool = True,
) -> dict[str, object]:
    output_dir = Path(out_dir)
    _clean_generated_output(output_dir)

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
                viewbox_payload = info.get("viewbox", {})
                viewbox = Rect(
                    x=float(viewbox_payload.get("x", 0.0)),
                    y=float(viewbox_payload.get("y", 0.0)),
                    width=float(viewbox_payload.get("width", env.renderer.config.viewport_width)),
                    height=float(viewbox_payload.get("height", env.renderer.config.viewport_height)),
                )
                full_scene = build_page_scene(
                    spec.workbook,
                    sheet_index=int(info.get("active_sheet_index", sheet_index)),
                    page_index=int(info.get("current_page_index", page_index)),
                    viewport=viewbox,
                    config=env.renderer.config,
                )
                _capture_current_observation(
                    output_dir=output_dir,
                    records=records,
                    ref=ref,
                    observation=observation,
                    info=info,
                    full_scene=full_scene,
                    surface_index=surface_index,
                )
                surface_index += 1

    public_records = [
        {
            key: value
            for key, value in record.items()
            if key not in {"visible_text", "choice_values", "non_wide_scrollbar_tables", "semantic_metrics"}
        }
        for record in records
    ]
    expected_count = EXPECTED_ALL_BENCHMARK_SURFACES if all_benchmark_records else None
    contact_sheets = _write_contact_sheets(output_dir, public_records)
    validation = _validate_exported_gallery(
        output_dir,
        records,
        expected_count=expected_count,
        contact_sheets=contact_sheets,
    )

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "mode": "agent_observation",
                "suite": None if all_benchmark_records else suite,
                "all_benchmark_records": all_benchmark_records,
                "surfaces": public_records,
                "validation": validation,
                "contact_sheets": contact_sheets,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    legacy_pages = _write_legacy_debug_pages(output_dir, public_records)
    dashboard_result: dict[str, Any] = {"status": "skipped", "reason": "disabled"}
    if generate_dashboard:
        dashboard_result = _generate_canonical_dashboard(
            output_dir=output_dir,
            manifest_path=manifest_path,
            artifacts_root=Path(dashboard_artifacts_root) if dashboard_artifacts_root is not None else None,
            human_dir=Path(dashboard_human_dir) if dashboard_human_dir is not None else None,
        )
    dashboard_payload = dashboard_result.get("result") if isinstance(dashboard_result.get("result"), dict) else {}
    index_path = dashboard_payload.get("agent_index") or legacy_pages["index"]
    return {
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "index": index_path,
        "review": legacy_pages["review"],
        "dashboard": dashboard_result,
        "dashboard_index": dashboard_payload.get("index"),
        "dashboard_css": dashboard_payload.get("css"),
        "dashboard_js": dashboard_payload.get("js"),
        "count": len(public_records),
        "validation": validation,
        "contact_sheets": contact_sheets,
    }


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


def _review_html(records: list[dict[str, Any]], *, output_dir: Path) -> str:
    records_json = json.dumps(records, ensure_ascii=False)
    viewport_width, viewport_height = AGENT_IMAGE_SIZE
    snapshots: dict[str, Any] = {}
    for record in records:
        snapshot_path = output_dir / str(record.get("semantic_snapshot", ""))
        if snapshot_path.exists():
            snapshots[str(record["surface_id"])] = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshots_json = json.dumps(snapshots, ensure_ascii=False)
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
          body {{ padding: 0; margin: 0; background: #eef2f6; }}
          .review-shell {{
            min-height: 100vh;
            display: flex;
            flex-direction: column;
          }}
          .review-panel {{
            position: sticky;
            top: 0;
            z-index: 5;
            display: grid;
            grid-template-columns: minmax(180px, 260px) 1fr auto;
            align-items: center;
            gap: 10px;
            background: #fff;
            border-bottom: 1px solid #d6dee8;
            padding: 8px 12px;
          }}
          .review-panel h2 {{ margin: 0; font-size: 14px; color: #0f172a; }}
          select {{
            width: 100%;
            padding: 8px 10px;
            border: 1px solid var(--teb-ghost-border-strong);
            border-radius: var(--teb-radius-md);
          }}
          .filter-grid {{
            display: none;
            grid-template-columns: repeat(4, minmax(120px, 1fr));
            gap: 10px;
            grid-column: 1 / -1;
          }}
          body[data-filters-open="true"] .filter-grid {{ display: grid; }}
          .filter-grid label {{
            display: grid;
            gap: 5px;
            color: var(--teb-on-surface-variant);
            font-size: 12px;
          }}
          .review-actions {{ display: flex; gap: 6px; align-items: center; }}
          .review-actions button, .details-toggle {{
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            background: #fff;
            color: #1f2937;
            padding: 7px 9px;
            font-size: 12px;
            cursor: pointer;
          }}
          .review-actions button[data-active="true"] {{ background: #0f172a; color: #fff; }}
          #surface-meta {{ margin: 0; font-size: 12px; color: #475569; white-space: nowrap; }}
          .surface-wrap {{
            flex: 1;
            overflow: auto;
            padding: 12px;
          }}
          .surface-frame {{
            min-width: max-content;
            display: flex;
            justify-content: center;
            align-items: flex-start;
          }}
          #agent-observation {{
            display: block;
            width: {viewport_width}px;
            height: {viewport_height}px;
            transform-origin: top center;
            background: #fff;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
          }}
          .details {{
            display: none;
            position: fixed;
            right: 14px;
            top: 58px;
            width: 360px;
            max-height: calc(100vh - 76px);
            overflow: auto;
            background: #fff;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            padding: 12px;
            box-shadow: 0 16px 40px rgba(15, 23, 42, 0.16);
            z-index: 7;
          }}
          body[data-details-open="true"] .details {{ display: block; }}
          .details h3 {{ margin: 0 0 8px; font-size: 14px; }}
          .details pre {{ white-space: pre-wrap; font-size: 11px; color: #334155; }}
          body[data-focus-mode="true"] .review-panel, body[data-focus-mode="true"] .details {{ display: none; }}
          body[data-focus-mode="true"] .surface-wrap {{ padding: 0; background: #111827; }}
          body[data-focus-mode="true"] #agent-observation {{ box-shadow: none; }}
          .status-pass {{ color: #166534; }}
          .status-fail {{ color: #991b1b; }}
          @media (max-width: 1200px) {{
            .review-panel {{ grid-template-columns: 1fr; }}
            .review-actions {{ flex-wrap: wrap; }}
          }}
        </style>
      </head>
      <body data-review-contract-version="{REVIEW_CONTRACT_VERSION}">
        <section class="review-shell">
          <aside class="review-panel">
            <h2>Observation QA</h2>
            <select id="surface-select"></select>
            <div class="review-actions">
              <span id="surface-meta"></span>
              <button type="button" id="zoom-fit">Fit</button>
              <button type="button" data-zoom="0.5">50%</button>
              <button type="button" data-zoom="0.75">75%</button>
              <button type="button" data-zoom="1">100%</button>
              <button type="button" data-zoom="1.25">125%</button>
              <button type="button" id="focus-toggle">Focus</button>
              <button type="button" id="filters-toggle">Filters</button>
              <button type="button" id="details-toggle" class="details-toggle">Details</button>
            </div>
            <div class="filter-grid">
              <label>Level<select id="filter-level"><option value="">전체</option></select></label>
              <label>Template<select id="filter-template"><option value="">전체</option></select></label>
              <label>Sheet/Page<select id="filter-page"><option value="">전체</option></select></label>
              <label>Seed<select id="filter-seed"><option value="">전체</option></select></label>
            </div>
          </aside>
          <main class="surface-wrap"><div class="surface-frame"><img id="agent-observation" alt="agent observation"/></div></main>
          <aside class="details">
            <h3>선택 화면 정보</h3>
            <p id="review-status"></p>
            <p id="review-validation"></p>
            <p id="review-metrics"></p>
            <details><summary>Full ID</summary><pre id="review-full-id"></pre></details>
          </aside>
        </section>
        <script id="review-snapshot-json" type="application/json">{snapshots_json}</script>
        <script>
          const records = {records_json};
          const viewportSize = {{ width: {viewport_width}, height: {viewport_height} }};
          const snapshots = JSON.parse(document.getElementById('review-snapshot-json').textContent || '{{}}');
          const select = document.getElementById('surface-select');
          const image = document.getElementById('agent-observation');
          const meta = document.getElementById('surface-meta');
          const status = document.getElementById('review-status');
          const validationEl = document.getElementById('review-validation');
          const metricsEl = document.getElementById('review-metrics');
          const fullIdEl = document.getElementById('review-full-id');
          const filters = {{
            level: document.getElementById('filter-level'),
            template: document.getElementById('filter-template'),
            page: document.getElementById('filter-page'),
            seed: document.getElementById('filter-seed'),
          }};
          function fillFilter(selectEl, values) {{
            values.forEach((value) => {{
              const option = document.createElement('option');
              option.value = String(value);
              option.textContent = String(value);
              selectEl.appendChild(option);
            }});
          }}
          fillFilter(filters.level, [...new Set(records.map((item) => item.level))].sort((a, b) => a - b).map((item) => `L${{item}}`));
          fillFilter(filters.template, [...new Set(records.map((item) => item.template_id))].sort());
          fillFilter(filters.page, [...new Set(records.map((item) => `${{item.sheet_id}}/${{item.page_id}}`))].sort());
          fillFilter(filters.seed, [...new Set(records.map((item) => item.seed))].sort((a, b) => a - b));
          const templateLabels = {{
            symbol_rule_induction: '기호 규칙',
            abbrev_doc_reference: '약어 문서',
            color_condition_rule_induction: '조건 서식',
            legend_color_exception_scope: '범례 예외',
            merged_header_scope: '병합 헤더',
            merged_header_pan_scope: '가로 헤더',
            wide_table_navigation: '와이드 원장',
            wide_table_viewport_trace: '뷰포트 추적',
            zoom_micro_marker_exception: '미세 마커',
          }};
          function compactLabel(record) {{
            const template = templateLabels[record.template_id] || record.template_id;
            return `L${{record.level}} · ${{template}} · ${{record.sheet}} · s${{record.seed}}`;
          }}
          function filteredRecords() {{
            return records.filter((item) => {{
              if (filters.level.value && filters.level.value !== `L${{item.level}}`) return false;
              if (filters.template.value && filters.template.value !== item.template_id) return false;
              if (filters.page.value && filters.page.value !== `${{item.sheet_id}}/${{item.page_id}}`) return false;
              if (filters.seed.value && filters.seed.value !== String(item.seed)) return false;
              return true;
            }});
          }}
          function refreshOptions() {{
            const items = filteredRecords();
            select.innerHTML = '';
            items.forEach((record) => {{
              const option = document.createElement('option');
              option.value = record.surface_id;
              option.textContent = compactLabel(record);
              select.appendChild(option);
            }});
            if (items.length) loadSurface(items[0].surface_id);
          }}
          function setScale(value) {{
            const wrap = document.querySelector('.surface-wrap');
            const frame = document.querySelector('.surface-frame');
            let scale = value;
            if (value === 'fit') {{
              const availableW = Math.max(320, wrap.clientWidth - 24);
              const availableH = Math.max(240, wrap.clientHeight - 24);
              scale = Math.min(1, availableW / viewportSize.width, availableH / viewportSize.height);
            }}
            image.style.transform = `scale(${{scale}})`;
            frame.style.width = `${{viewportSize.width * scale}}px`;
            frame.style.height = `${{viewportSize.height * scale}}px`;
            meta.textContent = `${{meta.dataset.label || ''}} · ${{Math.round(scale * 100)}}%`;
            document.querySelectorAll('[data-zoom], #zoom-fit').forEach((button) => button.dataset.active = 'false');
          }}
          document.querySelectorAll('[data-zoom]').forEach((button) => button.addEventListener('click', () => setScale(Number(button.dataset.zoom))));
          document.getElementById('zoom-fit').addEventListener('click', () => setScale('fit'));
          document.getElementById('focus-toggle').addEventListener('click', () => {{
            document.body.dataset.focusMode = document.body.dataset.focusMode === 'true' ? 'false' : 'true';
            setScale(document.body.dataset.focusMode === 'true' ? 'fit' : 1);
          }});
          document.getElementById('filters-toggle').addEventListener('click', () => {{
            document.body.dataset.filtersOpen = document.body.dataset.filtersOpen === 'true' ? 'false' : 'true';
          }});
          document.getElementById('details-toggle').addEventListener('click', () => {{
            document.body.dataset.detailsOpen = document.body.dataset.detailsOpen === 'true' ? 'false' : 'true';
          }});
          function loadSurface(surfaceId) {{
            const record = records.find((item) => item.surface_id === surfaceId) || records[0];
            if (!record) return;
            const snapshot = snapshots[record.surface_id] || null;
            image.src = record.png;
            document.body.dataset.surfaceLoaded = 'pending';
            image.onload = () => {{
              document.body.dataset.surfaceLoaded = record.surface_id;
              const canUse100 = window.innerWidth >= 1160 && window.innerHeight >= 860;
              setScale(canUse100 ? 1 : 'fit');
            }};
            meta.dataset.label = compactLabel(record);
            meta.textContent = compactLabel(record);
            const metrics = snapshot?.metrics || {{}};
            const failures = [];
            if (metrics.content_top_px && metrics.content_top_px > (record.sheet_id === 'query' ? 145 : 130)) failures.push('content top');
            if (metrics.bottom_blank_px && metrics.bottom_blank_px > 190) failures.push('bottom blank');
            if (metrics.content_area_ratio && metrics.content_area_ratio < 0.56) failures.push('content ratio');
            status.className = failures.length ? 'status-fail' : 'status-pass';
            status.textContent = failures.length ? `FAIL · ${{failures.join(', ')}}` : 'PASS';
            validationEl.textContent = `source: ${{record.metric_source || 'n/a'}} · contract v${{record.review_contract_version || 0}}`;
            metricsEl.textContent = snapshot ? `top ${{metrics.content_top_px}}px · bottom blank ${{metrics.bottom_blank_px}}px · ratio ${{metrics.content_area_ratio}}` : 'semantic snapshot 없음';
            fullIdEl.textContent = record.surface_id;
          }}
          const params = new URLSearchParams(window.location.search);
          const initial = params.get('surface') || '{first_surface_id}';
          if (select) {{
            select.value = initial;
            select.addEventListener('change', () => loadSurface(select.value));
          }}
          Object.values(filters).forEach((filter) => filter.addEventListener('change', refreshOptions));
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
    parser.add_argument("--dashboard-artifacts-root", type=Path)
    parser.add_argument("--dashboard-human-dir", type=Path)
    parser.add_argument(
        "--skip-dashboard",
        action="store_true",
        help="Write only legacy debug pages instead of delegating to the canonical dashboard exporter.",
    )
    args = parser.parse_args()

    result = export_agent_observation_gallery(
        args.out,
        suite=args.suite,
        all_benchmark_records=args.all_benchmark_records,
        family=args.family,
        levels=args.levels,
        seeds=args.seeds,
        template_id=args.template_id,
        dashboard_artifacts_root=args.dashboard_artifacts_root,
        dashboard_human_dir=args.dashboard_human_dir,
        generate_dashboard=not args.skip_dashboard,
    )
    print(f"Wrote {result['count']} agent observation previews to {result['output_dir']}")
    print(f"index={result['index']}")
    print(f"review={result['review']}")
    print(f"manifest={result['manifest']}")
    dashboard = result.get("dashboard", {})
    if isinstance(dashboard, dict):
        print(f"dashboard_status={dashboard.get('status')}")


if __name__ == "__main__":
    main()
