"""Export the canonical static review dashboard artifacts.

The dashboard exporter owns the static HTML contract for both the executive
review hub and the agent-observation inspection page.  It reads source evidence
from human screenshot filenames and the agent observation manifest, embeds a
compact review-data payload into each page, and emits shared local CSS/JS assets
so the exported pages work when opened directly from the filesystem.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

HUMAN_SCREENSHOT_RE = re.compile(
    r"^(?P<ordinal>\d+)-(?P<family>.+)-l(?P<level>\d+)-(?P<template_id>.+)-s(?P<seed>\d+)\.png$"
)
SHEET_ORDER = {
    "query": 0,
    "main": 1,
    "examples": 2,
    "example": 2,
    "glossary": 3,
    "reference": 3,
    "notes": 4,
    "note": 4,
    "directory": 5,
    "legend": 6,
    "wide": 7,
}
DATA_SCRIPT_ID = "review-dashboard-data"


@dataclass(frozen=True)
class DashboardPaths:
    artifacts_root: Path
    human_dir: Path
    agent_dir: Path
    agent_manifest: Path


def episode_key(family: object, level: object, template_id: object, seed: object) -> str:
    """Return the shared human/agent compare key."""
    return f"{family}::L{int(level)}::{template_id}::s{int(seed)}"


def parse_human_screenshot(path: Path, *, base_dir: Path | None = None) -> dict[str, Any]:
    """Parse a human review screenshot filename into dashboard metadata."""
    match = HUMAN_SCREENSHOT_RE.match(path.name)
    if not match:
        raise ValueError(f"Unsupported human screenshot filename: {path.name}")
    groups = match.groupdict()
    family = groups["family"]
    level = int(groups["level"])
    template_id = groups["template_id"]
    seed = int(groups["seed"])
    rel_path = path.name if base_dir is None else path.relative_to(base_dir).as_posix()
    key = episode_key(family, level, template_id, seed)
    return {
        "kind": "human",
        "ordinal": int(groups["ordinal"]),
        "family": family,
        "level": level,
        "template_id": template_id,
        "seed": seed,
        "episode_key": key,
        "png": rel_path,
        "alt": f"{family} L{level} {template_id} seed {seed} human UI screenshot",
    }


def collect_human_records(human_dir: Path, *, artifacts_root: Path) -> list[dict[str, Any]]:
    if not human_dir.exists():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(human_dir.glob("*.png")):
        try:
            record = parse_human_screenshot(path, base_dir=artifacts_root)
        except ValueError:
            continue
        records.append(record)
    return sorted(records, key=lambda item: (item["level"], item["template_id"], item["seed"], item["ordinal"]))


def surface_sort_key(surface: dict[str, Any]) -> tuple[Any, ...]:
    sheet_id = str(surface.get("sheet_id") or surface.get("sheet") or "").lower()
    page_id = str(surface.get("page_id") or "").lower()
    order = SHEET_ORDER.get(sheet_id, 8)
    version = _surface_version(surface)
    return (
        order,
        int(surface.get("sheet_index") or 0),
        int(surface.get("page_index") or 0),
        page_id,
        version,
        str(surface.get("surface_id") or surface.get("png") or ""),
    )


def _surface_version(surface: dict[str, Any]) -> int:
    text = str(surface.get("surface_id") or surface.get("png") or "")
    match = re.search(r"(?:^|__)v(\d+)(?:\.|$)", text)
    return int(match.group(1)) if match else 0


def _agent_png_path(png: object, *, agent_dir: Path, artifacts_root: Path) -> str:
    png_text = str(png or "")
    path = Path(png_text)
    if path.is_absolute():
        try:
            return path.relative_to(artifacts_root).as_posix()
        except ValueError:
            return path.name
    if "/" in png_text:
        return png_text
    try:
        return (agent_dir / png_text).relative_to(artifacts_root).as_posix()
    except ValueError:
        return png_text


def collect_agent_records(agent_manifest: Path, *, agent_dir: Path, artifacts_root: Path) -> dict[str, Any]:
    if not agent_manifest.exists():
        manifest: dict[str, Any] = {"mode": "agent_observation", "suite": None, "all_benchmark_records": False, "surfaces": []}
    else:
        manifest = json.loads(agent_manifest.read_text(encoding="utf-8"))
    surfaces: list[dict[str, Any]] = []
    for raw in manifest.get("surfaces", []):
        surface = dict(raw)
        family = surface.get("family")
        level = int(surface.get("level") or 0)
        template_id = surface.get("template_id") or "default"
        seed = int(surface.get("seed") or 0)
        key = episode_key(family, level, template_id, seed)
        surface["episode_key"] = key
        surface["png"] = _agent_png_path(surface.get("png"), agent_dir=agent_dir, artifacts_root=artifacts_root)
        if surface.get("observation"):
            obs_path = Path(str(surface["observation"]))
            if not obs_path.is_absolute() and "/" not in str(surface["observation"]):
                surface["observation"] = (agent_dir / obs_path).relative_to(artifacts_root).as_posix()
        surface["sort_order"] = list(surface_sort_key(surface))
        surfaces.append(surface)
    surfaces.sort(key=surface_sort_key)

    episodes: dict[str, dict[str, Any]] = {}
    for surface in surfaces:
        key = surface["episode_key"]
        episode = episodes.setdefault(
            key,
            {
                "episode_key": key,
                "family": surface.get("family"),
                "level": surface.get("level"),
                "template_id": surface.get("template_id"),
                "seed": surface.get("seed"),
                "surface_count": 0,
                "sheets": [],
                "default_surface_id": None,
            },
        )
        episode["surface_count"] += 1
        sheet_id = surface.get("sheet_id")
        if sheet_id and sheet_id not in episode["sheets"]:
            episode["sheets"].append(sheet_id)
        if episode["default_surface_id"] is None:
            episode["default_surface_id"] = surface.get("surface_id")
    for key, grouped in _group_surfaces(surfaces).items():
        query = next((item for item in grouped if str(item.get("sheet_id")) == "query"), None)
        if query:
            episodes[key]["default_surface_id"] = query.get("surface_id")
    return {
        "manifest_meta": {key: manifest.get(key) for key in ("mode", "suite", "all_benchmark_records")},
        "surfaces": surfaces,
        "episodes": sorted(episodes.values(), key=lambda item: (item.get("level") or 0, str(item.get("template_id")), item.get("seed") or 0)),
    }


def _group_surfaces(surfaces: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for surface in surfaces:
        grouped[surface["episode_key"]].append(surface)
    for key in grouped:
        grouped[key].sort(key=surface_sort_key)
    return dict(grouped)


def build_review_data(paths: DashboardPaths) -> dict[str, Any]:
    human = collect_human_records(paths.human_dir, artifacts_root=paths.artifacts_root)
    agent = collect_agent_records(paths.agent_manifest, agent_dir=paths.agent_dir, artifacts_root=paths.artifacts_root)
    human_keys = {record["episode_key"] for record in human}
    agent_keys = {record["episode_key"] for record in agent["surfaces"]}
    template_counts = Counter(str(item.get("template_id")) for item in agent["surfaces"])
    sheet_counts = Counter(str(item.get("sheet_id")) for item in agent["surfaces"])
    return {
        "schema_version": "1.0",
        "generated_by": "table_env_bench.scripts.export_review_dashboard",
        "episode_key_contract": "family + level + template_id + seed",
        "human": human,
        "agent": agent,
        "summary": {
            "human_count": len(human),
            "agent_surface_count": len(agent["surfaces"]),
            "agent_episode_count": len(agent["episodes"]),
            "matched_episode_count": len(human_keys & agent_keys),
            "human_only_episode_count": len(human_keys - agent_keys),
            "agent_only_episode_count": len(agent_keys - human_keys),
            "levels": sorted({item["level"] for item in human} | {int(item.get("level") or 0) for item in agent["surfaces"]}),
            "human_templates": sorted({item["template_id"] for item in human}),
            "agent_templates": sorted(template_counts),
            "agent_sheets": sorted(sheet_counts),
            "agent_template_counts": dict(sorted(template_counts.items())),
            "agent_sheet_counts": dict(sorted(sheet_counts.items())),
        },
    }


def _json_script(data: dict[str, Any], *, page: str) -> str:
    payload = {"page": page, "data": data}
    return f'<script id="{DATA_SCRIPT_ID}" type="application/json">{escape(json.dumps(payload, ensure_ascii=False), quote=False)}</script>'


def _metric_cards(data: dict[str, Any]) -> str:
    metrics = [
        ("Human UI", data["summary"]["human_count"], "사람 기준 캡처"),
        ("Agent surfaces", data["summary"]["agent_surface_count"], "관측 PNG"),
        ("Episodes", data["summary"]["agent_episode_count"], "agent episode"),
        ("Matched", data["summary"]["matched_episode_count"], "human ↔ agent"),
    ]
    return "".join(f'<article class="metric-card"><span>{label}</span><strong>{value}</strong><em>{hint}</em></article>' for label, value, hint in metrics)


def _html_shell(*, title: str, body_class: str, data: dict[str, Any], page: str, content: str, asset_prefix: str, artifact_prefix: str = "") -> str:
    return f"""<!doctype html>
<html lang="ko">
  <head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>{escape(title)}</title>
    <link rel="stylesheet" href="{asset_prefix}review-dashboard-assets/review-dashboard.css"/>
  </head>
  <body class="{body_class}" data-dashboard-page="{page}" data-artifact-prefix="{artifact_prefix}">
    {_json_script(data, page=page)}
    {content}
    <div id="review-modal" class="modal" hidden></div>
    <script src="{asset_prefix}review-dashboard-assets/review-dashboard.js"></script>
  </body>
</html>
"""


def render_hub_html(data: dict[str, Any], *, asset_prefix: str = "") -> str:
    content = f"""
<header class="hero">
  <nav class="top-nav"><a href="index.html">리뷰 허브</a><a href="agent_observations_active/index.html">Agent 대시보드</a></nav>
  <p class="eyebrow">K-VisTable-ARC Static Review</p>
  <h1>시각 테이블 QA 정적 리뷰 허브</h1>
  <p class="lede">Human UI 캡처와 agent 관측 surface를 분리해 보여주되, 같은 episode_key로 안전하게 비교합니다.</p>
  <section class="metrics">{_metric_cards(data)}</section>
</header>
<main class="dashboard-shell">
  <section class="panel" id="overview">
    <h2>리뷰 원칙</h2>
    <div class="rubric-grid">
      <article><h3>Human UI</h3><p>사람이 문제를 검토하는 polished screenshot입니다. 파일명에서 level/template/seed를 생성합니다.</p></article>
      <article><h3>Agent observation</h3><p>agent API의 viewport 관측 truth입니다. manifest.json에서 surface metadata를 생성합니다.</p></article>
      <article><h3>비교 규칙</h3><p><code>family + level + template_id + seed</code>를 episode_key로 사용하고 query surface를 우선 선택합니다.</p></article>
    </div>
  </section>
  <section class="panel" id="human-gallery">
    <div class="section-heading"><div><p class="eyebrow">Human screenshots</p><h2>Human UI 갤러리</h2></div><button class="ghost-button" data-reset-human>필터 초기화</button></div>
    <div class="controls" data-human-controls>
      <label>Level <select data-filter="human-level"><option value="">전체</option></select></label>
      <label>Template <select data-filter="human-template"><option value="">전체</option></select></label>
      <label>Seed <select data-filter="human-seed"><option value="">전체</option></select></label>
      <label>Sort <select data-sort="human"><option value="ordinal">파일 순서</option><option value="template">템플릿</option><option value="seed">Seed</option></select></label>
    </div>
    <div class="card-grid" data-human-grid></div>
    <div class="load-row"><button class="primary-button" data-human-load>더 보기</button><span data-human-count></span></div>
  </section>
  <section class="panel compare-panel" id="comparison">
    <div><p class="eyebrow">Human ↔ Agent</p><h2>비교 브릿지</h2><p>Human screenshot을 선택하면 같은 episode_key의 agent surface set으로 이동할 수 있습니다.</p></div>
    <div data-hub-compare-list class="compare-list"></div>
  </section>
  <section class="panel agent-summary">
    <h2>Agent 관측 요약</h2>
    <p>총 <strong>{data['summary']['agent_surface_count']}</strong>개 surface, <strong>{data['summary']['agent_episode_count']}</strong>개 episode.</p>
    <a class="primary-button" href="agent_observations_active/index.html">Agent 대시보드 열기</a>
  </section>
</main>
"""
    return _html_shell(title="TableMagnifier Static Review Dashboard", body_class="hub-page", data=data, page="hub", content=content, asset_prefix=asset_prefix)


def render_agent_html(data: dict[str, Any], *, asset_prefix: str = "../", artifact_prefix: str = "../") -> str:
    content = f"""
<header class="hero agent-hero">
  <nav class="top-nav"><a href="../index.html">리뷰 허브</a><a href="index.html">Agent 대시보드</a></nav>
  <p class="eyebrow">Agent Observation Dashboard</p>
  <h1>Agent surface QA 콘솔</h1>
  <p class="lede">manifest 기반 surface를 Gallery / Matrix / Compare 모드로 점검합니다. QA 체크리스트는 세션 메모리에서만 유지됩니다.</p>
  <section class="metrics">{_metric_cards(data)}</section>
</header>
<main class="dashboard-shell">
  <section class="panel sticky-controls">
    <div class="section-heading"><div><p class="eyebrow">Filters</p><h2>관측 필터</h2></div><button class="ghost-button" data-reset-agent>초기화</button></div>
    <div class="controls agent-controls">
      <label>Level <select data-filter="agent-level"><option value="">전체</option></select></label>
      <label>Template <select data-filter="agent-template"><option value="">전체</option></select></label>
      <label>Sheet <select data-filter="agent-sheet"><option value="">전체</option></select></label>
      <label>Seed <select data-filter="agent-seed"><option value="">전체</option></select></label>
      <label>Search <input data-filter="agent-search" type="search" placeholder="question, surface_id"/></label>
    </div>
    <div class="mode-tabs" role="tablist"><button data-mode="gallery" class="active">Gallery</button><button data-mode="matrix">Matrix</button><button data-mode="compare">Compare</button></div>
  </section>
  <section class="panel" data-agent-mode-panel="gallery">
    <div class="section-heading"><div><p class="eyebrow">Gallery</p><h2>Surface 갤러리</h2></div><span data-agent-count></span></div>
    <div class="card-grid agent-grid" data-agent-grid></div>
    <div class="load-row"><button class="primary-button" data-agent-load>더 보기</button></div>
  </section>
  <section class="panel" data-agent-mode-panel="matrix" hidden>
    <p class="eyebrow">Matrix</p><h2>Template · Sheet 매트릭스</h2>
    <div class="matrix-grid" data-agent-matrix></div>
    <div class="card-grid agent-grid compact" data-agent-matrix-detail></div>
  </section>
  <section class="panel" data-agent-mode-panel="compare" hidden>
    <div class="section-heading"><div><p class="eyebrow">Compare</p><h2>Episode surface set</h2></div><select data-compare-episode></select></div>
    <div data-agent-compare class="compare-stage"></div>
  </section>
</main>
"""
    return _html_shell(title="Agent Observation Dashboard", body_class="agent-page", data=data, page="agent", content=content, asset_prefix=asset_prefix, artifact_prefix=artifact_prefix)


def css_text() -> str:
    return r'''
:root{--bg:#f4f0e8;--ink:#1d2433;--muted:#697386;--card:#fffdf8;--line:#ded4c3;--brand:#3d5afe;--brand2:#00a1a7;--bad:#b42318;--ok:#15803d;--shadow:0 18px 60px rgba(29,36,51,.12);font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}*{box-sizing:border-box}body{margin:0;background:linear-gradient(135deg,#f9f4ea,#eaf2ff);color:var(--ink)}a{color:inherit}.hero{padding:28px clamp(18px,4vw,56px) 36px;background:radial-gradient(circle at top right,#dce8ff,transparent 32%),linear-gradient(135deg,#151b2d,#28375c);color:white}.agent-hero{background:radial-gradient(circle at top right,#c7fff4,transparent 32%),linear-gradient(135deg,#142820,#204858)}.top-nav{display:flex;gap:12px;margin-bottom:42px}.top-nav a{padding:9px 14px;border:1px solid rgba(255,255,255,.3);border-radius:999px;text-decoration:none;background:rgba(255,255,255,.09)}.eyebrow{margin:0 0 8px;color:#6f7f95;text-transform:uppercase;letter-spacing:.14em;font-size:12px;font-weight:800}.hero .eyebrow,.hero .lede{color:#d7e2ff}.hero h1{font-size:clamp(34px,6vw,72px);max-width:980px;line-height:.96;margin:0}.lede{font-size:18px;max-width:860px}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-top:28px}.metric-card,.panel{background:rgba(255,253,248,.94);border:1px solid var(--line);border-radius:24px;box-shadow:var(--shadow)}.metric-card{color:var(--ink);padding:18px}.metric-card span,.metric-card em{display:block;color:var(--muted);font-style:normal}.metric-card strong{display:block;font-size:34px}.dashboard-shell{display:grid;gap:22px;padding:24px clamp(14px,3vw,44px) 60px;max-width:1680px;margin:0 auto}.panel{padding:22px}.section-heading{display:flex;align-items:center;justify-content:space-between;gap:16px}.rubric-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.rubric-grid article{padding:16px;border:1px solid var(--line);border-radius:18px;background:white}.controls{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}.controls label{display:grid;gap:6px;color:var(--muted);font-size:13px;font-weight:700}.controls select,.controls input,.section-heading select{min-width:150px;border:1px solid var(--line);border-radius:12px;padding:10px 12px;background:white;color:var(--ink)}.card-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px}.review-card{border:1px solid var(--line);border-radius:18px;overflow:hidden;background:white;display:flex;flex-direction:column}.review-card figure{margin:0;background:#f7f3ea;aspect-ratio:4/3;display:grid;place-items:center;position:relative}.review-card img{max-width:100%;width:100%;height:100%;object-fit:contain;display:block}.review-card.broken figure:after{content:"이미지 경로 오류";position:absolute;inset:auto 10px 10px;background:var(--bad);color:#fff;padding:6px 10px;border-radius:10px;font-weight:800}.card-body{padding:13px}.meta-line{color:var(--muted);font-size:12px}.tag-row{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}.tag{font-size:11px;padding:4px 7px;border-radius:999px;background:#eef2ff;color:#29377a}.primary-button,.ghost-button,.mode-tabs button{border:0;border-radius:999px;padding:10px 15px;font-weight:800;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;justify-content:center}.primary-button{background:var(--brand);color:white}.ghost-button,.mode-tabs button{background:#eef1f6;color:#25324a}.mode-tabs{display:flex;gap:8px;flex-wrap:wrap}.mode-tabs button.active{background:var(--brand2);color:white}.load-row{display:flex;align-items:center;justify-content:center;gap:16px;margin-top:18px}.compare-list,.compare-stage{display:grid;gap:12px}.compare-item{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:12px;border:1px solid var(--line);border-radius:16px;background:white}.matrix-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px}.matrix-cell{padding:14px;border:1px solid var(--line);border-radius:16px;background:white;text-align:left;cursor:pointer}.matrix-cell strong{font-size:28px;display:block}.compare-surfaces{display:grid;grid-template-columns:280px minmax(0,1fr);gap:16px}.surface-list{display:grid;gap:8px;align-content:start}.surface-list button{text-align:left;border:1px solid var(--line);background:white;border-radius:12px;padding:10px;cursor:pointer}.surface-list button.active{border-color:var(--brand);box-shadow:0 0 0 3px rgba(61,90,254,.12)}.inspection{background:white;border:1px solid var(--line);border-radius:18px;padding:16px}.inspection img{width:100%;max-height:76vh;object-fit:contain;background:#f7f3ea;border-radius:14px}.qa-list{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:8px;margin-top:12px}.qa-list label{border:1px solid var(--line);border-radius:12px;padding:9px;background:#fffdf8}.modal{position:fixed;inset:0;background:rgba(8,13,25,.82);z-index:10;padding:30px;overflow:auto}.modal-card{background:white;border-radius:22px;max-width:1280px;margin:auto;padding:18px}.modal img{width:100%;max-height:78vh;object-fit:contain;background:#f7f3ea}.modal-close{float:right}.dim{color:var(--muted)}code{background:#eef1f6;padding:2px 5px;border-radius:6px}@media (max-width:860px){.metrics,.rubric-grid,.compare-surfaces{grid-template-columns:1fr}.section-heading{align-items:flex-start;flex-direction:column}.hero{padding:20px}.dashboard-shell{padding:14px}.card-grid{grid-template-columns:1fr}.controls label,.controls select,.controls input{width:100%}}
'''.strip()


def js_text() -> str:
    return r'''
(() => {
  const dataEl = document.getElementById('review-dashboard-data');
  if (!dataEl) return;
  const payload = JSON.parse(dataEl.textContent);
  const data = payload.data;
  const page = payload.page;
  const artifactPrefix = document.body.dataset.artifactPrefix || '';
  const assetUrl = (path) => `${artifactPrefix}${path}`;
  const state = { humanLimit: 96, agentLimit: 96, mode: 'gallery', humanIndex: 0, agentFilters: {}, humanFilters: {}, selectedEpisode: null, selectedSurface: null, imageMeta: new Map(), qa: new Map() };
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const uniq = (items) => Array.from(new Set(items.filter((v) => v !== undefined && v !== null && v !== ''))).sort((a,b) => String(a).localeCompare(String(b), 'ko', { numeric: true }));
  const episodeMap = new Map(data.agent.episodes.map((ep) => [ep.episode_key, ep]));
  const surfacesByEpisode = new Map();
  data.agent.surfaces.forEach((surface) => { if (!surfacesByEpisode.has(surface.episode_key)) surfacesByEpisode.set(surface.episode_key, []); surfacesByEpisode.get(surface.episode_key).push(surface); });
  function fillSelect(sel, values, prefix = '전체') { const node = $(sel); if (!node) return; node.innerHTML = `<option value="">${prefix}</option>` + values.map((v) => `<option value="${esc(v)}">${esc(v)}</option>`).join(''); }
  function esc(value) { return String(value ?? '').replace(/[&<>"']/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch])); }
  function trackImage(img, card, id) { img.addEventListener('load', () => { state.imageMeta.set(id, { width: img.naturalWidth, height: img.naturalHeight }); card?.classList.remove('broken'); const dim = card?.querySelector('[data-dim]'); if (dim) dim.textContent = `${img.naturalWidth}×${img.naturalHeight}`; }); img.addEventListener('error', () => { card?.classList.add('broken'); const dim = card?.querySelector('[data-dim]'); if (dim) dim.textContent = 'broken path'; }); }
  function humanCard(record, index) { const match = episodeMap.get(record.episode_key); const el = document.createElement('article'); el.className = 'review-card'; el.innerHTML = `<figure><img loading="lazy" src="${esc(record.png)}" alt="${esc(record.alt)}"></figure><div class="card-body"><strong>${esc(record.template_id)}</strong><p class="meta-line">L${record.level} · seed ${record.seed} · <span data-dim>loading</span></p><div class="tag-row"><span class="tag">${esc(record.family)}</span><span class="tag">${match ? match.surface_count + ' agent surfaces' : 'agent match 없음'}</span></div><button class="ghost-button" data-open-human>검사</button>${match ? `<a class="primary-button" href="agent_observations_active/index.html?episode=${encodeURIComponent(record.episode_key)}">Agent 비교</a>` : ''}</div>`; trackImage($('img', el), el, `human:${record.episode_key}`); $('[data-open-human]', el).addEventListener('click', () => openModal(record, data.human, index)); return el; }
  function surfaceCard(surface) { const el = document.createElement('article'); el.className = 'review-card'; el.innerHTML = `<figure><img loading="lazy" src="${esc(assetUrl(surface.png))}" alt="${esc(surface.surface_id)}"></figure><div class="card-body"><strong>${esc(surface.sheet_id)} / ${esc(surface.page_id)}</strong><p class="meta-line">${esc(surface.template_id)} · L${surface.level} · seed ${surface.seed} · <span data-dim>loading</span></p><div class="tag-row"><span class="tag">${esc(surface.family)}</span><span class="tag">${esc(surface.surface_id)}</span></div><button class="ghost-button" data-inspect-agent>검사</button></div>`; trackImage($('img', el), el, `agent:${surface.surface_id}`); $('[data-inspect-agent]', el).addEventListener('click', () => openAgentModal(surface)); return el; }
  function filteredHuman() { let items = data.human.slice(); const level = $('[data-filter="human-level"]')?.value; const template = $('[data-filter="human-template"]')?.value; const seed = $('[data-filter="human-seed"]')?.value; if (level) items = items.filter((x) => String(x.level) === level); if (template) items = items.filter((x) => x.template_id === template); if (seed) items = items.filter((x) => String(x.seed) === seed); const sort = $('[data-sort="human"]')?.value || 'ordinal'; items.sort((a,b) => sort === 'template' ? a.template_id.localeCompare(b.template_id) || a.seed-b.seed : sort === 'seed' ? a.seed-b.seed || a.ordinal-b.ordinal : a.ordinal-b.ordinal); return items; }
  function renderHuman() { const grid = $('[data-human-grid]'); if (!grid) return; const items = filteredHuman(); grid.replaceChildren(...items.slice(0, state.humanLimit).map(humanCard)); $('[data-human-count]').textContent = `${Math.min(items.length, state.humanLimit)} / ${items.length}`; $('[data-human-load]').hidden = state.humanLimit >= items.length; renderHubCompare(items); }
  function renderHubCompare(items) { const root = $('[data-hub-compare-list]'); if (!root) return; root.innerHTML = ''; items.slice(0, 12).forEach((record) => { const ep = episodeMap.get(record.episode_key); const div = document.createElement('div'); div.className = 'compare-item'; div.innerHTML = `<div><strong>${esc(record.template_id)} · L${record.level} · seed ${record.seed}</strong><p class="meta-line">${esc(record.episode_key)}</p></div>${ep ? `<a class="primary-button" href="agent_observations_active/index.html?episode=${encodeURIComponent(record.episode_key)}">${ep.surface_count}개 surface</a>` : '<span class="tag">agent-only coverage 없음</span>'}`; root.appendChild(div); }); }
  function filteredSurfaces() { let items = data.agent.surfaces.slice(); const level = $('[data-filter="agent-level"]')?.value; const template = $('[data-filter="agent-template"]')?.value; const sheet = $('[data-filter="agent-sheet"]')?.value; const seed = $('[data-filter="agent-seed"]')?.value; const q = ($('[data-filter="agent-search"]')?.value || '').toLowerCase(); if (level) items = items.filter((x) => String(x.level) === level); if (template) items = items.filter((x) => x.template_id === template); if (sheet) items = items.filter((x) => x.sheet_id === sheet); if (seed) items = items.filter((x) => String(x.seed) === seed); if (q) items = items.filter((x) => JSON.stringify([x.surface_id,x.question,x.page_id,x.sheet_id]).toLowerCase().includes(q)); return items; }
  function renderAgentGallery() { const grid = $('[data-agent-grid]'); if (!grid) return; const items = filteredSurfaces(); grid.replaceChildren(...items.slice(0, state.agentLimit).map(surfaceCard)); $('[data-agent-count]').textContent = `${Math.min(items.length, state.agentLimit)} / ${items.length}`; $('[data-agent-load]').hidden = state.agentLimit >= items.length; }
  function renderMatrix() { const root = $('[data-agent-matrix]'); if (!root) return; const counts = new Map(); filteredSurfaces().forEach((s) => { const key = `${s.template_id}|||${s.sheet_id}`; counts.set(key, (counts.get(key) || 0) + 1); }); root.innerHTML = ''; Array.from(counts.entries()).sort().forEach(([key,count]) => { const [template,sheet] = key.split('|||'); const btn = document.createElement('button'); btn.className = 'matrix-cell'; btn.innerHTML = `<span>${esc(template)}</span><strong>${count}</strong><em>${esc(sheet)}</em>`; btn.addEventListener('click', () => { const detail = $('[data-agent-matrix-detail]'); detail.replaceChildren(...filteredSurfaces().filter((s) => s.template_id === template && s.sheet_id === sheet).slice(0, 48).map(surfaceCard)); }); root.appendChild(btn); }); }
  function renderCompare() { const select = $('[data-compare-episode]'); const stage = $('[data-agent-compare]'); if (!select || !stage) return; if (!select.options.length) select.innerHTML = data.agent.episodes.map((ep) => `<option value="${esc(ep.episode_key)}">L${ep.level} · ${esc(ep.template_id)} · seed ${ep.seed} (${ep.surface_count})</option>`).join(''); const params = new URLSearchParams(location.search); const initial = params.get('episode'); if (initial && !state.selectedEpisode) select.value = initial; state.selectedEpisode = select.value || data.agent.episodes[0]?.episode_key; const surfaces = surfacesByEpisode.get(state.selectedEpisode) || []; const defaultId = episodeMap.get(state.selectedEpisode)?.default_surface_id || surfaces[0]?.surface_id; if (!state.selectedSurface || !surfaces.some((s) => s.surface_id === state.selectedSurface)) state.selectedSurface = defaultId; const selected = surfaces.find((s) => s.surface_id === state.selectedSurface) || surfaces[0]; stage.innerHTML = `<div class="compare-surfaces"><div class="surface-list">${surfaces.map((s) => `<button data-surface="${esc(s.surface_id)}" class="${s.surface_id === selected?.surface_id ? 'active' : ''}"><strong>${esc(s.sheet_id)} / ${esc(s.page_id)}</strong><br><span class="meta-line">${esc(s.surface_id)}</span></button>`).join('')}</div><div class="inspection" data-compare-inspection></div></div>`; $$('[data-surface]', stage).forEach((b) => b.addEventListener('click', () => { state.selectedSurface = b.dataset.surface; renderCompare(); })); if (selected) renderInspection($('[data-compare-inspection]'), selected); }
  function renderInspection(root, surface) { root.innerHTML = `<h3>${esc(surface.sheet_id)} / ${esc(surface.page_id)}</h3><p class="meta-line">${esc(surface.episode_key)} · ${esc(surface.surface_id)}</p><img loading="lazy" src="${esc(assetUrl(surface.png))}" alt="${esc(surface.surface_id)}"><p class="dim" data-dim>loading</p>${qaList(surface.surface_id)}`; trackImage($('img', root), root, `agent:${surface.surface_id}`); bindQA(root, surface.surface_id); }
  function qaList(id) { const checks = ['가독성 OK','coverage OK','label 안전','mismatch 없음','broken path 없음']; return `<div class="qa-list">${checks.map((c,i) => `<label><input type="checkbox" data-qa="${i}" ${state.qa.get(id)?.has(String(i)) ? 'checked' : ''}> ${c}</label>`).join('')}</div>`; }
  function bindQA(root, id) { $$('[data-qa]', root).forEach((box) => box.addEventListener('change', () => { const set = state.qa.get(id) || new Set(); box.checked ? set.add(box.dataset.qa) : set.delete(box.dataset.qa); state.qa.set(id, set); })); }
  function openModal(record, list, index) { const modal = $('#review-modal'); modal.hidden = false; modal.innerHTML = `<div class="modal-card"><button class="ghost-button modal-close">닫기</button><h2>${esc(record.template_id)} · L${record.level} · seed ${record.seed}</h2><p class="meta-line">${esc(record.episode_key)}</p><img src="${esc(record.png)}" alt="${esc(record.alt)}"><p class="dim" data-dim>loading</p></div>`; $('.modal-close', modal).onclick = () => modal.hidden = true; trackImage($('img', modal), $('.modal-card', modal), `modal:${record.episode_key}`); }
  function openAgentModal(surface) { const modal = $('#review-modal'); modal.hidden = false; modal.innerHTML = `<div class="modal-card"><button class="ghost-button modal-close">닫기</button><div data-agent-modal></div></div>`; $('.modal-close', modal).onclick = () => modal.hidden = true; renderInspection($('[data-agent-modal]', modal), surface); }
  function bindControls() { if (page === 'hub') { fillSelect('[data-filter="human-level"]', uniq(data.human.map((x) => x.level))); fillSelect('[data-filter="human-template"]', uniq(data.human.map((x) => x.template_id))); fillSelect('[data-filter="human-seed"]', uniq(data.human.map((x) => x.seed))); $$('[data-filter^="human"], [data-sort="human"]').forEach((n) => n.addEventListener('change', () => { state.humanLimit = 96; renderHuman(); })); $('[data-human-load]')?.addEventListener('click', () => { state.humanLimit += 96; renderHuman(); }); $('[data-reset-human]')?.addEventListener('click', () => { $$('[data-filter^="human"]').forEach((n) => n.value = ''); renderHuman(); }); renderHuman(); } else { fillSelect('[data-filter="agent-level"]', uniq(data.agent.surfaces.map((x) => x.level))); fillSelect('[data-filter="agent-template"]', uniq(data.agent.surfaces.map((x) => x.template_id))); fillSelect('[data-filter="agent-sheet"]', uniq(data.agent.surfaces.map((x) => x.sheet_id))); fillSelect('[data-filter="agent-seed"]', uniq(data.agent.surfaces.map((x) => x.seed))); $$('[data-filter^="agent"]').forEach((n) => n.addEventListener(n.tagName === 'INPUT' ? 'input' : 'change', () => { state.agentLimit = 96; renderAgentGallery(); renderMatrix(); })); $('[data-agent-load]')?.addEventListener('click', () => { state.agentLimit += 96; renderAgentGallery(); }); $('[data-reset-agent]')?.addEventListener('click', () => { $$('[data-filter^="agent"]').forEach((n) => n.value = ''); renderAgentGallery(); renderMatrix(); }); $$('[data-mode]').forEach((b) => b.addEventListener('click', () => { state.mode = b.dataset.mode; $$('[data-mode]').forEach((x) => x.classList.toggle('active', x === b)); $$('[data-agent-mode-panel]').forEach((p) => p.hidden = p.dataset.agentModePanel !== state.mode); if (state.mode === 'matrix') renderMatrix(); if (state.mode === 'compare') renderCompare(); })); $('[data-compare-episode]')?.addEventListener('change', () => { state.selectedSurface = null; renderCompare(); }); renderAgentGallery(); renderMatrix(); renderCompare(); } }
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape') { const modal = $('#review-modal'); if (modal) modal.hidden = true; } });
  bindControls();
})();
'''.strip()



def _relative_prefix(from_dir: Path, artifacts_root: Path) -> str:
    rel = Path(__import__("os").path.relpath(artifacts_root, from_dir)).as_posix()
    return "" if rel == "." else rel.rstrip("/") + "/"

def export_review_dashboard(
    *,
    artifacts_root: str | Path = "artifacts",
    human_dir: str | Path = "artifacts/ui-design-review/all-problems",
    agent_dir: str | Path = "artifacts/agent_observations_active",
    agent_manifest: str | Path = "artifacts/agent_observations_active/manifest.json",
) -> dict[str, Any]:
    paths = DashboardPaths(Path(artifacts_root), Path(human_dir), Path(agent_dir), Path(agent_manifest))
    paths.artifacts_root.mkdir(parents=True, exist_ok=True)
    paths.agent_dir.mkdir(parents=True, exist_ok=True)
    asset_dir = paths.artifacts_root / "review-dashboard-assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    data = build_review_data(paths)
    hub_path = paths.artifacts_root / "index.html"
    agent_path = paths.agent_dir / "index.html"
    css_path = asset_dir / "review-dashboard.css"
    js_path = asset_dir / "review-dashboard.js"
    hub_asset_prefix = _relative_prefix(hub_path.parent, paths.artifacts_root)
    agent_artifact_prefix = _relative_prefix(agent_path.parent, paths.artifacts_root)
    agent_asset_prefix = _relative_prefix(agent_path.parent, paths.artifacts_root)
    hub_path.write_text(render_hub_html(data, asset_prefix=hub_asset_prefix), encoding="utf-8")
    agent_path.write_text(render_agent_html(data, asset_prefix=agent_asset_prefix, artifact_prefix=agent_artifact_prefix), encoding="utf-8")
    css_path.write_text(css_text() + "\n", encoding="utf-8")
    js_path.write_text(js_text() + "\n", encoding="utf-8")
    return {
        "artifacts_root": str(paths.artifacts_root),
        "index": str(hub_path),
        "agent_index": str(agent_path),
        "css": str(css_path),
        "js": str(js_path),
        "human_count": data["summary"]["human_count"],
        "agent_surface_count": data["summary"]["agent_surface_count"],
        "agent_episode_count": data["summary"]["agent_episode_count"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export static TableMagnifier review dashboards.")
    parser.add_argument("--artifacts-root", default="artifacts")
    parser.add_argument("--human-dir", default="artifacts/ui-design-review/all-problems")
    parser.add_argument("--agent-dir", default="artifacts/agent_observations_active")
    parser.add_argument("--agent-manifest", default="artifacts/agent_observations_active/manifest.json")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = export_review_dashboard(
        artifacts_root=args.artifacts_root,
        human_dir=args.human_dir,
        agent_dir=args.agent_dir,
        agent_manifest=args.agent_manifest,
    )
    print(f"Wrote review dashboard: index={result['index']} agent_index={result['agent_index']}")
    print(f"human={result['human_count']} agent_surfaces={result['agent_surface_count']} episodes={result['agent_episode_count']}")


if __name__ == "__main__":
    main()
