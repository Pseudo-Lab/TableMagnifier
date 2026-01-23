#!/usr/bin/env python3
"""
vLLM 서버를 사용하여 QA 난이도를 측정하고 필터링하는 스크립트.

모델이 너무 쉽게 맞추는 문제(10/10)는 제외하고,
적당한 난이도(3-6/10 정확도)의 QA만 검수 대상으로 추출합니다.

Usage:
    # 기본 사용 (business 도메인)
    python filter_qa_by_difficulty.py --domain business

    # 여러 도메인
    python filter_qa_by_difficulty.py --all

    # 커스텀 설정
    python filter_qa_by_difficulty.py --domain business --trials 10 --min-acc 0.3 --max-acc 0.6

    # vLLM 서버 URL 지정
    python filter_qa_by_difficulty.py --domain business --vllm-url http://localhost:8000/v1
"""

import argparse
import base64
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv

load_dotenv()

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from eval.metrics import normalize_answer, exact_match, f1_score

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DOMAIN_DIRS = {
    "academic": "output_academic",
    "business": "output_business",
    "finance": "output_finance",
    "medical": "output_medical",
    "public": "output_public",
}


@dataclass
class FilterConfig:
    """필터링 설정"""
    vllm_url: str = "http://localhost:8000/v1"
    model_name: str = ""  # vLLM 서버에서 자동 감지
    trials: int = 10  # 각 QA당 시도 횟수
    min_accuracy: float = 0.3  # 최소 정확도 (이상)
    max_accuracy: float = 0.6  # 최대 정확도 (이하)
    temperature: float = 0.7  # 다양한 응답을 위해
    max_tokens: int = 512
    timeout: int = 60
    max_workers: int = 4  # 병렬 처리


@dataclass
class QADifficultyResult:
    """QA 난이도 측정 결과"""
    pair_id: str
    table_index: int
    qa_index: int
    question: str
    answer: str
    qa_type: str
    correct_count: int
    total_trials: int
    accuracy: float
    responses: List[str] = field(default_factory=list)
    difficulty_category: str = ""  # easy, medium, hard, very_hard

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pair_id": self.pair_id,
            "table_index": self.table_index,
            "qa_index": self.qa_index,
            "question": self.question,
            "answer": self.answer,
            "qa_type": self.qa_type,
            "correct_count": self.correct_count,
            "total_trials": self.total_trials,
            "accuracy": self.accuracy,
            "difficulty_category": self.difficulty_category,
            "sample_responses": self.responses[:3],  # 샘플만 저장
        }


def get_vllm_model_name(vllm_url: str) -> str:
    """vLLM 서버에서 모델 이름 가져오기"""
    import requests
    try:
        response = requests.get(f"{vllm_url}/models", timeout=10)
        response.raise_for_status()
        models = response.json().get("data", [])
        if models:
            return models[0]["id"]
    except Exception as e:
        logger.warning(f"Failed to get model name from vLLM: {e}")
    return "default"


def find_table_images(output_dir: Path, pair_id: str) -> List[Path]:
    """pair_id에 해당하는 테이블 이미지 찾기"""
    images_dir = output_dir / "images"
    if not images_dir.exists():
        return []

    found_images = []
    for img_file in sorted(images_dir.glob(f"{pair_id}_table_*.png")):
        found_images.append(img_file)

    return found_images


def encode_image_base64(image_path: Path) -> str:
    """이미지를 base64로 인코딩"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def run_single_inference(
    vllm_url: str,
    model_name: str,
    image_base64: str,
    question: str,
    config: FilterConfig,
) -> Optional[str]:
    """단일 추론 실행"""
    import requests

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_base64}"
                    }
                },
                {
                    "type": "text",
                    "text": f"Based on the table image, answer the following question concisely.\n\nQuestion: {question}\n\nAnswer:"
                }
            ]
        }
    ]

    try:
        response = requests.post(
            f"{vllm_url}/chat/completions",
            json={
                "model": model_name,
                "messages": messages,
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
            },
            timeout=config.timeout,
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.debug(f"Inference failed: {e}")
        return None


def check_answer_correct(prediction: str, ground_truth: str) -> bool:
    """답변이 맞는지 확인 (EM 또는 F1 > 0.8)"""
    if not prediction:
        return False

    # Exact match
    if exact_match(prediction, ground_truth):
        return True

    # F1 score > 0.8
    if f1_score(prediction, ground_truth) > 0.8:
        return True

    # 정규화된 답변이 포함되는지 확인
    norm_pred = normalize_answer(prediction)
    norm_gt = normalize_answer(ground_truth)
    if norm_gt in norm_pred or norm_pred in norm_gt:
        return True

    return False


def measure_qa_difficulty(
    vllm_url: str,
    model_name: str,
    image_base64: str,
    question: str,
    answer: str,
    config: FilterConfig,
) -> Tuple[int, List[str]]:
    """QA 난이도 측정 (여러 번 시도)"""
    correct_count = 0
    responses = []

    for trial in range(config.trials):
        response = run_single_inference(
            vllm_url, model_name, image_base64, question, config
        )
        if response:
            responses.append(response)
            if check_answer_correct(response, answer):
                correct_count += 1

    return correct_count, responses


def categorize_difficulty(accuracy: float) -> str:
    """정확도에 따라 난이도 분류"""
    if accuracy >= 0.9:
        return "too_easy"
    elif accuracy >= 0.7:
        return "easy"
    elif accuracy >= 0.3:
        return "medium"  # 목표 범위
    elif accuracy > 0:
        return "hard"
    else:
        return "very_hard"


def filter_qa_for_domain(
    domain: str,
    config: FilterConfig,
    limit: Optional[int] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """도메인의 QA를 필터링"""
    domain_dir = DOMAIN_DIRS.get(domain)
    if not domain_dir:
        raise ValueError(f"Unknown domain: {domain}")

    output_dir = project_root / domain_dir
    pipeline_output_path = output_dir / "pipeline_output.json"

    if not pipeline_output_path.exists():
        raise FileNotFoundError(f"pipeline_output.json not found: {pipeline_output_path}")

    # 이미지 디렉토리
    images_dir = output_dir / "images"

    # 데이터 로드
    with open(pipeline_output_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    logger.info(f"Loaded {len(data)} entries from {pipeline_output_path}")

    if limit:
        data = data[:limit]
        logger.info(f"Limited to {limit} entries")

    if dry_run:
        # QA 수 확인만 (이미지 없어도 OK)
        total_qa = sum(len(entry.get("qa_results", [])) for entry in data)
        images_exist = images_dir.exists()
        image_count = len(list(images_dir.glob("*.png"))) if images_exist else 0
        logger.info(f"Dry run: {len(data)} entries, {total_qa} QA pairs")
        logger.info(f"Images directory: {'exists' if images_exist else 'NOT FOUND'} ({image_count} images)")
        if not images_exist:
            logger.warning("이미지 디렉토리가 없습니다. 먼저 capture_html_to_images.py를 실행하세요.")
        return {
            "domain": domain,
            "entries": len(data),
            "total_qa": total_qa,
            "images_exist": images_exist,
            "image_count": image_count,
            "dry_run": True,
        }

    # 이미지 디렉토리 확인 (실제 실행 시)
    if not images_dir.exists():
        raise FileNotFoundError(
            f"Images directory not found: {images_dir}\n"
            "먼저 capture_html_to_images.py를 실행하여 HTML을 이미지로 변환하세요."
        )

    # vLLM 모델 이름 가져오기
    model_name = config.model_name or get_vllm_model_name(config.vllm_url)
    logger.info(f"Using model: {model_name}")

    # 결과 수집
    all_results: List[QADifficultyResult] = []
    stats = {
        "total_qa": 0,
        "too_easy": 0,
        "easy": 0,
        "medium": 0,
        "hard": 0,
        "very_hard": 0,
        "skipped": 0,
    }

    for entry_idx, entry in enumerate(data):
        pair_id = entry.get("pair_id", entry.get("name", f"entry_{entry_idx}"))
        qa_results = entry.get("qa_results", [])

        if not qa_results:
            continue

        # 이미지 찾기
        image_files = find_table_images(output_dir, pair_id)
        if not image_files:
            logger.warning(f"No images found for {pair_id}, skipping")
            stats["skipped"] += len(qa_results)
            continue

        # 첫 번째 이미지 사용 (TODO: 멀티 이미지 지원)
        image_base64 = encode_image_base64(image_files[0])

        logger.info(f"[{entry_idx + 1}/{len(data)}] Processing {pair_id} ({len(qa_results)} QAs)")

        for qa_idx, qa in enumerate(qa_results):
            question = qa.get("question", "")
            answer = qa.get("answer", "")
            qa_type = qa.get("type", "unknown")

            if not question or not answer:
                stats["skipped"] += 1
                continue

            stats["total_qa"] += 1

            # 난이도 측정
            correct_count, responses = measure_qa_difficulty(
                config.vllm_url,
                model_name,
                image_base64,
                question,
                answer,
                config,
            )

            accuracy = correct_count / config.trials if config.trials > 0 else 0
            difficulty = categorize_difficulty(accuracy)
            stats[difficulty] += 1

            result = QADifficultyResult(
                pair_id=pair_id,
                table_index=0,
                qa_index=qa_idx,
                question=question,
                answer=answer,
                qa_type=qa_type,
                correct_count=correct_count,
                total_trials=config.trials,
                accuracy=accuracy,
                responses=responses,
                difficulty_category=difficulty,
            )
            all_results.append(result)

            # 진행 상황 로그
            status = "✓" if config.min_accuracy <= accuracy <= config.max_accuracy else "✗"
            logger.info(f"    [{qa_idx + 1}/{len(qa_results)}] {qa_type}: {correct_count}/{config.trials} ({accuracy:.0%}) [{difficulty}] {status}")

    # 필터링 (목표 난이도 범위)
    filtered_results = [
        r for r in all_results
        if config.min_accuracy <= r.accuracy <= config.max_accuracy
    ]

    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"qa_difficulty_analysis_{timestamp}.json"

    output_data = {
        "domain": domain,
        "config": {
            "vllm_url": config.vllm_url,
            "model_name": model_name,
            "trials": config.trials,
            "min_accuracy": config.min_accuracy,
            "max_accuracy": config.max_accuracy,
            "temperature": config.temperature,
        },
        "stats": stats,
        "filtered_count": len(filtered_results),
        "all_results": [r.to_dict() for r in all_results],
        "filtered_for_review": [r.to_dict() for r in filtered_results],
        "timestamp": timestamp,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    logger.info(f"Results saved to {output_file}")

    # 검수용 간단 리스트 저장
    review_file = output_dir / f"qa_for_review_{timestamp}.json"
    review_data = {
        "domain": domain,
        "description": f"QA pairs with accuracy between {config.min_accuracy:.0%} and {config.max_accuracy:.0%}",
        "count": len(filtered_results),
        "items": [
            {
                "pair_id": r.pair_id,
                "qa_type": r.qa_type,
                "question": r.question,
                "answer": r.answer,
                "accuracy": f"{r.accuracy:.0%} ({r.correct_count}/{r.total_trials})",
                "sample_model_responses": r.responses[:3],
            }
            for r in filtered_results
        ],
    }

    with open(review_file, "w", encoding="utf-8") as f:
        json.dump(review_data, f, ensure_ascii=False, indent=2)

    logger.info(f"Review list saved to {review_file}")

    return {
        "domain": domain,
        "total_qa": stats["total_qa"],
        "stats": stats,
        "filtered_for_review": len(filtered_results),
        "output_file": str(output_file),
        "review_file": str(review_file),
    }


def main():
    parser = argparse.ArgumentParser(
        description="vLLM을 사용하여 QA 난이도를 측정하고 검수 대상을 필터링합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # business 도메인 필터링
  python filter_qa_by_difficulty.py --domain business

  # 모든 도메인
  python filter_qa_by_difficulty.py --all

  # 커스텀 설정 (5회 시도, 20-50% 정확도)
  python filter_qa_by_difficulty.py --domain business --trials 5 --min-acc 0.2 --max-acc 0.5

  # vLLM 서버 지정
  python filter_qa_by_difficulty.py --domain business --vllm-url http://localhost:8000/v1

  # 테스트 (3개 entry만)
  python filter_qa_by_difficulty.py --domain business --limit 3

Difficulty Categories:
  - too_easy: 90-100% accuracy (제외)
  - easy: 70-89% accuracy
  - medium: 30-69% accuracy (검수 대상)
  - hard: 1-29% accuracy
  - very_hard: 0% accuracy
        """
    )

    parser.add_argument(
        "--domain",
        nargs="+",
        choices=list(DOMAIN_DIRS.keys()),
        help="필터링할 도메인(들)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="모든 도메인 필터링",
    )
    parser.add_argument(
        "--vllm-url",
        default="http://localhost:8000/v1",
        help="vLLM 서버 URL (default: http://localhost:8000/v1)",
    )
    parser.add_argument(
        "--model",
        default="",
        help="모델 이름 (미지정시 vLLM에서 자동 감지)",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=10,
        help="각 QA당 시도 횟수 (default: 10)",
    )
    parser.add_argument(
        "--min-acc",
        type=float,
        default=0.3,
        help="최소 정확도 (default: 0.3)",
    )
    parser.add_argument(
        "--max-acc",
        type=float,
        default=0.6,
        help="최대 정확도 (default: 0.6)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="샘플링 temperature (default: 0.7)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="처리할 최대 entry 수 (테스트용)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 추론 없이 확인만",
    )

    args = parser.parse_args()

    # 도메인 결정
    if args.all:
        domains = list(DOMAIN_DIRS.keys())
    elif args.domain:
        domains = args.domain
    else:
        parser.error("--domain 또는 --all을 지정해야 합니다.")

    # 설정
    config = FilterConfig(
        vllm_url=args.vllm_url,
        model_name=args.model,
        trials=args.trials,
        min_accuracy=args.min_acc,
        max_accuracy=args.max_acc,
        temperature=args.temperature,
    )

    logger.info(f"Domains: {domains}")
    logger.info(f"Config: trials={config.trials}, accuracy range={config.min_accuracy:.0%}-{config.max_accuracy:.0%}")

    # 각 도메인 처리
    results = []
    for domain in domains:
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing domain: {domain}")
        logger.info(f"{'='*60}")

        try:
            result = filter_qa_for_domain(
                domain=domain,
                config=config,
                limit=args.limit,
                dry_run=args.dry_run,
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to process {domain}: {e}")
            results.append({"domain": domain, "error": str(e)})

    # 요약
    print("\n" + "=" * 60)
    print("  QA Difficulty Filtering Summary")
    print("=" * 60)
    for result in results:
        domain = result.get("domain", "unknown")
        if "error" in result:
            print(f"  {domain}: ERROR - {result['error']}")
        elif result.get("dry_run"):
            img_status = "✓" if result.get("images_exist") else "✗ (run capture_html_to_images.py first)"
            print(f"  {domain}: {result.get('total_qa', 0)} QA pairs, {result.get('image_count', 0)} images {img_status} (dry run)")
        else:
            stats = result.get("stats", {})
            filtered = result.get("filtered_for_review", 0)
            total = result.get("total_qa", 0)
            print(f"  {domain}:")
            print(f"    Total QA: {total}")
            print(f"    too_easy: {stats.get('too_easy', 0)}, easy: {stats.get('easy', 0)}")
            print(f"    medium: {stats.get('medium', 0)}, hard: {stats.get('hard', 0)}, very_hard: {stats.get('very_hard', 0)}")
            print(f"    → For review: {filtered} ({filtered/total*100:.1f}% of total)" if total > 0 else "")
    print("=" * 60)


if __name__ == "__main__":
    main()
