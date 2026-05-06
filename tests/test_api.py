from dataclasses import dataclass

from fastapi.testclient import TestClient

from table_env_bench.authoring import LeadAgent
from table_env_bench.authoring.models import FileMutation, PipelineContext, StageResult
from table_env_bench.server.authoring_store import AuthoringRunStore
import table_env_bench.server.app as server_app

app = server_app.app


@dataclass
class ApiFakeStage:
    stage: str
    allowed_prefixes: tuple[str, ...]
    name: str = "api-fake"

    def run(self, context: PipelineContext, *, attempt: int = 1) -> tuple[StageResult, list[FileMutation]]:
        mutations = []
        if self.stage == "rulebook":
            mutations = [FileMutation("docs/authoring/rule_contracts/api.json", '{"api": true}\n')]
        return (
            StageResult(stage=self.stage, status="passed", summary=f"{self.stage} ok", attempt=attempt),
            mutations,
        )


def test_api_session_flow_for_workbook_env() -> None:
    client = TestClient(app)

    catalog_response = client.get("/api/catalog")
    assert catalog_response.status_code == 200
    families = catalog_response.json()
    assert [item["family"] for item in families] == [
        "marker_position_rule_transfer",
        "excel_viewport_sheet_navigation",
    ]
    assert families[0]["is_preferred"] is True
    assert families[0]["family_status"] == "preferred"
    excel_family = next(item for item in families if item["family"] == "excel_viewport_sheet_navigation")
    assert excel_family["is_preferred"] is False
    assert excel_family["family_status"] == "active"
    assert all(item["family_status"] != "deprecated" for item in families)

    session_response = client.post(
        "/api/sessions",
        json={"family": "marker_position_rule_transfer", "level": 1, "seed": 0, "mode": "agent"},
    )
    assert session_response.status_code == 200
    session_payload = session_response.json()
    session_id = session_payload["session_id"]
    assert session_payload["info"]["sheet_tabs"] == ["예시", "범례", "반례", "질의"]
    assert session_payload["info"]["active_sheet_id"] == "examples"
    assert session_payload["info"]["current_page_id"] == "examples-p1"
    assert session_payload["info"]["zoom_index"] == 0
    assert session_payload["info"]["viewbox"]["width"] > 0
    assert session_payload["info"]["required_navigation"]["required_sheet_ids"] == ["examples", "legend", "exception", "query"]
    assert session_payload["observation"]["viewport_scene"]["page"]["page_id"] == "examples-p1"
    assert "elements" not in session_payload["observation"]["viewport_scene"]["page"]
    assert "regions" not in session_payload["observation"]["viewport_scene"]["page"]
    assert "notes" not in session_payload["observation"]["viewport_scene"]["page"]
    assert session_payload["observation"]["viewport_image_png_base64"]

    instances_response = client.get("/api/instances")
    assert instances_response.status_code == 200
    assert instances_response.json() == []

    step_response = client.post(
        f"/api/sessions/{session_id}/actions",
        json={"type": "select_sheet", "sheet": "질의"},
    )
    assert step_response.status_code == 200
    assert step_response.json()["observation"]["current_sheet_name"] == "질의"

    replay_response = client.get(f"/api/sessions/{session_id}/replay")
    assert replay_response.status_code == 200
    assert replay_response.json()["replay"]["action_count"] == 1

    instance_session_response = client.post("/api/sessions", json={"instance_id": "removed_instance", "mode": "agent"})
    assert instance_session_response.status_code == 404


def test_generated_benchmark_suite_catalog_is_compact_and_launchable() -> None:
    client = TestClient(app)

    response = client.get("/api/benchmark-suites")
    assert response.status_code == 200
    payload = response.json()
    assert list(payload) == ["suites"]
    suites = payload["suites"]
    assert [suite["suite_id"] for suite in suites] == ["canonical_dev"]

    first_suite = suites[0]
    first_template = first_suite["templates"][0]
    first_record = first_template["records"][0]
    assert first_template["family"] == "marker_position_rule_transfer"
    assert first_template["template_id"]
    assert first_template["seed_slots"] == sorted(first_template["seed_slots"])
    assert first_record["seed"] == first_template["seed_slots"][0]
    assert first_record["episode_id"] == (
        f"{first_record['family']}_{first_record['template_id']}_l{first_record['level']}_s{first_record['seed']}"
    )
    assert "records" in first_template
    assert "required_navigation" in first_record
    assert "required_evidence" not in first_record
    assert "free_seed" not in first_template
    assert "seed" not in first_template

    session_response = client.post(
        "/api/sessions",
        json={
            "family": first_record["family"],
            "level": first_record["level"],
            "seed": first_record["seed"],
            "template_id": first_record["template_id"],
            "mode": "agent",
        },
    )
    assert session_response.status_code == 200
    info = session_response.json()["info"]
    assert info["episode_id"] == first_record["episode_id"]
    assert info["template_id"] == first_record["template_id"]


def test_api_authoring_run_flow(monkeypatch, tmp_path) -> None:
    stage_map = {
        "rulebook": ApiFakeStage("rulebook", ("docs",)),
        "family_builder": ApiFakeStage("family_builder", ("src/table_env_bench/data/families/contracts",)),
        "visual_qa": ApiFakeStage("visual_qa", ()),
        "viewport_readability": ApiFakeStage("viewport_readability", ()),
        "red_team_solver": ApiFakeStage("red_team_solver", ()),
        "regression_gate": ApiFakeStage("regression_gate", ()),
    }
    monkeypatch.setattr(
        server_app,
        "authoring_store",
        AuthoringRunStore(lead_agent=LeadAgent(repo_root=tmp_path, stage_map=stage_map)),
    )
    client = TestClient(app)

    create_response = client.post("/api/agent-runs", json={"family": "demo_family", "seed_samples": [0], "apply_changes": False})
    assert create_response.status_code == 200
    payload = create_response.json()
    run_id = payload["run_id"]
    assert payload["overall_status"] == "passed"
    assert payload["stage_results"][0]["stage"] == "rulebook"

    list_response = client.get("/api/agent-runs")
    assert list_response.status_code == 200
    assert list_response.json()[0]["run_id"] == run_id

    get_response = client.get(f"/api/agent-runs/{run_id}")
    assert get_response.status_code == 200
    assert get_response.json()["run_id"] == run_id
