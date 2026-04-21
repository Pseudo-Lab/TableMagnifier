import json
from collections import Counter
from pathlib import Path

import pytest

from table_env_bench.data.generators import benchmark_suite_manifest, benchmark_suite_records, list_instance_packs, load_instance
from table_env_bench.data.instances import PRIVATE_DATA_ENV, load_instance_pack


def test_public_dev_real_pack_manifest_and_snapshots_are_loadable() -> None:
    pack = load_instance_pack("public_dev_real_v1")

    assert pack.pack_id == "public_dev_real_v1"
    assert pack.benchmark_track == "canonical_real_tableqa"
    assert pack.instance_count == 12
    assert len(pack.instances) == 12

    sample = pack.instances[0]
    spec = load_instance(sample.instance_id)
    assert spec.episode_id == sample.instance_id
    assert spec.metadata["pack_id"] == "public_dev_real_v1"
    assert spec.metadata["instance_id"] == sample.instance_id
    assert spec.metadata["instance_label"] == sample.instance_label
    assert spec.metadata["source_episode_id"] == sample.source_episode_id
    assert spec.metadata["benchmark_track"] == "canonical_real_tableqa"


def test_public_dev_real_suite_records_cover_three_families_and_level_ramp() -> None:
    records = benchmark_suite_records(suite="public_dev_real_v1")
    manifest = benchmark_suite_manifest()

    assert len(manifest["public_dev_real_v1"]) == 12
    assert len(records) == 12
    assert {record["pack_id"] for record in records} == {"public_dev_real_v1"}
    assert len({record["instance_id"] for record in records}) == 12

    family_counts = Counter((str(record["family"]), int(record["level"])) for record in records)
    assert family_counts == {
        ("channel_policy_transfer", 1): 1,
        ("channel_policy_transfer", 2): 2,
        ("channel_policy_transfer", 3): 1,
        ("inventory_exception_disambiguation", 1): 1,
        ("inventory_exception_disambiguation", 2): 2,
        ("inventory_exception_disambiguation", 3): 1,
        ("report_scope_reconciliation", 1): 2,
        ("report_scope_reconciliation", 2): 1,
        ("report_scope_reconciliation", 3): 1,
    }


def test_public_arc_packs_are_registered_and_expose_arc_metadata() -> None:
    manifest = benchmark_suite_manifest()
    assert len(manifest["public_dev_real_v1"]) == 12
    assert len(manifest["public_smoke_real_v1"]) == 3

    pack = load_instance_pack("public_dev_real_v1")
    assert pack.benchmark_track == "canonical_real_tableqa"
    assert pack.pack_role == "public"

    sample = pack.instances[0]
    spec = load_instance(sample.instance_id)
    assert spec.metadata["benchmark_track"] == "canonical_real_tableqa"
    assert spec.metadata["reasoning_archetype"] in {"induce_apply", "compose_apply", "disambiguate_apply"}
    assert spec.metadata["generalization_group"]


def test_list_instance_packs_only_exposes_real_public_packs_from_repo() -> None:
    pack_ids = [pack.pack_id for pack in list_instance_packs()]
    assert pack_ids[:2] == ["public_dev_real_v1", "public_smoke_real_v1"]
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
