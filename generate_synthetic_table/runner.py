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

from .flow import (
    TableState,
    run_synthetic_table_flow,
    list_checkpoints,
    get_checkpoint_state,
    delete_checkpoint,
    clear_all_checkpoints,
    resume_from_checkpoint,
)
from .notion_uploader import upload_to_notion

try:
    from data_organizer import TableDataOrganizer
except ImportError:
    # Fallback if running from a package context where root is not in path yet
    # Assuming the user runs from root, this should be fine. 
    # But just in case, we can try to add parent to path.
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    from data_organizer import TableDataOrganizer


# Domain auto-detection mapping: prefix -> domain name
_DOMAIN_PREFIX_MAP = {
    "M_": "medical",
    "P_": "public",
    "I_": "insurance",
    "F_": "finance",
    "A_": "academic",
    "B_": "business",
}


def _auto_detect_domain(name: str) -> str | None:
    """Auto-detect domain from file/folder name prefix."""
    for prefix, domain in _DOMAIN_PREFIX_MAP.items():
        if name.startswith(prefix):
            return domain
    return None


def _save_upload_log(image_path: str) -> None:
    """Save uploaded image path to log file."""
    log_file = Path("tests/choi/upload_fin.txt")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"{image_path}\n")


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
        choices=["openai", "azure", "gemini", "gemini_pool", "claude", "vllm"],
        help="LLM provider to use (default: openai). azure uses Azure OpenAI. gemini_pool uses API key rotation from apis/gemini_keys.yaml. claude uses ANTHROPIC_API_KEY.",
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
        "--azure-deployment",
        help="Azure OpenAI deployment name (required for azure provider)",
    )
    parser.add_argument(
        "--azure-endpoint",
        help="Azure OpenAI endpoint URL (required for azure provider)",
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

    # 체크포인팅 옵션
    checkpoint_group = parser.add_argument_group("Checkpointing Options")
    checkpoint_group.add_argument(
        "--checkpoint",
        action="store_true",
        help="Enable checkpointing for resumable execution",
    )
    checkpoint_group.add_argument(
        "--checkpoint-dir",
        type=Path,
        help="Directory to store checkpoint files (default: ./checkpoints)",
    )
    checkpoint_group.add_argument(
        "--thread-id",
        help="Custom thread ID for checkpoint (auto-generated from image path if not provided)",
    )
    checkpoint_group.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing checkpoint if available",
    )

    # 체크포인트 관리 서브커맨드
    checkpoint_group.add_argument(
        "--list-checkpoints",
        action="store_true",
        help="List all saved checkpoints and exit",
    )
    checkpoint_group.add_argument(
        "--show-checkpoint",
        metavar="THREAD_ID",
        help="Show details of a specific checkpoint and exit",
    )
    checkpoint_group.add_argument(
        "--delete-checkpoint",
        metavar="THREAD_ID",
        help="Delete a specific checkpoint and exit",
    )
    checkpoint_group.add_argument(
        "--clear-checkpoints",
        action="store_true",
        help="Delete all checkpoints and exit",
    )
    checkpoint_group.add_argument(
        "--resume-checkpoint",
        metavar="THREAD_ID",
        help="Resume execution from a specific checkpoint thread ID",
    )

    parser.add_argument(
        "--upload-notion",
        action="store_true",
        help="Upload QA results to Notion database (requires domain to be specified)",
    )
    parser.add_argument(
        "--notion-config",
        type=Path,
        help="Path to config file with Notion API key and database IDs (default: apis/gemini_keys.yaml)",
    )
    parser.add_argument(
        "--upload-log",
        action="store_true",
        help="Save uploaded image paths to tests/choi/upload_fin.txt for tracking",
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
    azure_deployment: str | None = None,
    azure_endpoint: str | None = None,
    qa_only: bool = False,
    domain: str | None = None,
    # 체크포인팅 옵션
    enable_checkpointing: bool = False,
    thread_id: str | None = None,
    checkpoint_dir: str | None = None,
    resume: bool = False,
) -> TableState:
    """Execute the synthetic table flow for a given image path.

    Args:
        image: Path to the input image or HTML file
        provider: LLM provider
        model: Model name
        temperature: Sampling temperature
        base_url: Custom base URL
        config_path: Config path for gemini_pool
        azure_deployment: Azure OpenAI deployment name
        azure_endpoint: Azure OpenAI endpoint URL
        qa_only: Generate QA only without synthetic data
        domain: Domain for prompt customization
        enable_checkpointing: Enable checkpointing for resumable execution
        thread_id: Custom thread ID for checkpoint
        checkpoint_dir: Directory to store checkpoint files
        resume: Resume from existing checkpoint if available

    Returns:
        Final TableState with results
    """

    load_dotenv()

    # Basic env check based on provider
    if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        msg = "OPENAI_API_KEY is not set. Add it to a .env file or your environment."
        raise RuntimeError(msg)
    # azure는 yaml 파일에서도 읽을 수 있으므로 여기서 체크하지 않음 (get_llm에서 체크)
    if provider == "gemini" and not os.getenv("GOOGLE_API_KEY"):
        msg = "GOOGLE_API_KEY is not set. Add it to a .env file or your environment."
        raise RuntimeError(msg)
    if provider == "claude" and not os.getenv("ANTHROPIC_API_KEY"):
        msg = "ANTHROPIC_API_KEY is not set. Add it to a .env file or your environment."
        raise RuntimeError(msg)
    # gemini_pool과 azure는 apis/gemini_keys.yaml에서 키를 로드하므로 환경변수 체크 불필요

    return run_synthetic_table_flow(
        str(image),
        provider=provider,
        model=model,
        temperature=temperature,
        base_url=base_url,
        config_path=config_path,
        azure_deployment=azure_deployment,
        azure_endpoint=azure_endpoint,
        qa_only=qa_only,
        domain=domain,
        enable_checkpointing=enable_checkpointing,
        thread_id=thread_id,
        checkpoint_dir=checkpoint_dir,
        resume=resume,
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


def run_with_args(args: argparse.Namespace) -> TableState | Dict | None:
    """Run the flow using parsed CLI arguments and handle optional persistence."""

    # 체크포인트 디렉토리 설정
    checkpoint_dir = str(args.checkpoint_dir) if getattr(args, 'checkpoint_dir', None) else None

    # ========================================
    # 체크포인트 관리 명령 처리
    # ========================================

    # --list-checkpoints: 모든 체크포인트 목록 출력
    if getattr(args, 'list_checkpoints', False):
        checkpoints = list_checkpoints(checkpoint_dir)
        if not checkpoints:
            print("No checkpoints found.")
        else:
            print(f"Found {len(checkpoints)} checkpoint(s):\n")
            print(f"{'Thread ID':<12} {'Created At':<25} {'Parent ID':<12}")
            print("-" * 50)
            for cp in checkpoints:
                print(f"{cp['thread_id']:<12} {cp['created_at'] or 'N/A':<25} {cp['parent_id'] or 'N/A':<12}")
        return None

    # --show-checkpoint: 특정 체크포인트 상세 정보
    if getattr(args, 'show_checkpoint', None):
        thread_id = args.show_checkpoint
        state = get_checkpoint_state(thread_id, checkpoint_dir)
        if state:
            print(f"Checkpoint: {thread_id}\n")
            print(f"Image Path: {state.get('image_path', 'N/A')}")
            print(f"Attempts: {state.get('attempts', 0)}")
            print(f"Passed: {state.get('passed', 'N/A')}")
            print(f"Errors: {state.get('errors', [])}")
            print(f"\nHas HTML Table: {bool(state.get('html_table'))}")
            print(f"Has Synthetic Table: {bool(state.get('synthetic_table'))}")
            print(f"Has QA Results: {bool(state.get('qa_results'))}")
            if state.get('qa_results'):
                print(f"QA Count: {len(state.get('qa_results', []))}")
        else:
            print(f"Checkpoint not found: {thread_id}")
        return None

    # --delete-checkpoint: 특정 체크포인트 삭제
    if getattr(args, 'delete_checkpoint', None):
        thread_id = args.delete_checkpoint
        if delete_checkpoint(thread_id, checkpoint_dir):
            print(f"✅ Deleted checkpoint: {thread_id}")
        else:
            print(f"❌ Failed to delete checkpoint: {thread_id}")
        return None

    # --clear-checkpoints: 모든 체크포인트 삭제
    if getattr(args, 'clear_checkpoints', False):
        count = clear_all_checkpoints(checkpoint_dir)
        print(f"✅ Cleared {count} checkpoint(s)")
        return None

    # --resume-checkpoint: 특정 체크포인트에서 재개
    if getattr(args, 'resume_checkpoint', None):
        thread_id = args.resume_checkpoint
        print(f"Resuming from checkpoint: {thread_id}")
        result = resume_from_checkpoint(
            thread_id,
            provider=args.provider,
            model=args.model,
            temperature=args.temperature,
            base_url=args.base_url,
            config_path=str(args.config_path) if args.config_path else None,
            qa_only=getattr(args, 'qa_only', False),
            checkpoint_dir=checkpoint_dir,
        )
        if result:
            print(f"✅ Resumed and completed execution")
            payload = _filter_json_safe_state(result, html_paths=[])
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return result
        else:
            print(f"❌ Failed to resume from checkpoint: {thread_id}")
            return None

    # ========================================
    # 일반 실행 흐름
    # ========================================

    input_path = args.image

    # 체크포인팅 옵션 추출
    enable_checkpointing = getattr(args, 'checkpoint', False)
    thread_id = getattr(args, 'thread_id', None)
    resume = getattr(args, 'resume', False)

    # Check if input is a folder -> batch processing
    if input_path.is_dir():
        return run_batch_for_folder(
            input_path,
            provider=args.provider,
            model=args.model,
            temperature=args.temperature,
            base_url=args.base_url,
            config_path=str(args.config_path) if args.config_path else None,
            azure_deployment=getattr(args, 'azure_deployment', None),
            azure_endpoint=getattr(args, 'azure_endpoint', None),
            qa_only=getattr(args, 'qa_only', False),
            output_dir=getattr(args, 'output_dir', None),
            max_workers=getattr(args, 'max_workers', 3),
            sampling=getattr(args, 'sampling', False),
            min_k=getattr(args, 'min_k', 2),
            max_k=getattr(args, 'max_k', 3),
            num_samples=getattr(args, 'num_samples', 1),
            domain=args.domain,
            pair_mode=getattr(args, 'pair_mode', False),
            # 체크포인팅 옵션
            enable_checkpointing=enable_checkpointing,
            checkpoint_dir=checkpoint_dir,
            upload_notion=getattr(args, 'upload_notion', False),
            notion_config=str(args.notion_config) if getattr(args, 'notion_config', None) else None,
            upload_log=getattr(args, 'upload_log', False),
        )

    # Single file processing
    # Auto-detect domain if not provided
    domain = args.domain
    if not domain:
        domain = _auto_detect_domain(input_path.name)
        if domain:
            print(f"Auto-detected domain: {domain}")

    # 체크포인팅 활성화 시 메시지 출력
    if enable_checkpointing:
        print(f"🔄 Checkpointing enabled" + (f" (thread_id: {thread_id})" if thread_id else ""))
        if resume:
            print(f"   Resume mode: ON")

    result = run_flow_for_image(
        input_path,
        provider=args.provider,
        model=args.model,
        temperature=args.temperature,
        base_url=args.base_url,
        config_path=str(args.config_path) if args.config_path else None,
        azure_deployment=getattr(args, 'azure_deployment', None),
        azure_endpoint=getattr(args, 'azure_endpoint', None),
        qa_only=getattr(args, 'qa_only', False),
        domain=domain,
        # 체크포인팅 옵션
        enable_checkpointing=enable_checkpointing,
        thread_id=thread_id,
        checkpoint_dir=checkpoint_dir,
        resume=resume,
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

    # Upload to Notion if requested (single file)
    if getattr(args, 'upload_notion', False):
        if not domain:
            print("\n⚠️  --upload-notion requires --domain to be specified. Skipping upload.")
        else:
            qa_results = result.get("qa_results", [])
            if qa_results:
                print(f"\n{'='*50}")
                print(f"Uploading to Notion (domain: {domain})...")
                try:
                    notion_results = [{
                        "image_path": str(input_path),
                        "qa_results": qa_results,
                        "table_summary": result.get("table_summary"),
                        "token_usage": result.get("token_usage", 0),
                    }]
                    notion_config = str(args.notion_config) if getattr(args, 'notion_config', None) else None
                    upload_summary = upload_to_notion(
                        domain=domain,
                        results=notion_results,
                        config_path=notion_config,
                        verbose=True,
                        provider=args.provider,
                    )
                    print(f"\n✅ Notion upload complete: {upload_summary['success']}/{upload_summary['total']} succeeded")
                    
                    # Save uploaded image path to log file if requested
                    if getattr(args, 'upload_log', False) and upload_summary['success'] > 0:
                        _save_upload_log(str(input_path))
                        
                except ImportError as e:
                    print(f"\n❌ Notion upload failed: {e}")
                    print("   Install with: pip install notion-client")
                except Exception as e:
                    print(f"\n❌ Notion upload failed: {e}")
            else:
                print("\n⚠️  No QA results to upload.")

    return result


def run_batch_for_folder(
    folder: Path,
    *,
    provider: str = "openai",
    model: str = "gpt-4o-mini",
    temperature: float = 0.2,
    base_url: str | None = None,
    config_path: str | None = None,
    azure_deployment: str | None = None,
    azure_endpoint: str | None = None,
    qa_only: bool = False,
    output_dir: Path | None = None,
    max_workers: int = 3,
    sampling: bool = False,
    min_k: int = 2,
    max_k: int = 3,
    num_samples: int = 1,
    domain: str | None = None,
    pair_mode: bool = False,
    # 체크포인팅 옵션
    enable_checkpointing: bool = False,
    checkpoint_dir: str | None = None,
    upload_notion: bool = False,
    notion_config: str | None = None,
    upload_log: bool = False,
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
        azure_deployment: Azure OpenAI deployment name
        azure_endpoint: Azure OpenAI endpoint URL
        qa_only: Generate QA only without synthetic data
        output_dir: Output directory for results
        max_workers: Number of parallel workers
        sampling: Enable random sampling
        min_k: Minimum images per sample
        max_k: Maximum images per sample
        num_samples: Number of samples per table
        domain: Domain for prompt customization
        pair_mode: Enable pair processing mode
        enable_checkpointing: Enable checkpointing for each task
        checkpoint_dir: Directory to store checkpoint files

    Returns:
        Summary dict with results and statistics
    """
    load_dotenv()

    # Find all image files (recursive)
    image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    image_files = sorted([
        f for f in folder.rglob("*")
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
    if not domain:
        domain = _auto_detect_domain(folder.name)
        
    print(f"Found {len(image_files)} images in {folder}")
    print(f"Output directory: {output_dir}")
    if domain:
        print(f"Domain: {domain}")
    print(f"Using {max_workers} parallel workers")
    if pair_mode:
        print("Pair Mode: ENABLED (0-1, 2-3...)")
    if enable_checkpointing:
        print(f"🔄 Checkpointing: ENABLED (dir: {checkpoint_dir or 'default'})")
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

        # 배치 처리에서는 task name을 thread_id로 사용
        task_thread_id = name if enable_checkpointing else None

        try:
            result = run_synthetic_table_flow(
                image_path=str(primary_image_path), # Pass first image as primary "path" (legacy)
                image_paths=images,                 # Pass all images
                provider=provider,
                model=model,
                temperature=temperature,
                base_url=base_url,
                config_path=config_path,
                azure_deployment=azure_deployment,
                azure_endpoint=azure_endpoint,
                qa_only=qa_only,
                domain=domain,
                # 체크포인팅 옵션
                enable_checkpointing=enable_checkpointing,
                thread_id=task_thread_id,
                checkpoint_dir=checkpoint_dir,
                resume=True,  # 배치에서는 항상 resume 시도
            )

            # Save individual result
            output_file = output_dir / f"{name}_qa.json"
            output_data = {
                "name": name,
                "image_paths": images,
                "qa_results": result.get("qa_results", []),
                "token_usage": result.get("token_usage", 0),
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
                "token_usage": result.get("token_usage", 0),
                "errors": result.get("errors", []),
            }

        except Exception as e:
            return {
                "name": name,
                "status": "failed",
                "qa_count": 0,
                "error": str(e),
            }

    # Initialize Notion uploader if needed
    notion_uploader = None
    notion_upload_success = 0
    notion_upload_failed = 0
    
    if upload_notion:
        if not domain:
            print("⚠️  --upload-notion requires --domain to be specified. Notion upload disabled.")
            upload_notion = False
        else:
            try:
                from .notion_uploader import NotionUploader
                notion_uploader = NotionUploader(config_path=notion_config)
                print(f"📤 Notion upload enabled (domain: {domain})")
            except ImportError as e:
                print(f"⚠️  Notion upload disabled: {e}")
                print("   Install with: pip install notion-client")
                upload_notion = False
            except Exception as e:
                print(f"⚠️  Notion upload disabled: {e}")
                upload_notion = False

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
                    
                    # Upload to Notion immediately after QA generation
                    if upload_notion and notion_uploader and result.get("output_file"):
                        try:
                            output_file = Path(result["output_file"])
                            if output_file.exists():
                                data = json.loads(output_file.read_text(encoding="utf-8"))
                                qa_results = data.get("qa_results", [])
                                if qa_results:
                                    # Use token_usage from result (already available)
                                    token_usage = result.get("token_usage", 0)
                                    upload_result = notion_uploader.upload_qa_result(
                                        domain=domain,
                                        image_path=data.get("name", result["name"]),
                                        qa_results=qa_results,
                                        table_summary=data.get("table_summary"),
                                        token_usage=token_usage,
                                        provider=provider,
                                    )
                                    notion_upload_success += 1
                                    print(f"   📤 Uploaded to Notion: {upload_result.get('created_count', 0)} rows (tokens: {token_usage})")
                                    
                                    # Save to upload log if requested
                                    if upload_log:
                                        image_paths = data.get("image_paths", [])
                                        for img_path in image_paths:
                                            _save_upload_log(img_path)
                        except Exception as e:
                            notion_upload_failed += 1
                            print(f"   ⚠️ Notion upload failed: {e}")
                    
                elif result["status"] == "partial":
                    success_count += 1
                    print(f"⚠️ {result['name']} - {result['qa_count']} QA pairs (with errors)")
                    
                    # Upload partial results to Notion
                    if upload_notion and notion_uploader and result.get("output_file"):
                        try:
                            output_file = Path(result["output_file"])
                            if output_file.exists():
                                data = json.loads(output_file.read_text(encoding="utf-8"))
                                qa_results = data.get("qa_results", [])
                                if qa_results:
                                    # Use token_usage from result
                                    token_usage = result.get("token_usage", 0)
                                    upload_result = notion_uploader.upload_qa_result(
                                        domain=domain,
                                        image_path=data.get("name", result["name"]),
                                        qa_results=qa_results,
                                        table_summary=data.get("table_summary"),
                                        token_usage=token_usage,
                                        provider=provider,
                                    )
                                    notion_upload_success += 1
                                    print(f"   📤 Uploaded to Notion: {upload_result.get('created_count', 0)} rows (tokens: {token_usage})")
                                    
                                    # Save to upload log if requested
                                    if upload_log:
                                        image_paths = data.get("image_paths", [])
                                        for img_path in image_paths:
                                            _save_upload_log(img_path)
                        except Exception as e:
                            notion_upload_failed += 1
                            print(f"   ⚠️ Notion upload failed: {e}")
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
        "checkpointing_enabled": enable_checkpointing,
        "checkpoint_dir": checkpoint_dir,
        "results": results,
    }
    
    # Add Notion upload summary if enabled
    if upload_notion and notion_uploader:
        summary["notion_upload"] = {
            "enabled": True,
            "success": notion_upload_success,
            "failed": notion_upload_failed,
            "total": notion_upload_success + notion_upload_failed,
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
    if upload_notion and notion_uploader:
        print(f"Notion Upload: {notion_upload_success} succeeded, {notion_upload_failed} failed")
    print(f"Summary saved to: {summary_file}")

    return summary


__all__ = ["build_arg_parser", "run_flow_for_image", "run_with_args", "run_batch_for_folder"]
