from __future__ import annotations

import argparse

from table_agi_bench.demo import run_demo
from table_agi_bench.generators.v3_tasks import V3_TASK_FAMILIES


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a deterministic Table-AGI smoke task.")
    parser.add_argument("--task-family", choices=["rule_key_rank", *V3_TASK_FAMILIES], default="rule_key_rank")
    parser.add_argument("--level", type=int, choices=[1, 2, 3], default=2)
    parser.add_argument("--run-dir", default="runs/smoke")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    summary = run_demo(
        seeds=[7],
        run_dir=args.run_dir,
        run_id="smoke",
        task_family=args.task_family,
        level=args.level,
    )
    print(summary)
    print(f"Rendered images, public traces, protected traces, and summary saved under {args.run_dir}/")


if __name__ == "__main__":
    main()
