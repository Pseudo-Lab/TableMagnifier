"""
Upload QA results to Notion from pipeline_output.json files.

This script reads pipeline_output.json from a specified directory 
and uploads only the QA results to Notion database.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

sys.path.append(str(Path(__file__).parent))

from generate_synthetic_table.notion_uploader import NotionUploader


def upload_from_json(
    json_path: Path,
    config_path: str = "apis/gemini_keys.yaml",
    dry_run: bool = False,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Upload QA results from pipeline_output.json to Notion.
    
    Args:
        json_path: Path to pipeline_output.json
        config_path: Path to config file with Notion credentials
        dry_run: If True, only print what would be uploaded without actually uploading
        verbose: Print detailed progress
        
    Returns:
        Upload summary
    """
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")
    
    # Load JSON data
    with open(json_path, "r", encoding="utf-8") as f:
        results = json.load(f)
    
    if not isinstance(results, list):
        raise ValueError("JSON must contain a list of result items")
    
    if verbose:
        print(f"📂 Loaded {len(results)} result(s) from {json_path}")
    
    # Initialize Notion uploader
    if not dry_run:
        uploader = NotionUploader(config_path=config_path)
        if verbose:
            print("✅ Notion uploader initialized\n")
    
    total_uploaded = 0
    total_qa_count = 0
    skipped_count = 0
    failed_count = 0
    
    for i, result in enumerate(results, 1):
        pair_id = result.get("pair_id", f"unknown_{i}")
        domain = result.get("domain", "unknown")
        qa_results = result.get("qa_results", [])
        provider = result.get("metadata", {}).get("provider", "unknown")
        image_paths = result.get("image_paths", [])
        
        # Use first image path or pair_id as identifier
        image_identifier = image_paths[0] if image_paths else pair_id
        
        if not qa_results:
            if verbose:
                print(f"⏭️  [{i}/{len(results)}] Skipped {pair_id}: No QA results")
            skipped_count += 1
            continue
        
        qa_count = len(qa_results)
        
        if dry_run:
            if verbose:
                print(f"🔍 [{i}/{len(results)}] Would upload {pair_id}:")
                print(f"   - Domain: {domain}")
                print(f"   - Image: {image_identifier}")
                print(f"   - QA pairs: {qa_count}")
                print(f"   - Provider: {provider}")
        else:
            try:
                if verbose:
                    print(f"⬆️  [{i}/{len(results)}] Uploading {pair_id}...")
                    print(f"   - Domain: {domain}")
                    print(f"   - Image: {image_identifier}")
                    print(f"   - QA pairs: {qa_count}")
                
                upload_result = uploader.upload_qa_result(
                    domain=domain,
                    image_path=image_identifier,
                    qa_results=qa_results,
                    provider=provider
                )
                
                created_count = upload_result.get("created_count", 0)
                total_qa_count += created_count
                total_uploaded += 1
                
                if verbose:
                    print(f"   ✅ Uploaded {created_count} QA rows\n")
                    
            except Exception as e:
                failed_count += 1
                if verbose:
                    print(f"   ❌ Failed: {e}\n")
    
    summary = {
        "total_results": len(results),
        "uploaded": total_uploaded,
        "skipped": skipped_count,
        "failed": failed_count,
        "total_qa_rows": total_qa_count
    }
    
    if verbose:
        print("=" * 50)
        print("📊 Upload Summary:")
        print(f"   Total results: {summary['total_results']}")
        print(f"   Uploaded: {summary['uploaded']}")
        print(f"   Skipped: {summary['skipped']}")
        print(f"   Failed: {summary['failed']}")
        print(f"   Total QA rows: {summary['total_qa_rows']}")
        if dry_run:
            print("\n⚠️  DRY RUN: No data was actually uploaded")
    
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Upload QA results from pipeline_output.json to Notion database"
    )
    parser.add_argument(
        "json_path",
        type=str,
        help="Path to pipeline_output.json or directory containing it"
    )
    parser.add_argument(
        "--config-path",
        default="apis/gemini_keys.yaml",
        help="Path to config file with Notion credentials (default: apis/gemini_keys.yaml)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be uploaded without actually uploading"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress messages"
    )
    
    args = parser.parse_args()
    
    # Convert to Path
    json_path = Path(args.json_path)
    
    # If directory is given, look for pipeline_output.json inside
    if json_path.is_dir():
        json_path = json_path / "pipeline_output.json"
        if not json_path.exists():
            print(f"❌ Error: pipeline_output.json not found in {args.json_path}")
            print(f"   Looking for: {json_path}")
            sys.exit(1)
    
    try:
        upload_from_json(
            json_path=json_path,
            config_path=args.config_path,
            dry_run=args.dry_run,
            verbose=not args.quiet
        )
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
