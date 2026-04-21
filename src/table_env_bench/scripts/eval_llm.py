"""Evaluate tool-calling LLM agents on workbook benchmark suites."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from table_env_bench.baselines import LLMAgent, run_episode
from table_env_bench.baselines.llm_agent import OpenAICompatibleClient
from table_env_bench.data.generators import benchmark_suite_manifest, benchmark_suite_records, load_instance
from table_env_bench.env.environment import WorkbookEnv
from table_env_bench.eval.benchmark_metrics import generalization_score, raw_accuracy, slice_breakdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate a tool-calling LLM on benchmark episodes.")
    parser.add_argument("--output", default="artifacts/llm_results.json")
    parser.add_argument("--suite", choices=sorted(benchmark_suite_manifest()), default="public_dev_real_v1")
    parser.add_argument("--family")
    parser.add_argument("--level", type=int)
    parser.add_argument("--template-id")
    parser.add_argument("--seeds", nargs="*", type=int)
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", default="https://api.openai.com/v1")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--reasoning-effort", default="minimal")
    parser.add_argument("--max-output-tokens", type=int, default=400)
    return parser


def _select_records(args: argparse.Namespace) -> list[dict[str, object]]:
    suite_records = benchmark_suite_records(suite=args.suite)
    selected = suite_records
    if args.family is not None:
        selected = [record for record in selected if record["family"] == args.family]
    if args.level is not None:
        selected = [record for record in selected if record["level"] == args.level]
    if args.template_id is not None:
        selected = [record for record in selected if record["template_id"] == args.template_id]
    if args.seeds:
        selected = [record for record in selected if record["seed"] in set(args.seeds)]
    return selected


def _usage_from_record(record: dict[str, object]) -> dict[str, int]:
    metadata = record.get("run_metadata", {})
    usage = metadata.get("usage", {}) if isinstance(metadata, dict) else {}
    return {
        "input_tokens": int(usage.get("input_tokens", 0) or 0),
        "cached_input_tokens": int(usage.get("cached_input_tokens", 0) or 0),
        "output_tokens": int(usage.get("output_tokens", 0) or 0),
        "reasoning_tokens": int(usage.get("reasoning_tokens", 0) or 0),
        "total_tokens": int(usage.get("total_tokens", 0) or 0),
    }


def _cost_from_record(record: dict[str, object]) -> float | None:
    metadata = record.get("run_metadata", {})
    if not isinstance(metadata, dict):
        return None
    raw_cost = metadata.get("estimated_cost_usd")
    if raw_cost is None:
        return None
    return float(raw_cost)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _build_summary(records: list[dict[str, object]]) -> dict[str, object]:
    count = len(records)
    usage_totals = {
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens": 0,
        "total_tokens": 0,
    }
    priced_costs: list[float] = []
    by_family: dict[str, dict[str, object]] = {}
    for record in records:
        usage = _usage_from_record(record)
        for key, value in usage.items():
            usage_totals[key] += value
        family = str(record["family"])
        family_summary = by_family.setdefault(
            family,
            {
                "count": 0,
                "input_tokens": 0,
                "cached_input_tokens": 0,
                "output_tokens": 0,
                "reasoning_tokens": 0,
                "total_tokens": 0,
                "estimated_cost_usd": 0.0,
                "priced_episode_count": 0,
            },
        )
        family_summary["count"] = int(family_summary["count"]) + 1
        for key, value in usage.items():
            family_summary[key] = int(family_summary[key]) + value
        record_cost = _cost_from_record(record)
        if record_cost is not None:
            priced_costs.append(record_cost)
            family_summary["estimated_cost_usd"] = float(family_summary["estimated_cost_usd"]) + record_cost
            family_summary["priced_episode_count"] = int(family_summary["priced_episode_count"]) + 1
    for family, family_summary in by_family.items():
        family_summary["estimated_cost_usd"] = round(float(family_summary["estimated_cost_usd"]), 8)
    highest_cost_episodes = sorted(
        [
            {
                "episode_id": record["episode_id"],
                "family": record["family"],
                "instance_id": record.get("instance_id"),
                "estimated_cost_usd": _cost_from_record(record),
                "total_tokens": _usage_from_record(record)["total_tokens"],
            }
            for record in records
            if _cost_from_record(record) is not None
        ],
        key=lambda item: float(item["estimated_cost_usd"] or 0.0),
        reverse=True,
    )[:5]
    return {
        "count": count,
        "raw_accuracy": raw_accuracy(records),
        "generalization_score": generalization_score(records),
        "correctness": _mean([float(record["evaluation"]["correctness"]["value"]) for record in records]),
        "efficiency": _mean([float(record["evaluation"]["efficiency"]["value"]) for record in records]),
        "overall": _mean([float(record["evaluation"]["overall"]) for record in records]),
        "usage": usage_totals,
        "average_usage": {
            key: round(value / count, 3) if count else 0.0
            for key, value in usage_totals.items()
        },
        "estimated_cost_usd": round(sum(priced_costs), 8) if priced_costs else None,
        "average_cost_usd": round(sum(priced_costs) / len(priced_costs), 8) if priced_costs else None,
        "by_family": by_family,
        "highest_cost_episodes": highest_cost_episodes,
        "slice_breakdown": slice_breakdown(records),
    }


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    client = OpenAICompatibleClient.from_env(
        model=args.model,
        base_url=args.base_url,
        api_key_env=args.api_key_env,
        reasoning_effort=args.reasoning_effort,
        max_output_tokens=args.max_output_tokens,
    )
    agent = LLMAgent(client=client, name=f"llm:{args.model}")

    records: list[dict[str, object]] = []
    try:
        for benchmark_record in _select_records(args):
            family = str(benchmark_record["family"])
            level = int(benchmark_record["level"])
            seed = int(benchmark_record["seed"])
            template_id = str(benchmark_record["template_id"])
            instance_id = benchmark_record.get("instance_id")
            pack_id = benchmark_record.get("pack_id")
            if instance_id is not None:
                env = WorkbookEnv(episode_spec=load_instance(str(instance_id)))
                replay_name = f"llm_{pack_id}_{instance_id}.json"
            else:
                env = WorkbookEnv(family=family, level=level, seed=seed, template_id=template_id)
                replay_name = f"llm_{family}_{template_id}_l{level}_s{seed}.json"
            replay_path = output_path.parent / "replays" / replay_name
            result = run_episode(env, agent, replay_path=str(replay_path))
            records.append(
                {
                    "agent": agent.name,
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
    finally:
        client.close()

    summary = _build_summary(records)
    payload = {"records": records, "summary": summary}
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(records)} LLM episode results to {output_path}")


if __name__ == "__main__":
    main()
