import json
from pathlib import Path

import pytest

from table_env_bench.data.generators import benchmark_suite_manifest, benchmark_suite_records, list_instance_packs
from table_env_bench.data.instances import PRIVATE_DATA_ENV, load_instance_pack


def test_repo_no_longer_ships_public_instance_packs() -> None:
    manifest = benchmark_suite_manifest()
    pack_ids = [pack.pack_id for pack in list_instance_packs()]

    assert "public_dev_real_v1" not in manifest
    assert "public_smoke_real_v1" not in manifest
    assert benchmark_suite_records(suite="canonical_dev")
    assert all(not pack_id.startswith("public_") for pack_id in pack_ids)
    assert "benchmark_v1" not in pack_ids
    assert "public_dev_arc_v1" not in pack_ids
    assert "public_smoke_arc_v1" not in pack_ids


def test_hidden_holdout_pack_requires_private_data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    hidden_root = tmp_path / "private_instances"
    hidden_pack = hidden_root / "hidden_holdout_real_v1"
    hidden_pack.mkdir(parents=True)
    manifest = {
        "pack_id": "hidden_holdout_real_v1",
        "pack_label": "Hidden Holdout Real V1",
        "version": "1.0",
        "locale": "ko-KR",
        "benchmark_track": "canonical_real_tableqa",
        "pack_role": "hidden_holdout",
        "instances": [],
    }
    (hidden_pack / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv(PRIVATE_DATA_ENV, str(hidden_root))
    pack = load_instance_pack("hidden_holdout_real_v1")
    assert pack.pack_role == "hidden_holdout"
