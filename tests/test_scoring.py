from table_env_bench.data.models import AnswerSpec
from table_env_bench.eval.scoring import ActionCountEfficiencyScorer, EpisodeEvaluator, ExactMatchScorer


def test_scorers_and_episode_metrics_behave_as_expected() -> None:
    answer = AnswerSpec(canonical="462000000", accepted=("462,000,000원",), normalizer="ko_answer")
    scorer = ExactMatchScorer()
    assert scorer.score("462000000원", answer).value == 1.0
    assert scorer.score("999", answer).value == 0.0

    efficiency = ActionCountEfficiencyScorer()
    assert efficiency.score(action_count=1, max_actions=5).value == 1.0
    assert efficiency.score(action_count=5, max_actions=5).value == 0.0

    evaluation = EpisodeEvaluator().evaluate(
        prediction="462000000원",
        answer=answer,
        action_count=3,
        max_actions=5,
        unique_sheets_visited=2,
        unique_pages_visited=3,
        metadata={
            "family": "marker_position_rule_transfer",
            "navigation": {"sheet_switch_count": 1, "wrong_sheet_visit_count": 0, "revisit_count": 0},
            "coverage": {"answer_form": "count", "operator_tags": ["count"], "cue_tags": ["note_scope"]},
        },
    )
    assert evaluation.correctness.value == 1.0
    assert evaluation.unique_sheets_visited == 2
    assert evaluation.unique_pages_visited == 3
    assert evaluation.navigation_metrics["sheet_switch_count"] == 1
    assert evaluation.coverage_slices["answer_form"] == "count"
    assert evaluation.overall == 0.5
    payload = evaluation.to_dict()
    assert "overall" in payload


def test_episode_evaluator_rewards_decisive_evidence_before_submit() -> None:
    answer = AnswerSpec(canonical="B", accepted=("b",), normalizer="basic")
    evaluation = EpisodeEvaluator().evaluate(
        prediction="B",
        answer=answer,
        action_count=3,
        max_actions=6,
        unique_sheets_visited=3,
        unique_pages_visited=3,
        metadata={
            "family": "marker_position_rule_transfer",
            "navigation": {
                "sheet_switch_count": 2,
                "wrong_sheet_visit_count": 0,
                "revisit_count": 0,
                "evidence_coverage": 1.0,
                "decisive_evidence_before_submit": True,
                "correction_surface_visited": True,
                "workflow_discipline": 1.0,
            },
            "coverage": {"answer_form": "statement_choice", "operator_tags": ["verify_statement"], "cue_tags": ["pattern_marker"]},
        },
    )
    assert evaluation.overall == 0.6
