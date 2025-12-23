"""Reusable runner utilities for the synthetic table flow."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Iterable, List

from dotenv import load_dotenv

from .flow import TableState, run_synthetic_table_flow


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the common argument parser used by CLI entrypoints."""

    parser = argparse.ArgumentParser(
        description="Generate a synthetic HTML table from a Korean table image using LangGraph.",
    )
    parser.add_argument(
        "image",
        type=Path,
        help="Path to the input table image, HTML file, or folder containing images",
    )
    parser.add_argument(
        "--provider",
        default="openai",
        choices=["openai", "gemini", "gemini_pool", "claude", "vllm"],
        help="LLM provider to use (default: openai). gemini_pool uses API key rotation from apis/gemini_keys.yaml. claude uses ANTHROPIC_API_KEY.",
    )
    parser.add_argument(
        "--config-path",
        type=Path,
        help="Path to gemini_keys.yaml for gemini_pool provider (default: apis/gemini_keys.yaml)",
    )
    parser.add_argument(
        "--base-url",
        help="Custom Base URL for vLLM or OpenAI-compatible endpoints",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="Model name to use (default: gpt-4o-mini)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Sampling temperature for the model (default: 0.2)",
    )
    parser.add_argument(
        "--save-json",
        type=Path,
        help="Optional path to save the parsed result as JSON (HTML saved separately)",
    )
    parser.add_argument(
        "--qa-only",
        action="store_true",
        help="Generate QA pairs directly from image without synthetic data generation (faster)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for batch processing results (default: ./output)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=3,
        help="Maximum number of parallel workers for batch processing (default: 3)",
    )
    return parser


def run_flow_for_image(
    image: Path,
    *,
    provider: str = "openai",
    model: str = "gpt-4o-mini",
    temperature: float = 0.2,
    base_url: str | None = None,
    config_path: str | None = None,
    qa_only: bool = False,
) -> TableState:
    """Execute the synthetic table flow for a given image path."""

    load_dotenv()

    # Basic env check based on provider
    if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        msg = "OPENAI_API_KEY is not set. Add it to a .env file or your environment."
        raise RuntimeError(msg)
    if provider == "gemini" and not os.getenv("GOOGLE_API_KEY"):
        msg = "GOOGLE_API_KEY is not set. Add it to a .env file or your environment."
        raise RuntimeError(msg)
    if provider == "claude" and not os.getenv("ANTHROPIC_API_KEY"):
        msg = "ANTHROPIC_API_KEY is not set. Add it to a .env file or your environment."
        raise RuntimeError(msg)
    # gemini_pool은 apis/gemini_keys.yaml에서 키를 로드하므로 환경변수 체크 불필요

    return run_synthetic_table_flow(
        str(image),
        provider=provider,
        model=model,
        temperature=temperature,
        base_url=base_url,
        config_path=config_path,
        qa_only=qa_only,
    )


def _write_html(path: Path, content: str | None) -> Path | None:
    """Persist HTML content to disk if available."""

    if content is None:
        return None

    path.write_text(content, encoding="utf-8")
    return path


def _filter_json_safe_state(state: TableState, *, html_paths: Iterable[tuple[str, Path | None]]) -> Dict:
    """Remove large HTML payloads from JSON output and include file references."""

    payload: Dict[str, object] = {
        "image_path": state.get("image_path"),
        "table_summary": state.get("table_summary"),
        "reflection": state.get("reflection"),
        "errors": state.get("errors"),
        "synthetic_json": state.get("synthetic_json"),
    }

    for label, path in html_paths:
        if path:
            payload[label] = str(path)

    return payload


def run_with_args(args: argparse.Namespace) -> TableState | Dict:
    """Run the flow using parsed CLI arguments and handle optional persistence."""

    input_path = args.image

    # Check if input is a folder -> batch processing
    if input_path.is_dir():
        return run_batch_for_folder(
            input_path,
            provider=args.provider,
            model=args.model,
            temperature=args.temperature,
            base_url=args.base_url,
            config_path=str(args.config_path) if args.config_path else None,
            qa_only=getattr(args, 'qa_only', False),
            output_dir=getattr(args, 'output_dir', None),
            max_workers=getattr(args, 'max_workers', 3),
        )

    # Single file processing
    result = run_flow_for_image(
        input_path,
        provider=args.provider,
        model=args.model,
        temperature=args.temperature,
        base_url=args.base_url,
        config_path=str(args.config_path) if args.config_path else None,
        qa_only=getattr(args, 'qa_only', False),
    )

    html_refs: list[tuple[str, Path | None]] = []
    if args.save_json:
        base = args.save_json.with_suffix("")
        parsed_html_path = base.with_name(base.name + "_parsed.html")
        synthetic_html_path = base.with_name(base.name + "_synthetic.html")
        synthetic_json_path = base.with_name(base.name + "_synthetic.json")


        html_refs.append(("html_table_path", _write_html(parsed_html_path, result.get("html_table"))))
        html_refs.append(("synthetic_table_path", _write_html(synthetic_html_path, result.get("synthetic_table"))))

        payload = _filter_json_safe_state(result, html_paths=html_refs)
        args.save_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ Saved parsed JSON to {args.save_json}")

        if result.get("synthetic_json"):
             synthetic_json_path.write_text(json.dumps(result["synthetic_json"], ensure_ascii=False, indent=2), encoding="utf-8")
             print(f"✅ Saved synthetic JSON to {synthetic_json_path}")

        for label, path in html_refs:
            if path:
                print(f"📄 Saved {label} to {path}")
    else:
        payload = _filter_json_safe_state(result, html_paths=[])
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    return result


def run_batch_for_folder(
    folder: Path,
    *,
    provider: str = "openai",
    model: str = "gpt-4o-mini",
    temperature: float = 0.2,
    base_url: str | None = None,
    config_path: str | None = None,
    qa_only: bool = False,
    output_dir: Path | None = None,
    max_workers: int = 3,
) -> Dict[str, any]:
    """
    Execute the flow for all images in a folder (batch processing).

    Args:
        folder: Path to folder containing images
        provider: LLM provider
        model: Model name
        temperature: Sampling temperature
        base_url: Custom base URL
        config_path: Config path for gemini_pool
        qa_only: Generate QA only without synthetic data
        output_dir: Output directory for results
        max_workers: Number of parallel workers

    Returns:
        Summary dict with results and statistics
    """
    load_dotenv()

    # Find all image files
    image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    image_files = sorted([
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in image_extensions
    ])

    if not image_files:
        print(f"No image files found in {folder}")
        return {"total": 0, "success": 0, "failed": 0, "results": []}

    # Setup output directory
    if output_dir is None:
        output_dir = folder / "qa_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Found {len(image_files)} images in {folder}")
    print(f"Output directory: {output_dir}")
    print(f"Using {max_workers} parallel workers")
    print()

    results = []
    success_count = 0
    failed_count = 0

    def process_single(image_path: Path) -> Dict:
        """Process a single image and return result."""
        try:
            result = run_synthetic_table_flow(
                str(image_path),
                provider=provider,
                model=model,
                temperature=temperature,
                base_url=base_url,
                config_path=config_path,
                qa_only=qa_only,
            )

            # Save individual result
            output_file = output_dir / f"{image_path.stem}_qa.json"
            output_data = {
                "image_path": str(image_path),
                "image_name": image_path.name,
                "qa_results": result.get("qa_results", []),
                "errors": result.get("errors", []),
            }

            if not qa_only:
                output_data["synthetic_json"] = result.get("synthetic_json")

            output_file.write_text(
                json.dumps(output_data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            return {
                "image": image_path.name,
                "status": "success" if not result.get("errors") else "partial",
                "qa_count": len(result.get("qa_results", [])),
                "output_file": str(output_file),
                "errors": result.get("errors", []),
            }

        except Exception as e:
            return {
                "image": image_path.name,
                "status": "failed",
                "qa_count": 0,
                "error": str(e),
            }

    # Parallel processing with ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_image = {
            executor.submit(process_single, img): img
            for img in image_files
        }

        for future in as_completed(future_to_image):
            image_path = future_to_image[future]
            try:
                result = future.result()
                results.append(result)

                if result["status"] == "success":
                    success_count += 1
                    print(f"✅ {result['image']} - {result['qa_count']} QA pairs")
                elif result["status"] == "partial":
                    success_count += 1
                    print(f"⚠️ {result['image']} - {result['qa_count']} QA pairs (with errors)")
                else:
                    failed_count += 1
                    print(f"❌ {result['image']} - {result.get('error', 'Unknown error')}")

            except Exception as e:
                failed_count += 1
                print(f"❌ {image_path.name} - {e}")
                results.append({
                    "image": image_path.name,
                    "status": "failed",
                    "error": str(e),
                })

    # Save summary
    summary = {
        "folder": str(folder),
        "total": len(image_files),
        "success": success_count,
        "failed": failed_count,
        "qa_only": qa_only,
        "provider": provider,
        "model": model,
        "results": results,
    }

    summary_file = output_dir / "_summary.json"
    summary_file.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print()
    print(f"{'='*50}")
    print(f"Batch processing complete!")
    print(f"Total: {len(image_files)}, Success: {success_count}, Failed: {failed_count}")
    print(f"Summary saved to: {summary_file}")

    return summary


__all__ = ["build_arg_parser", "run_flow_for_image", "run_with_args", "run_batch_for_folder"]
