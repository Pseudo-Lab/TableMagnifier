from table_env_bench.baselines import NoNoteAgent, SinglePageAgent, TextScrapeHeuristicAgent, run_episode
from table_env_bench.data.generators import benchmark_suite_manifest, benchmark_suite_records, eval_hard_episode_catalog, generate_episode
from table_env_bench.env.environment import WorkbookEnv


def test_eval_hard_catalog_and_suite_manifest_match_expected_counts() -> None:
    manifest = benchmark_suite_manifest()
    assert len(manifest["canonical_dev"]) == 12
    assert len(manifest["eval_hard_dev"]) == 4
    assert len(manifest["eval_hard_holdout"]) == 4

    hard_catalog = eval_hard_episode_catalog()
    assert len(hard_catalog) == 64
    assert len(benchmark_suite_records(suite="eval_hard_dev")) == 32
    assert len(benchmark_suite_records(suite="eval_hard_holdout")) == 32
    assert all(record["difficulty_tier"] == "eval_hard" for record in hard_catalog)


def test_eval_hard_paired_variants_have_different_answers_and_required_metadata() -> None:
    for family in ("report_scope_reconciliation", "channel_policy_transfer"):
        for level in (2, 3):
            base = generate_episode(family, level, seed=0, template_id=f"evalhard_l{level}_base")
            counterfactual = generate_episode(family, level, seed=0, template_id=f"evalhard_l{level}_counterfactual")
            assert base.metadata["difficulty_tier"] == "eval_hard"
            assert counterfactual.metadata["difficulty_tier"] == "eval_hard"
            assert len(base.metadata["required_actions"]) >= 1
            assert len(base.metadata["required_evidence"]) >= 2
            assert base.metadata["expected_min_steps"] >= 4
            assert base.metadata["holdout_group"] == counterfactual.metadata["holdout_group"]
            assert base.metadata["pair_group"] == counterfactual.metadata["pair_group"]
            assert base.answer.canonical != counterfactual.answer.canonical


def test_eval_hard_replay_marks_premature_submit_when_required_evidence_is_missed() -> None:
    env = WorkbookEnv(family="report_scope_reconciliation", level=2, seed=0, template_id="evalhard_l2_base")
    env.reset()
    env.step({"type": "submit_answer", "text": "A"})
    metrics = env.replay.metrics(env.spec.metadata)
    assert metrics["premature_submit"] is True
    assert metrics["evidence_coverage"] < 1.0
    assert metrics["missed_required_evidence"]
    assert metrics["decisive_evidence_before_submit"] is False
    assert metrics["correction_surface_visited"] is False
    assert metrics["workflow_discipline"] < 1.0
    assert metrics["support_surface_compliance"] is False


def test_restricted_baselines_generate_low_coverage_on_eval_hard_episode() -> None:
    for family in ("report_scope_reconciliation", "channel_policy_transfer"):
        for agent in (NoNoteAgent(), SinglePageAgent(), TextScrapeHeuristicAgent()):
            result = run_episode(
                WorkbookEnv(family=family, level=2, seed=0, template_id="evalhard_l2_base"),
                agent,
            )
            assert result.evaluation.navigation_metrics["evidence_coverage"] < 1.0
            assert result.evaluation.navigation_metrics["premature_submit"] is True
            assert result.evaluation.navigation_metrics["decisive_evidence_before_submit"] is False
            assert result.evaluation.overall <= result.evaluation.correctness.value
