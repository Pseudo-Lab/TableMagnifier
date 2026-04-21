from table_env_bench.baselines import RandomAgent, run_episode
from table_env_bench.data.generators import list_families, list_levels
from table_env_bench.env.environment import WorkbookEnv


def test_random_baseline_can_run_registered_family_levels_end_to_end() -> None:
    assert list_families() == sorted(
        [
            "inventory_exception_disambiguation",
            "channel_policy_transfer",
            "report_scope_reconciliation",
        ]
    )
    for family in list_families():
        for level in list_levels(family):
            env = WorkbookEnv(family=family, level=level, seed=0)
            result = run_episode(env, RandomAgent(seed=7))
            assert result.terminated
