import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple

from dotenv import load_dotenv

# Add parent directory to path to allow imports if running from root
sys.path.append(str(Path(__file__).parent))

from generate_synthetic_table.runner import run_synthetic_table_flow, _auto_detect_domain
from generate_synthetic_table.flow import TableState
from generate_synthetic_table.notion_uploader import NotionUploader

def resolve_paths(pair: List[str], data_root: Path) -> List[Path]:
    """Resolves a list of relative paths to absolute Paths."""
    paths = []
    for pid in pair:
        # Prioritize using the path exactly as given in the JSON
        p = Path(pid)
        if p.exists():
            paths.append(p)
            continue
            
        # Fallback: Try joining with data_root if provided (for backward compatibility or convenience)
        p_joined = data_root / pid
        if p_joined.exists():
            paths.append(p_joined)
        else:
            print(f"Warning: File not found: {pid} (checked {p.absolute()} and {p_joined.absolute()})")
            return []
    return paths

def run_pipeline(
    json_input: List[List[str]],
    data_root: Path,
    output_dir: Path,
    provider: str = "gemini_pool",
    model: str = "gemini-2.5-flash",
    config_path: str = "apis/gemini_keys.yaml",
    arg_domain: str = None,
    qa_only: bool = False,
    upload_to_notion: bool = False
):
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize Notion uploader if needed
    notion_uploader = None
    if upload_to_notion:
        try:
            notion_uploader = NotionUploader(config_path=config_path)
            print("✅ Notion uploader initialized")
        except Exception as e:
            print(f"⚠️  Warning: Failed to initialize Notion uploader: {e}")
            print("   Continuing without Notion upload...")
    
    final_results = []

    for i, pair_input in enumerate(json_input):
        # Support both formats:
        # 1. Legacy: ["path1", "path2"]
        # 2. Structured: {"pair_id": "...", "image_paths": [...], "domain": "..."}
        
        if isinstance(pair_input, dict):
            # Structured format
            pair_id_override = pair_input.get("pair_id")
            pair_ids = pair_input.get("image_paths", [])
            domain_override = pair_input.get("domain")
            
            print(f"\nProcessing Pair {i+1}/{len(json_input)}: {pair_id_override or pair_ids}")
        else:
            # Legacy format (array)
            pair_id_override = None
            pair_ids = pair_input
            domain_override = None
            
            print(f"\nProcessing Pair {i+1}/{len(json_input)}: {pair_ids}")
        
        paths = resolve_paths(pair_ids, data_root)
        if len(paths) != len(pair_ids):
            print(f"Skipping pair {pair_ids} due to missing files.")
            final_results.append({
                "pair_id": pair_id_override or f"error_{i}",
                "image_paths": pair_ids,
                "error": "Missing files"
            })
            continue

        # Detect domain: priority order is domain_override > arg_domain > auto_detect
        domain = domain_override or arg_domain
        if not domain:
            domain = _auto_detect_domain(pair_ids[0])
            if not domain: 
                # fallback try second
                domain = _auto_detect_domain(pair_ids[1]) if len(pair_ids) > 1 else None
        
        print(f"Domain: {domain}")
        
        # Generate pair_id from override or common path elements
        if pair_id_override:
            pair_id = pair_id_override
        else:
            pair_id = Path(paths[0]).stem if paths else f"pair_{i}"

        # Store paths as strings
        image_paths_str = [str(p) for p in paths]
        
        # Initialize result structure
        pair_tables = []
        pair_qa = []
        
        # Logic Branching: Use qa_only flag OR domain-based logic
        should_skip_tables = qa_only or (domain == "public")
        
        if should_skip_tables:
            # QA only mode (either forced by flag or public domain)
            print(f"Mode: QA only (tables skipped)")
            
            # QA Generation (Pair)
            qa_state = run_synthetic_table_flow(
                image_path=str(paths[0]),  # Primary path
                image_paths=image_paths_str,
                provider=provider,
                model=model,
                config_path=config_path,
                qa_only=True,
                domain=domain
            )
            
            if qa_state.get("qa_results"):
                pair_qa = qa_state["qa_results"]
            
            # Tables are None when skipped
            pair_tables = [None] * len(paths)
            
        else:
            # Full mode: Individual Tables + Pair QA
            print("Mode: Synthetic Table + QA")
            
            # 1. Generate Tables Individually
            temp_tables = []
            for path in paths:
                print(f"  Generating table for {path.name}...")
                table_state = run_synthetic_table_flow(
                    image_path=str(path),
                    provider=provider,
                    model=model,
                    config_path=config_path,
                    qa_only=False,  # We want the table
                    domain=domain
                )
                
                # Check errors
                if table_state.get("errors"):
                    print(f"    Error generating table: {table_state['errors']}")
                
                # Filter state
                safe_state = {
                    "image_path": str(path),
                    "synthetic_table": table_state.get("synthetic_table"),
                    "synthetic_json": table_state.get("synthetic_json"),
                    "table_summary": table_state.get("table_summary"),
                }
                temp_tables.append(safe_state)
            
            pair_tables = temp_tables

            # 2. Generate QA for the Pair
            print(f"  Generating QA for pair...")
            qa_state = run_synthetic_table_flow(
                image_path=str(paths[0]),
                image_paths=image_paths_str,
                provider=provider,
                model=model,
                config_path=config_path,
                qa_only=True,  # Focus on QA from these images
                domain=domain
            )
             
            if qa_state.get("qa_results"):
                pair_qa = qa_state["qa_results"]

        # Create structured result with keys
        result_item = {
            "pair_id": pair_id,
            "image_paths": image_paths_str,
            "domain": domain,
            "tables": pair_tables,
            "qa_results": pair_qa,
            "metadata": {
                "provider": provider,
                "model": model,
                "qa_only": should_skip_tables
            }
        }
        
        # Upload to Notion if enabled
        if notion_uploader and pair_qa:
            try:
                print(f"  Uploading to Notion database...")
                upload_result = notion_uploader.upload_qa_result(
                    domain=domain or "unknown",
                    image_path=pair_id,  # Use pair_id as identifier
                    qa_results=pair_qa,
                    provider=provider
                )
                result_item["notion_upload"] = {
                    "success": True,
                    "created_count": upload_result.get("created_count", 0)
                }
                print(f"  ✅ Uploaded {upload_result.get('created_count', 0)} QA rows to Notion")
            except Exception as e:
                result_item["notion_upload"] = {
                    "success": False,
                    "error": str(e)
                }
                print(f"  ❌ Notion upload failed: {e}")
        
        final_results.append(result_item)

        
        # Save intermediate per pair (optional, but good for safety)
        # pair_name = "_".join(pair_ids)
        # (output_dir / f"{pair_name}.json").write_text(json.dumps(result_item, ensure_ascii=False, indent=2), encoding="utf-8")

    # Save Final JSON
    output_file = output_dir / "pipeline_output.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_results, f, ensure_ascii=False, indent=2)
    
    print(f"\nPipeline Complete. Saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Run Table/QA pipeline from JSON input")
    parser.add_argument("--input", required=True, help="Path to JSON input file or JSON string")
    parser.add_argument("--data-root", default="data", help="Root directory to scan for images")
    parser.add_argument("--output-dir", default="output_json", help="Directory to save results")
    parser.add_argument("--provider", default="gemini_pool", help="LLM provider (default: gemini_pool)")
    parser.add_argument("--model", default="gemini-1.5-flash", help="Model name (default: gemini-1.5-flash)")
    parser.add_argument("--config-path", default="apis/gemini_keys.yaml", help="Path to gemini_keys.yaml")
    parser.add_argument("--domain", help="Force specific domain")
    parser.add_argument("--qa-only", action="store_true", help="Skip table generation, only generate QA (applies to all domains)")
    parser.add_argument("--upload-to-notion", action="store_true", help="Upload QA results to Notion database")

    args = parser.parse_args()

    # Parse JSON input
    input_data = []
    if os.path.isfile(args.input):
        with open(args.input, "r", encoding="utf-8") as f:
            input_data = json.load(f)
    else:
        try:
            input_data = json.loads(args.input)
        except json.JSONDecodeError:
            print("Error: Input is neither a valid file path nor a valid JSON string.")
            return

    # Validate structure roughly
    if not isinstance(input_data, list):
        print("Error: Input JSON must be a list of pairs.")
        return

    data_root = Path(args.data_root)
    output_dir = Path(args.output_dir)

    run_pipeline(
        json_input=input_data,
        data_root=data_root,
        output_dir=output_dir,
        provider=args.provider,
        model=args.model,
        config_path=args.config_path,
        arg_domain=args.domain,
        qa_only=args.qa_only,
        upload_to_notion=args.upload_to_notion
    )

if __name__ == "__main__":
    main()
