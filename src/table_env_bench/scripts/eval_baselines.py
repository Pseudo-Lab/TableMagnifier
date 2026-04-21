"""Run a small benchmark sweep for the included baselines."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from table_env_bench.baselines import (
    GreedySubmitAgent,
    HeuristicAgent,
    NoNoteAgent,
    RandomAgent,
    SinglePageAgent,
    TextScrapeHeuristicAgent,
    run_episode,
)
from table_env_bench.data.generators import benchmark_suite_manifest, benchmark_suite_records, load_instance
from table_env_bench.env.environment import WorkbookEnv
from table_env_bench.eval.benchmark_metrics import generalization_score, raw_accuracy, slice_breakdown


def _build_agent(name: str):
    if name == "single_page":
        return SinglePageAgent()
    if name == "no_note":
        return NoNoteAgent()
    if name == "text_scrape":
        return TextScrapeHeuristicAgent()
    if name == "greedy_submit":
        return GreedySubmitAgent()
    if name == "heuristic":
        return HeuristicAgent()
    return RandomAgent(seed=11)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate included baselines on benchmark suites.")
    parser.add_argument("--output", default="artifacts/baseline_results.json")
    parser.add_argument("--suite", choices=sorted(benchmark_suite_manifest()), default="public_dev_real_v1")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, object]] = []
    for agent_name in ("random", "heuristic", "single_page", "no_note", "text_scrape", "greedy_submit"):
        for benchmark_record in benchmark_suite_records(suite=args.suite):
            family = str(benchmark_record["family"])
            level = int(benchmark_record["level"])
            seed = int(benchmark_record["seed"])
            template_id = str(benchmark_record["template_id"])
            instance_id = benchmark_record.get("instance_id")
            pack_id = benchmark_record.get("pack_id")
            if instance_id is not None:
                env = WorkbookEnv(episode_spec=load_instance(str(instance_id)))
                replay_name = f"{agent_name}_{pack_id}_{instance_id}.json"
            else:
                env = WorkbookEnv(family=family, level=level, seed=seed, template_id=template_id)
                replay_name = f"{agent_name}_{family}_{template_id}_l{level}_s{seed}.json"
            replay_path = output_path.parent / "replays" / replay_name
            result = run_episode(env, _build_agent(agent_name), replay_path=str(replay_path))
            records.append(
                {
                    "agent": agent_name,
                    "suite": args.suite,
                    "family": family,
                    "level": level,
                    "seed": seed,
                    "template_id": template_id,
                    "instance_id": instance_id,
                    "pack_id": pack_id,
                    **result.to_dict(),
                }
            )

    summary: dict[str, dict[str, float]] = {}
    for agent_name in ("random", "heuristic"):
        agent_records = [record for record in records if record["agent"] == agent_name]
        correctness = sum(record["evaluation"]["correctness"]["value"] for record in agent_records) / len(agent_records)
        efficiency = sum(record["evaluation"]["efficiency"]["value"] for record in agent_records) / len(agent_records)
        overall = sum(record["evaluation"]["overall"] for record in agent_records) / len(agent_records)
        summary[agent_name] = {
            "raw_accuracy": raw_accuracy(agent_records),
            "generalization_score": generalization_score(agent_records),
            "correctness": correctness,
            "efficiency": efficiency,
            "overall": overall,
        }

    payload = {"records": records, "summary": summary, "slice_breakdown": slice_breakdown(records)}
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(records)} episode results to {output_path}")


if __name__ == "__main__":
    main()
