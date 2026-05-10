from table_env_bench.data.generators import benchmark_suite_manifest, benchmark_suite_records, eval_hard_episode_catalog, generate_episode


def test_removed_eval_hard_suites_are_not_exposed() -> None:
    manifest = benchmark_suite_manifest()
    assert set(manifest) == {"canonical_dev"}
    assert len(manifest["canonical_dev"]) == 6

    assert eval_hard_episode_catalog() == []
    assert len(benchmark_suite_records(suite="canonical_dev")) == 48


def test_removed_eval_hard_templates_are_not_launchable() -> None:
    try:
        generate_episode("k_vis_table_arc", 2, seed=0, template_id="evalhard_l2_base")
    except KeyError as exc:
        assert "Unknown template" in str(exc)
    else:
        raise AssertionError("eval_hard templates should not be launchable after deprecated suite removal")
