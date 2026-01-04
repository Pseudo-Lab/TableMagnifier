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

try:
    from data_organizer import TableDataOrganizer
except ImportError:
    # Fallback if running from a package context where root is not in path yet
    # Assuming the user runs from root, this should be fine. 
    # But just in case, we can try to add parent to path.
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    from data_organizer import TableDataOrganizer


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
    parser.add_argument(
        "--sampling",
        action="store_true",
        help="Enable random sampling of images per table (for QA generation)",
    )
    parser.add_argument(
        "--min-k",
        type=int,
        default=2,
        help="Minimum number of images to sample per table (default: 2)",
    )
    parser.add_argument(
        "--max-k",
        type=int,
        default=3,
        help="Maximum number of images to sample per table (default: 3)",
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        default=1,
        help="Number of random batches to generate per table (default: 1)",
    )
    parser.add_argument(
        "--domain",
        help="Domain for prompt customization (e.g., 'public'). Auto-detected if input starts with 'P_'.",
    )
    parser.add_argument(
        "--pair-mode",
        action="store_true",
        help="Enable sequential pair processing (0-1, 2-3...) for Public data. Overrides sampling.",
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
    domain: str | None = None,
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
        domain=domain,
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
        "qa_results": state.get("qa_results"),
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
            sampling=getattr(args, 'sampling', False),
            min_k=getattr(args, 'min_k', 2),
            max_k=getattr(args, 'max_k', 3),
            num_samples=getattr(args, 'num_samples', 1),

            domain=args.domain,
            pair_mode=getattr(args, 'pair_mode', False),
        )

    # Single file processing
    # Auto-detect domain if not provided
    domain = args.domain
    if not domain and input_path.name.startswith("P_"):
        domain = "public"
        print(f"Auto-detected domain: {domain}")
    elif not domain and input_path.name.startswith("I_"):
        domain = "insurance"
        print(f"Auto-detected domain: {domain}")

    result = run_flow_for_image(
        input_path,
        provider=args.provider,
        model=args.model,
        temperature=args.temperature,
        base_url=args.base_url,
        config_path=str(args.config_path) if args.config_path else None,
        qa_only=getattr(args, 'qa_only', False),
        domain=domain,
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
    sampling: bool = False,
    min_k: int = 2,
    max_k: int = 3,
    num_samples: int = 1,
    domain: str | None = None,
    pair_mode: bool = False,
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

    # Auto-detect domain if not provided
    if not domain and folder.name.startswith("P_"):
        domain = "public"
    elif not domain and folder.name.startswith("I_"):
        domain = "insurance"
        
    print(f"Found {len(image_files)} images in {folder}")
    print(f"Output directory: {output_dir}")
    if domain:
        print(f"Domain: {domain}")
    print(f"Using {max_workers} parallel workers")
    if pair_mode:
        print("Pair Mode: ENABLED (0-1, 2-3...)")
    print()

    # Try to organize data if using Data Organizer naming convention
    organizer = TableDataOrganizer(str(folder))

    # Auto-enable Pair Mode for Public domain if not explicitly requested
    if domain == "public" and not pair_mode:
        print("Auto-enabling Pair Mode for Public domain.")
        pair_mode = True

    grouped_batches = organizer.get_batches(
        sampling=sampling,
        min_k=min_k,
        max_k=max_k,
        num_samples=num_samples,
        pair_mode=pair_mode
    )

    batch_tasks = []

    if grouped_batches:
        print(f"Organized into {len(grouped_batches)} table groups/batches.")
        # Flatten the structure roughly for processing: key -> list of batches
        # get_batches returns { "key": [ [img1, img2], [img3, img4] ] }
        for table_key, batches_list in grouped_batches.items():
            for i, batch_images in enumerate(batches_list):
                 if pair_mode:
                    task_name = f"{table_key}_pair_{i}"
                 elif sampling:
                    task_name = f"{table_key}_sample_{i}"
                 else:
                    task_name = table_key

                 batch_tasks.append({
                     "name": task_name,
                     "images": batch_images
                 })
    else:
        # Fallback to flat list if no pattern matched
         print("No matching table groups found. processing images individually.")
         for img in image_files:
             batch_tasks.append({
                 "name": img.stem,
                 "images": [str(img)]
             })
             
    if not batch_tasks:
         print(f"No tasks created for {folder}")
         return {"total": 0, "success": 0, "failed": 0, "results": []}

    print(f"Created {len(batch_tasks)} tasks.")

    results = []
    success_count = 0
    failed_count = 0

    def process_task(task: Dict) -> Dict:
        """Process a task (single image or batch)."""
        images = task["images"]
        name = task["name"]
        
        # Primary image is the first one for naming/path purposes if needed
        primary_image_path = Path(images[0])
        
        try:
            result = run_synthetic_table_flow(
                image_path=str(primary_image_path), # Pass first image as primary "path" (legacy)
                image_paths=images,                 # Pass all images
                provider=provider,
                model=model,
                temperature=temperature,
                base_url=base_url,
                config_path=config_path,
                qa_only=qa_only,
                domain=domain,
            )

            # Save individual result
            output_file = output_dir / f"{name}_qa.json"
            output_data = {
                "name": name,
                "image_paths": images,
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
                "name": name,
                "status": "success" if not result.get("errors") else "partial",
                "qa_count": len(result.get("qa_results", [])),
                "output_file": str(output_file),
                "errors": result.get("errors", []),
            }

        except Exception as e:
            return {
                "name": name,
                "status": "failed",
                "qa_count": 0,
                "error": str(e),
            }

    # Parallel processing with ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {
            executor.submit(process_task, task): task
            for task in batch_tasks
        }

        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                result = future.result()
                results.append(result)

                if result["status"] == "success":
                    success_count += 1
                    print(f"✅ {result['name']} - {result['qa_count']} QA pairs")
                elif result["status"] == "partial":
                    success_count += 1
                    print(f"⚠️ {result['name']} - {result['qa_count']} QA pairs (with errors)")
                else:
                    failed_count += 1
                    print(f"❌ {result['name']} - {result.get('error', 'Unknown error')}")

            except Exception as e:
                failed_count += 1
                print(f"❌ {task['name']} - {e}")
                results.append({
                    "name": task['name'],
                    "status": "failed",
                    "error": str(e),
                })
 
    # Save summary
    summary = {
        "folder": str(folder),
        "total": len(batch_tasks),
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
