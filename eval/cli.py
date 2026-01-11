"""
CLI for Table QA evaluation.

Usage:
    # 데이터셋 준비
    python -m eval.cli prepare ./data/qa_output --output ./eval_data.jsonl

    # vLLM 서버로 평가
    python -m eval.cli run ./data/qa_output --provider vllm --base-url http://localhost:8000/v1

    # OpenAI API로 평가
    python -m eval.cli run ./data/qa_output --provider openai --model gpt-4o-mini

    # 기존 예측 결과 평가
    python -m eval.cli evaluate ./predictions.json --output ./report.json
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from .dataset import create_eval_dataset, load_qa_from_folder
from .evaluate import run_evaluation, evaluate_from_file


def setup_logging(verbose: bool = False):
    """로깅 설정"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def cmd_prepare(args: argparse.Namespace) -> int:
    """데이터셋 준비 커맨드"""
    source = Path(args.source)
    output = Path(args.output) if args.output else source / "eval_dataset.jsonl"
    format = "jsonl" if output.suffix == ".jsonl" else "json"

    print(f"Preparing evaluation dataset from: {source}")

    dataset = create_eval_dataset(source, output, format=format)

    print(f"\nDataset created: {output}")
    print(f"Total items: {len(dataset)}")
    print(f"Type distribution:")
    for qa_type, count in sorted(dataset.get_type_distribution().items()):
        print(f"  {qa_type}: {count}")

    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """평가 실행 커맨드"""
    source = Path(args.source)
    output_dir = Path(args.output_dir) if args.output_dir else source / "eval_results"

    print(f"Running evaluation on: {source}")
    print(f"Provider: {args.provider}")
    print(f"Output directory: {output_dir}")

    # 클라이언트 설정 구성
    client_kwargs = {}

    if args.provider == "vllm":
        client_kwargs["base_url"] = args.base_url or "http://localhost:8000/v1"
        client_kwargs["model"] = args.model or "default"
    elif args.provider == "openai":
        client_kwargs["model"] = args.model or "gpt-4o-mini"
        if args.api_key:
            client_kwargs["api_key"] = args.api_key
    elif args.provider in ["anthropic", "claude"]:
        client_kwargs["model"] = args.model or "claude-sonnet-4-20250514"
        if args.api_key:
            client_kwargs["api_key"] = args.api_key

    client_kwargs["max_tokens"] = args.max_tokens
    client_kwargs["temperature"] = args.temperature
    client_kwargs["max_concurrent"] = args.max_concurrent

    # 프롬프트 템플릿
    prompt_template = None
    if args.prompt_template:
        prompt_template = Path(args.prompt_template).read_text(encoding="utf-8")

    # 비동기 실행
    async def run():
        return await run_evaluation(
            data_source=source,
            provider=args.provider,
            output_dir=output_dir,
            prompt_template=prompt_template,
            include_images=args.include_images,
            **client_kwargs,
        )

    results, aggregated = asyncio.run(run())

    print(f"\n✅ Evaluation complete!")
    print(f"Results saved to: {output_dir}")

    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    """예측 결과 평가 커맨드"""
    predictions_path = Path(args.predictions)
    ground_truth_path = Path(args.ground_truth) if args.ground_truth else None
    output_path = Path(args.output) if args.output else None

    print(f"Evaluating predictions from: {predictions_path}")

    results, aggregated = evaluate_from_file(
        predictions_path,
        ground_truth_path,
        output_path,
    )

    if output_path:
        print(f"\n✅ Report saved to: {output_path}")

    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """데이터셋 정보 출력 커맨드"""
    source = Path(args.source)

    print(f"Loading dataset from: {source}")

    dataset = load_qa_from_folder(source)

    print(f"\nDataset Information:")
    print(f"  Total QA items: {len(dataset)}")
    print(f"  Source: {dataset.metadata.get('source_folder', 'N/A')}")
    print(f"  Files: {dataset.metadata.get('file_count', 'N/A')}")

    print(f"\nQA Type Distribution:")
    for qa_type, count in sorted(dataset.get_type_distribution().items()):
        pct = count / len(dataset) * 100 if len(dataset) > 0 else 0
        print(f"  {qa_type:<20} {count:>5} ({pct:>5.1f}%)")

    # 샘플 출력
    if args.show_samples and len(dataset) > 0:
        print(f"\nSample QA Items:")
        for i, item in enumerate(dataset[:min(3, len(dataset))]):
            print(f"\n  [{i+1}] ID: {item.id}")
            print(f"      Type: {item.qa_type}")
            print(f"      Q: {item.question[:80]}...")
            print(f"      A: {item.answer[:80]}...")

    return 0


def build_parser() -> argparse.ArgumentParser:
    """CLI 파서 구성"""
    parser = argparse.ArgumentParser(
        description="Table QA Evaluation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # prepare 커맨드
    prepare_parser = subparsers.add_parser(
        "prepare",
        help="Prepare evaluation dataset from QA output files",
    )
    prepare_parser.add_argument(
        "source",
        type=str,
        help="Path to QA output folder or file",
    )
    prepare_parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output file path (default: source/eval_dataset.jsonl)",
    )

    # run 커맨드
    run_parser = subparsers.add_parser(
        "run",
        help="Run full evaluation pipeline (inference + evaluation)",
    )
    run_parser.add_argument(
        "source",
        type=str,
        help="Path to QA output folder",
    )
    run_parser.add_argument(
        "--provider",
        choices=["vllm", "openai", "anthropic", "claude"],
        default="vllm",
        help="Inference provider (default: vllm)",
    )
    run_parser.add_argument(
        "--base-url",
        type=str,
        help="Base URL for vLLM server (default: http://localhost:8000/v1)",
    )
    run_parser.add_argument(
        "--model",
        type=str,
        help="Model name",
    )
    run_parser.add_argument(
        "--api-key",
        type=str,
        help="API key (for OpenAI/Anthropic)",
    )
    run_parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="Max tokens for generation (default: 512)",
    )
    run_parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature (default: 0.0)",
    )
    run_parser.add_argument(
        "--max-concurrent",
        type=int,
        default=10,
        help="Max concurrent requests (default: 10)",
    )
    run_parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory for results",
    )
    run_parser.add_argument(
        "--prompt-template",
        type=str,
        help="Path to prompt template file",
    )
    run_parser.add_argument(
        "--include-images",
        action="store_true",
        help="Include images in prompts (for multimodal models)",
    )

    # evaluate 커맨드
    eval_parser = subparsers.add_parser(
        "evaluate",
        help="Evaluate existing prediction results",
    )
    eval_parser.add_argument(
        "predictions",
        type=str,
        help="Path to predictions file (JSON or JSONL)",
    )
    eval_parser.add_argument(
        "--ground-truth",
        type=str,
        help="Path to ground truth file (if not in predictions)",
    )
    eval_parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output report path",
    )

    # info 커맨드
    info_parser = subparsers.add_parser(
        "info",
        help="Show dataset information",
    )
    info_parser.add_argument(
        "source",
        type=str,
        help="Path to QA output folder",
    )
    info_parser.add_argument(
        "--show-samples",
        action="store_true",
        help="Show sample QA items",
    )

    return parser


def main() -> int:
    """메인 엔트리포인트"""
    parser = build_parser()
    args = parser.parse_args()

    setup_logging(args.verbose)

    if args.command is None:
        parser.print_help()
        return 1

    commands = {
        "prepare": cmd_prepare,
        "run": cmd_run,
        "evaluate": cmd_evaluate,
        "info": cmd_info,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
