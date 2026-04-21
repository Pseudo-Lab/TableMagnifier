"""Run the authoring pipeline for a benchmark family."""

from __future__ import annotations

import argparse
import json

from table_env_bench.authoring import LeadAgent, VALID_STAGES, build_target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the benchmark authoring pipeline.")
    parser.add_argument("--family", required=True)
    parser.add_argument("--level", type=int)
    parser.add_argument("--template-id")
    parser.add_argument("--suite")
    parser.add_argument("--stages", nargs="*", choices=sorted(VALID_STAGES))
    parser.add_argument("--seed-samples", nargs="*", type=int, default=[0, 1, 2])
    parser.add_argument("--backend", choices=("local", "openai"), default="local")
    parser.add_argument("--apply", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    target = build_target(
        family=args.family,
        level=args.level,
        template_id=args.template_id,
        suite=args.suite,
        stages=tuple(args.stages) if args.stages else None,
        seed_samples=tuple(args.seed_samples),
    )
    record = LeadAgent().run(target=target, backend=args.backend, apply_changes=args.apply)
    print(json.dumps(record.to_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
