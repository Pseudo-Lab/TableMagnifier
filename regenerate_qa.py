#!/usr/bin/env python3
"""
기존 synthetic 테이블에서 QA를 재생성하는 스크립트.

output_*/html/ 디렉토리의 HTML 파일을 직접 읽어서 새로운 QA pairs를 생성합니다.
pipeline_output.json은 entry 목록과 결과 저장에만 사용됩니다.

Usage:
    # 특정 도메인 재생성
    python regenerate_qa.py --domain business

    # 여러 도메인 재생성
    python regenerate_qa.py --domain business finance academic medical

    # 모든 도메인 재생성 (output_public 제외)
    python regenerate_qa.py --all

    # 특정 provider/model 사용
    python regenerate_qa.py --domain business --provider openai --model gpt-4o
"""

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from generate_synthetic_table.flow import (
    _load_prompt,
    _call_llm,
    robust_json_parse,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 도메인별 output 디렉토리
DOMAIN_DIRS = {
    "academic": "output_academic",
    "business": "output_business",
    "finance": "output_finance",
    "medical": "output_medical",
    # "public": "output_public",  # 제외
}


def get_llm_client(provider: str, model: str):
    """LLM 클라이언트 생성"""
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic
    from langchain_google_genai import ChatGoogleGenerativeAI

    if provider == "openai":
        return ChatOpenAI(
            model=model,
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY"),
        )
    elif provider in ["claude", "anthropic"]:
        return ChatAnthropic(
            model=model,
            temperature=0.7,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )
    elif provider in ["gemini", "google"]:
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=0.7,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")


def find_html_files(output_dir: Path, pair_id: str) -> List[Path]:
    """
    output_dir/html/ 디렉토리에서 pair_id에 해당하는 HTML 파일들을 찾습니다.

    파일 패턴: {pair_id}_table_*.html
    예: B_origin_0_0_0_table_0.html, B_origin_0_0_0_table_1.html
    """
    html_dir = output_dir / "html"
    if not html_dir.exists():
        return []

    # pair_id로 시작하는 HTML 파일 찾기
    pattern = f"{pair_id}_table_*.html"
    html_files = sorted(html_dir.glob(pattern))

    return html_files


def read_html_files(html_files: List[Path]) -> List[str]:
    """
    HTML 파일들을 읽어서 내용을 반환합니다.
    """
    html_contents = []
    for html_file in html_files:
        try:
            with open(html_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    html_contents.append(content)
        except Exception as e:
            logger.warning(f"Failed to read {html_file}: {e}")

    return html_contents


def generate_qa_for_table(
    llm,
    synthetic_html: str,
    domain: str,
) -> List[Dict[str, Any]]:
    """단일 synthetic table에 대해 QA를 생성합니다."""
    try:
        prompt_template = _load_prompt("generate_qa", domain)
        prompt = prompt_template.format(synthetic_html=synthetic_html)

        response_text, _ = _call_llm(llm, prompt, return_token_usage=True)
        response_json = robust_json_parse(response_text)

        if response_json and "qa_pairs" in response_json:
            return response_json["qa_pairs"]
        else:
            logger.warning("QA generation did not return valid qa_pairs")
            return []
    except Exception as e:
        logger.error(f"Failed to generate QA: {e}")
        return []


def generate_long_sequence_for_table(
    llm,
    synthetic_html: str,
    domain: str,
) -> List[Dict[str, Any]]:
    """단일 synthetic table에 대해 long_sequence QA를 생성합니다."""
    try:
        prompt_template = _load_prompt("generate_long_sequence", domain)
        prompt = prompt_template.format(synthetic_html=synthetic_html)

        response_text, _ = _call_llm(llm, prompt, return_token_usage=True)
        response_json = robust_json_parse(response_text)

        if response_json and "qa_pairs" in response_json:
            return response_json["qa_pairs"]
        else:
            return []
    except ValueError:
        # generate_long_sequence prompt not found
        return []
    except Exception as e:
        logger.warning(f"Failed to generate long_sequence QA: {e}")
        return []


def regenerate_qa_for_entry(
    llm,
    entry: Dict[str, Any],
    output_dir: Path,
    domain: str,
    include_long_sequence: bool = True,
) -> Dict[str, Any]:
    """
    단일 entry에 대해 QA를 재생성합니다.

    html/ 디렉토리에서 HTML 파일을 직접 읽어서 QA를 생성합니다.
    여러 테이블이 있는 경우, 각 테이블에 대해 QA를 생성하고 합칩니다.
    """
    pair_id = entry.get("pair_id", entry.get("name", "unknown"))

    # HTML 파일 찾기 및 읽기
    html_files = find_html_files(output_dir, pair_id)
    if not html_files:
        logger.warning(f"No HTML files found for {pair_id} in {output_dir}/html/")
        return entry

    synthetic_tables = read_html_files(html_files)
    if not synthetic_tables:
        logger.warning(f"Failed to read HTML files for {pair_id}")
        return entry

    logger.info(f"  Found {len(html_files)} HTML files: {[f.name for f in html_files]}")

    all_qa_results = []

    # 각 테이블에 대해 QA 생성
    for idx, synthetic_html in enumerate(synthetic_tables):
        logger.info(f"  Generating QA for table {idx + 1}/{len(synthetic_tables)}")

        # 기본 QA 생성 (9개 타입)
        qa_results = generate_qa_for_table(llm, synthetic_html, domain)
        all_qa_results.extend(qa_results)

        # long_sequence QA 생성 (선택적)
        if include_long_sequence:
            long_seq_results = generate_long_sequence_for_table(llm, synthetic_html, domain)
            all_qa_results.extend(long_seq_results)

    # 결과 업데이트
    updated_entry = entry.copy()
    updated_entry["qa_results"] = all_qa_results
    updated_entry["qa_regenerated_at"] = datetime.now().isoformat()
    updated_entry["html_files_used"] = [f.name for f in html_files]

    return updated_entry


def regenerate_qa_for_domain(
    domain: str,
    provider: str = "claude",
    model: str = "claude-sonnet-4-5",
    include_long_sequence: bool = True,
    limit: Optional[int] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    특정 도메인의 모든 entry에 대해 QA를 재생성합니다.
    """
    domain_dir = DOMAIN_DIRS.get(domain)
    if not domain_dir:
        raise ValueError(f"Unknown domain: {domain}")

    output_dir = project_root / domain_dir
    pipeline_output_path = output_dir / "pipeline_output.json"

    if not pipeline_output_path.exists():
        raise FileNotFoundError(f"pipeline_output.json not found: {pipeline_output_path}")

    # Load existing data
    with open(pipeline_output_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    logger.info(f"Loaded {len(data)} entries from {pipeline_output_path}")

    if limit:
        data = data[:limit]
        logger.info(f"Limited to {limit} entries")

    if dry_run:
        logger.info("Dry run mode - not regenerating QA")
        # HTML 파일 존재 여부 확인
        html_dir = output_dir / "html"
        if not html_dir.exists():
            logger.warning(f"HTML directory not found: {html_dir}")
            return {"domain": domain, "entries": len(data), "dry_run": True, "html_dir_exists": False}

        # 각 entry에 대해 HTML 파일 수 확인
        entries_with_html = 0
        total_html_files = 0
        for entry in data:
            pair_id = entry.get("pair_id", entry.get("name", ""))
            html_files = find_html_files(output_dir, pair_id)
            if html_files:
                entries_with_html += 1
                total_html_files += len(html_files)
                logger.info(f"  {pair_id}: {len(html_files)} HTML files")

        logger.info(f"Summary: {entries_with_html}/{len(data)} entries have HTML files ({total_html_files} total)")
        return {
            "domain": domain,
            "entries": len(data),
            "entries_with_html": entries_with_html,
            "total_html_files": total_html_files,
            "dry_run": True,
        }

    # Create LLM client
    llm = get_llm_client(provider, model)

    # Regenerate QA for each entry
    updated_data = []
    success_count = 0
    error_count = 0

    for i, entry in enumerate(data):
        pair_id = entry.get("pair_id", entry.get("name", f"entry_{i}"))
        logger.info(f"[{i + 1}/{len(data)}] Processing: {pair_id}")

        try:
            updated_entry = regenerate_qa_for_entry(
                llm,
                entry,
                output_dir,
                domain,
                include_long_sequence=include_long_sequence,
            )
            updated_data.append(updated_entry)

            qa_count = len(updated_entry.get("qa_results", []))
            logger.info(f"  Generated {qa_count} QA pairs")
            success_count += 1
        except Exception as e:
            logger.error(f"  Failed: {e}")
            updated_data.append(entry)  # Keep original
            error_count += 1

    # Backup original file
    backup_path = output_dir / f"pipeline_output_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"Backed up original to {backup_path}")

    # Save updated data
    with open(pipeline_output_path, "w", encoding="utf-8") as f:
        json.dump(updated_data, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved updated data to {pipeline_output_path}")

    return {
        "domain": domain,
        "total_entries": len(data),
        "success": success_count,
        "errors": error_count,
        "backup": str(backup_path),
    }


def main():
    parser = argparse.ArgumentParser(
        description="기존 synthetic 테이블에서 QA를 재생성합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 특정 도메인 재생성
  python regenerate_qa.py --domain business

  # 여러 도메인 재생성
  python regenerate_qa.py --domain business finance

  # 모든 도메인 재생성 (output_public 제외)
  python regenerate_qa.py --all

  # OpenAI 사용
  python regenerate_qa.py --domain business --provider openai --model gpt-4o

  # 테스트 (5개만)
  python regenerate_qa.py --domain business --limit 5

  # Dry run (실제 재생성 없이 확인만)
  python regenerate_qa.py --domain business --dry-run
        """
    )

    parser.add_argument(
        "--domain",
        nargs="+",
        choices=list(DOMAIN_DIRS.keys()),
        help="재생성할 도메인(들)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="모든 도메인 재생성 (output_public 제외)",
    )
    parser.add_argument(
        "--provider",
        default="claude",
        choices=["claude", "anthropic", "openai", "gemini", "google"],
        help="LLM 제공자 (default: claude)",
    )
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-5",
        help="모델 이름 (default: claude-sonnet-4-5)",
    )
    parser.add_argument(
        "--no-long-sequence",
        action="store_true",
        help="long_sequence QA 생성 스킵",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="처리할 최대 entry 수 (테스트용)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 재생성 없이 확인만",
    )

    args = parser.parse_args()

    # Determine domains to process
    if args.all:
        domains = list(DOMAIN_DIRS.keys())
    elif args.domain:
        domains = args.domain
    else:
        parser.error("--domain 또는 --all을 지정해야 합니다.")

    logger.info(f"Domains to process: {domains}")
    logger.info(f"Provider: {args.provider}, Model: {args.model}")

    # Process each domain
    results = []
    for domain in domains:
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing domain: {domain}")
        logger.info(f"{'='*60}")

        try:
            result = regenerate_qa_for_domain(
                domain=domain,
                provider=args.provider,
                model=args.model,
                include_long_sequence=not args.no_long_sequence,
                limit=args.limit,
                dry_run=args.dry_run,
            )
            results.append(result)
            logger.info(f"Completed: {result}")
        except Exception as e:
            logger.error(f"Failed to process {domain}: {e}")
            results.append({"domain": domain, "error": str(e)})

    # Summary
    print("\n" + "=" * 60)
    print("  QA Regeneration Summary")
    print("=" * 60)
    for result in results:
        domain = result.get("domain", "unknown")
        if "error" in result:
            print(f"  {domain}: ERROR - {result['error']}")
        elif result.get("dry_run"):
            html_info = ""
            if "entries_with_html" in result:
                html_info = f", {result['entries_with_html']}/{result['entries']} with HTML ({result['total_html_files']} files)"
            elif result.get("html_dir_exists") is False:
                html_info = ", NO html/ directory!"
            print(f"  {domain}: {result.get('entries', 0)} entries (dry run){html_info}")
        else:
            print(f"  {domain}: {result.get('success', 0)}/{result.get('total_entries', 0)} success, {result.get('errors', 0)} errors")
    print("=" * 60)


if __name__ == "__main__":
    main()
