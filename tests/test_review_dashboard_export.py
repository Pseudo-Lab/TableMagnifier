import json
import re
from pathlib import Path

from table_env_bench.scripts.export_review_dashboard import export_review_dashboard


DATA_SCRIPT_RE = re.compile(
    r'<script id="review-dashboard-data" type="application/json">(.*?)</script>',
    re.DOTALL,
)
EXTERNAL_REF_RE = re.compile(r"https?://|cdn\.|fonts\.googleapis|fonts\.gstatic")
MANIFEST_FETCH_RE = re.compile(r"fetch\([^\n)]*manifest\.json", re.IGNORECASE)


def _write_fixture_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # The dashboard generator only needs stable local paths for static review; image
    # decoding is intentionally left to the browser runtime.
    path.write_bytes(b"\x89PNG\r\n\x1a\n")


def _write_observation(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"observation": {"viewport": "fixture"}}, ensure_ascii=False), encoding="utf-8")


def _build_dashboard_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    artifacts_root = tmp_path / "artifacts"
    human_dir = artifacts_root / "ui-design-review" / "all-problems"
    agent_dir = artifacts_root / "agent_observations_active"
    manifest_path = agent_dir / "manifest.json"

    for name in [
        "01-k_vis_table_arc-l1-merged_header_scope-s0.png",
        "02-k_vis_table_arc-l2-symbol_rule_induction-s3.png",
    ]:
        _write_fixture_png(human_dir / name)

    surfaces = [
        {
            "surface_id": "match__main__v1",
            "family": "k_vis_table_arc",
            "level": 1,
            "template_id": "merged_header_scope",
            "seed": 0,
            "episode_id": "episode-match",
            "sheet": "본문",
            "sheet_id": "main",
            "sheet_index": 1,
            "page_id": "main-p1",
            "page_index": 0,
            "question": "본문 표에서 합계를 확인하세요.",
            "png": "match-main.png",
            "observation": "match-main.observation.json",
        },
        {
            "surface_id": "match__query__v1",
            "family": "k_vis_table_arc",
            "level": 1,
            "template_id": "merged_header_scope",
            "seed": 0,
            "episode_id": "episode-match",
            "sheet": "질의",
            "sheet_id": "query",
            "sheet_index": 0,
            "page_id": "query-p1",
            "page_index": 0,
            "question": "질의 시트를 먼저 확인하세요.",
            "png": "match-query.png",
            "observation": "match-query.observation.json",
        },
        {
            "surface_id": "agent_only__query__v1",
            "family": "k_vis_table_arc",
            "level": 3,
            "template_id": "wide_table_navigation",
            "seed": 7,
            "episode_id": "episode-agent-only",
            "sheet": "질의",
            "sheet_id": "query",
            "sheet_index": 0,
            "page_id": "query-p1",
            "page_index": 0,
            "question": "에이전트 전용 템플릿입니다.",
            "png": "agent-only-query.png",
            "observation": "agent-only-query.observation.json",
        },
    ]
    for surface in surfaces:
        _write_fixture_png(agent_dir / surface["png"])
        _write_observation(agent_dir / surface["observation"])

    agent_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "mode": "agent_observation",
                "suite": "fixture_suite",
                "all_benchmark_records": False,
                "surfaces": surfaces,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return artifacts_root, human_dir, agent_dir, manifest_path


def _export_fixture(tmp_path: Path) -> tuple[Path, Path, dict, dict]:
    artifacts_root, human_dir, agent_dir, manifest_path = _build_dashboard_fixture(tmp_path)
    result = export_review_dashboard(
        artifacts_root=artifacts_root,
        human_dir=human_dir,
        agent_dir=agent_dir,
        agent_manifest=manifest_path,
    )

    assert Path(result["index"]) == artifacts_root / "index.html"
    assert Path(result["agent_index"]) == agent_dir / "index.html"
    assert Path(result["css"]) == artifacts_root / "review-dashboard-assets" / "review-dashboard.css"
    assert Path(result["js"]) == artifacts_root / "review-dashboard-assets" / "review-dashboard.js"

    hub_html = (artifacts_root / "index.html").read_text(encoding="utf-8")
    agent_html = (agent_dir / "index.html").read_text(encoding="utf-8")
    hub_data = _extract_review_data(hub_html, expected_page="hub")
    agent_data = _extract_review_data(agent_html, expected_page="agent")
    return artifacts_root, agent_dir, hub_data, agent_data


def _extract_review_data(html: str, *, expected_page: str) -> dict:
    match = DATA_SCRIPT_RE.search(html)
    assert match, "generated pages must embed canonical review data in #review-dashboard-data"
    payload = json.loads(match.group(1))
    assert payload["page"] == expected_page
    return payload["data"]


def test_dashboard_export_parses_human_filenames_and_embeds_canonical_data(tmp_path: Path) -> None:
    _artifacts_root, _agent_dir, hub_data, agent_data = _export_fixture(tmp_path)

    assert hub_data == agent_data
    humans = hub_data["human"]
    assert len(humans) == 2
    assert humans[0] == {
        "kind": "human",
        "ordinal": 1,
        "family": "k_vis_table_arc",
        "level": 1,
        "template_id": "merged_header_scope",
        "seed": 0,
        "episode_key": "k_vis_table_arc::L1::merged_header_scope::s0",
        "png": "ui-design-review/all-problems/01-k_vis_table_arc-l1-merged_header_scope-s0.png",
        "alt": "k_vis_table_arc L1 merged_header_scope seed 0 human UI screenshot",
    }
    assert humans[1]["level"] == 2
    assert humans[1]["template_id"] == "symbol_rule_induction"
    assert humans[1]["seed"] == 3


def test_dashboard_export_joins_episodes_and_orders_compare_surfaces_query_first(tmp_path: Path) -> None:
    _artifacts_root, _agent_dir, hub_data, _agent_data = _export_fixture(tmp_path)

    humans = {record["episode_key"]: record for record in hub_data["human"]}
    agent_episodes = {episode["episode_key"]: episode for episode in hub_data["agent"]["episodes"]}
    surfaces_by_episode: dict[str, list[dict]] = {}
    for surface in hub_data["agent"]["surfaces"]:
        surfaces_by_episode.setdefault(surface["episode_key"], []).append(surface)

    matched_key = "k_vis_table_arc::L1::merged_header_scope::s0"
    assert humans[matched_key]["png"].endswith("01-k_vis_table_arc-l1-merged_header_scope-s0.png")
    assert [surface["surface_id"] for surface in surfaces_by_episode[matched_key]] == ["match__query__v1", "match__main__v1"]
    assert agent_episodes[matched_key]["default_surface_id"] == "match__query__v1"

    agent_only_key = "k_vis_table_arc::L3::wide_table_navigation::s7"
    assert agent_only_key not in humans
    assert surfaces_by_episode[agent_only_key][0]["surface_id"] == "agent_only__query__v1"


def test_dashboard_export_preserves_rendered_count_parity_and_embedded_json(tmp_path: Path) -> None:
    _artifacts_root, _agent_dir, hub_data, agent_data = _export_fixture(tmp_path)

    assert hub_data["summary"]["human_count"] == len(hub_data["human"]) == 2
    assert hub_data["summary"]["agent_surface_count"] == len(hub_data["agent"]["surfaces"]) == 3
    assert hub_data["summary"]["agent_episode_count"] == len(hub_data["agent"]["episodes"]) == 2
    assert hub_data["summary"]["matched_episode_count"] == 1
    assert hub_data["summary"] == agent_data["summary"]


def test_dashboard_export_uses_relative_shared_assets_and_no_runtime_manifest_fetch(tmp_path: Path) -> None:
    artifacts_root, agent_dir, _hub_data, _agent_data = _export_fixture(tmp_path)

    hub_html = (artifacts_root / "index.html").read_text(encoding="utf-8")
    agent_html = (agent_dir / "index.html").read_text(encoding="utf-8")
    shared_js = (artifacts_root / "review-dashboard-assets" / "review-dashboard.js").read_text(encoding="utf-8")
    shared_css = (artifacts_root / "review-dashboard-assets" / "review-dashboard.css").read_text(encoding="utf-8")

    assert 'href="review-dashboard-assets/review-dashboard.css"' in hub_html
    assert 'src="review-dashboard-assets/review-dashboard.js"' in hub_html
    assert 'href="../review-dashboard-assets/review-dashboard.css"' in agent_html
    assert 'src="../review-dashboard-assets/review-dashboard.js"' in agent_html

    for content in [hub_html, agent_html, shared_js, shared_css]:
        assert not EXTERNAL_REF_RE.search(content)
        assert not MANIFEST_FETCH_RE.search(content)
