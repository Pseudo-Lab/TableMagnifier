"""Run the FastAPI server for the local web UI."""

from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the table-env-bench FastAPI server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    reload_dirs = [str(Path(__file__).resolve().parents[1])] if args.reload else None
    uvicorn.run(
        "table_env_bench.server.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        reload_dirs=reload_dirs,
    )


if __name__ == "__main__":
    main()
