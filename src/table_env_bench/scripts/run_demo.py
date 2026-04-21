"""Run a single demo episode with a baseline agent."""

from __future__ import annotations

import argparse
from pathlib import Path

from table_env_bench.baselines import HeuristicAgent, RandomAgent, run_episode
from table_env_bench.data.generators import list_families, load_instance
from table_env_bench.env.environment import WorkbookEnv


def build_agent(name: str):
    if name == "heuristic":
        return HeuristicAgent()
    if name == "random":
        return RandomAgent(seed=7)
    raise ValueError(f"Unknown agent: {name}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a single workbook benchmark demo episode.")
    parser.add_argument("--family", choices=list_families())
    parser.add_argument("--level", type=int)
    parser.add_argument("--instance-id")
    parser.add_argument("--seed", default=0, type=int)
    parser.add_argument("--template-id")
    parser.add_argument("--agent", choices=("heuristic", "random"), default="random")
    parser.add_argument("--replay-dir", default="artifacts/replays")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.instance_id:
        spec = load_instance(args.instance_id)
        env = WorkbookEnv(episode_spec=spec)
        replay_stem = f"{args.instance_id}_{args.agent}.json"
    else:
        if args.family is None or args.level is None:
            raise SystemExit("--family and --level are required when --instance-id is not provided")
        env = WorkbookEnv(family=args.family, level=args.level, seed=args.seed, template_id=args.template_id)
        replay_stem = f"{args.family}_level{args.level}_{args.agent}_seed{args.seed}.json"
    agent = build_agent(args.agent)
    replay_path = Path(args.replay_dir) / replay_stem
    result = run_episode(env, agent, replay_path=str(replay_path))

    print(f"episode_id={result.episode_id}")
    print(f"agent={result.agent_name}")
    print(f"prediction={result.prediction}")
    print(f"terminated={result.terminated} truncated={result.truncated}")
    print(f"correctness={result.evaluation.correctness.value:.3f}")
    print(f"efficiency={result.evaluation.efficiency.value:.3f}")
    print(f"overall={result.evaluation.overall:.3f}")
    print(f"unique_sheets_visited={result.evaluation.unique_sheets_visited}")
    print(f"unique_pages_visited={result.evaluation.unique_pages_visited}")
    print(f"replay_path={result.replay_path}")


if __name__ == "__main__":
    main()
