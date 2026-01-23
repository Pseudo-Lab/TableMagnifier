#!/usr/bin/env python3
"""
vLLM 서버를 사용한 Table QA 평가 스크립트.

output_* 디렉토리의 HTML 테이블 이미지와 QA 데이터를 사용하여
멀티모달 모델의 Table QA 성능을 평가합니다.

Usage:
    # 단일 도메인 평가
    python -m eval.evaluate_vllm --domain public --vllm-url http://localhost:8000/v1

    # 모든 도메인 평가
    python -m eval.evaluate_vllm --all-domains --vllm-url http://localhost:8000/v1

    # 특정 모델 사용
    python -m eval.evaluate_vllm --domain business --model Qwen/Qwen2-VL-7B-Instruct

    # LLM-as-Judge 포함
    python -m eval.evaluate_vllm --domain finance --use-judge --judge-model gpt-4o
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from eval.dataset import QAItem, EvalDataset
from eval.inference import VLLMClient, InferenceRequest, InferenceResponse, run_inference
from eval.metrics import compute_metrics, aggregate_metrics, EvalResult, AggregatedMetrics
from eval.evaluate import evaluate_predictions, generate_report, print_report
from eval.llm_judge import create_judge_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# 도메인별 output 디렉토리 매핑
DOMAIN_DIRS = {
    "academic": "output_academic",
    "business": "output_business",
    "finance": "output_finance",
    "medical": "output_medical",
    "public": "output_public",
}

# 기본 프롬프트 템플릿
DEFAULT_PROMPT_TEMPLATE = """당신은 테이블 이미지를 분석하여 질문에 답하는 AI 어시스턴트입니다.
주어진 테이블 이미지를 주의 깊게 분석한 후, 질문에 대해 정확하고 간결하게 답변해주세요.

질문: {question}

답변:"""

# Context가 있는 경우의 프롬프트 템플릿
CONTEXT_PROMPT_TEMPLATE = """당신은 테이블 이미지를 분석하여 질문에 답하는 AI 어시스턴트입니다.
주어진 테이블 이미지와 아래 문맥을 함께 고려하여 질문에 정확하고 간결하게 답변해주세요.

[문맥]
{context}

질문: {question}

답변:"""


@dataclass
class EvalConfig:
    """평가 설정"""
    domain: str
    vllm_url: str = "http://localhost:8000/v1"
    model: str = "default"
    max_tokens: int = 512
    temperature: float = 0.0
    max_concurrent: int = 10
    timeout: float = 120.0
    use_judge: bool = False
    judge_provider: str = "openai"
    judge_model: Optional[str] = None
    judge_api_key: Optional[str] = None
    output_dir: Optional[Path] = None
    limit: Optional[int] = None  # 평가할 최대 샘플 수 (디버깅용)
    qa_types: Optional[List[str]] = None  # 특정 QA 타입만 평가


def find_table_images(
    output_dir: Path,
    pair_id: str,
    image_paths: List[str],
) -> List[Path]:
    """
    QA 항목에 해당하는 테이블 이미지를 찾습니다.

    HTML 파일이 이미지로 캡처되었다고 가정하고,
    output_dir/images/ 디렉토리에서 이미지를 찾습니다.

    파일명 패턴:
    - pair_id: "B_origin_3_3_0"
    - HTML: "B_origin_3_3_0_table_0.html", "B_origin_3_3_0_table_1.html"
    - Images: "B_origin_3_3_0_table_0.png", "B_origin_3_3_0_table_1.png"

    Args:
        output_dir: output_* 디렉토리 경로
        pair_id: QA pair ID
        image_paths: 원본 이미지 경로 리스트 (data/Public/Table/P_origin_0/...)

    Returns:
        찾은 이미지 경로 리스트
    """
    found_images = []

    images_dir = output_dir / "images"
    html_dir = output_dir / "html"

    # 1. images/ 디렉토리에서 캡처된 이미지 찾기 (pair_id_table_*.png 패턴)
    if images_dir.exists():
        # pair_id_table_N.png 패턴으로 찾기
        for img_file in sorted(images_dir.glob(f"{pair_id}_table_*.png")):
            found_images.append(img_file)

        # 못 찾았으면 pair_id*.png 패턴으로 시도
        if not found_images:
            for img_file in sorted(images_dir.glob(f"{pair_id}*.png")):
                found_images.append(img_file)

    # 2. html/ 디렉토리의 HTML 파일에 대응하는 이미지 찾기
    if not found_images and html_dir.exists() and images_dir.exists():
        for html_file in sorted(html_dir.glob(f"{pair_id}*.html")):
            img_path = images_dir / f"{html_file.stem}.png"
            if img_path.exists():
                found_images.append(img_path)

    # 3. 원본 이미지 경로가 존재하면 사용 (fallback)
    if not found_images:
        for orig_path in image_paths:
            p = Path(orig_path)
            if p.exists():
                found_images.append(p)
            else:
                # 프로젝트 루트 기준 상대 경로 시도
                full_path = project_root / orig_path
                if full_path.exists():
                    found_images.append(full_path)

    return sorted(set(found_images))  # 중복 제거 및 정렬


def load_qa_from_pipeline_output(
    output_dir: Path,
    limit: Optional[int] = None,
    qa_types: Optional[List[str]] = None,
) -> EvalDataset:
    """
    pipeline_output.json에서 QA 데이터를 로드합니다.

    Args:
        output_dir: output_* 디렉토리
        limit: 최대 로드할 샘플 수
        qa_types: 특정 QA 타입만 로드

    Returns:
        EvalDataset
    """
    pipeline_output = output_dir / "pipeline_output.json"

    if not pipeline_output.exists():
        logger.warning(f"pipeline_output.json not found in {output_dir}")
        return EvalDataset()

    with open(pipeline_output, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = []
    skipped_no_images = 0
    skipped_qa_type = 0

    for entry in data:
        pair_id = entry.get("pair_id", entry.get("name", "unknown"))
        image_paths = entry.get("image_paths", [])
        domain = entry.get("domain", "unknown")
        qa_results = entry.get("qa_results", [])

        # 테이블 이미지 찾기
        table_images = find_table_images(output_dir, pair_id, image_paths)

        for idx, qa in enumerate(qa_results):
            qa_type = qa.get("type", "unknown")

            # QA 타입 필터링
            if qa_types and qa_type not in qa_types:
                skipped_qa_type += 1
                continue

            item_id = f"{pair_id}_{idx}"

            # 이미지 경로 결정
            if table_images:
                item_image_paths = [str(p) for p in table_images]
            elif image_paths:
                # 원본 경로 사용 (fallback)
                item_image_paths = image_paths
            else:
                skipped_no_images += 1
                continue

            item = QAItem(
                id=item_id,
                question=qa.get("question", ""),
                answer=qa.get("answer", ""),
                qa_type=qa_type,
                image_paths=item_image_paths,
                reasoning_annotation=qa.get("reasoning_annotation"),
                context=qa.get("context"),
                source_file=str(pipeline_output),
            )
            items.append(item)

            if limit and len(items) >= limit:
                break

        if limit and len(items) >= limit:
            break

    if skipped_no_images:
        logger.warning(f"Skipped {skipped_no_images} QA items without images")
    if skipped_qa_type:
        logger.info(f"Skipped {skipped_qa_type} QA items due to type filter")

    dataset = EvalDataset(
        items=items,
        metadata={
            "source": str(pipeline_output),
            "domain": output_dir.name,
            "total_entries": len(data),
            "loaded_qa_count": len(items),
        }
    )

    return dataset


def create_inference_requests(
    dataset: EvalDataset,
    prompt_template: Optional[str] = None,
) -> List[InferenceRequest]:
    """
    추론 요청을 생성합니다.

    Args:
        dataset: 평가 데이터셋
        prompt_template: 프롬프트 템플릿

    Returns:
        InferenceRequest 리스트
    """
    requests = []

    for item in dataset:
        # context가 있으면 context 템플릿 사용
        if item.context:
            template = prompt_template or CONTEXT_PROMPT_TEMPLATE
            prompt = template.format(
                question=item.question,
                context=item.context,
            )
        else:
            template = prompt_template or DEFAULT_PROMPT_TEMPLATE
            prompt = template.format(question=item.question)

        request = InferenceRequest(
            id=item.id,
            prompt=prompt,
            ground_truth=item.answer,
            qa_type=item.qa_type,
            image_paths=item.image_paths,
        )
        requests.append(request)

    return requests


async def evaluate_domain(
    config: EvalConfig,
) -> tuple[List[EvalResult], AggregatedMetrics, Dict[str, Any]]:
    """
    단일 도메인에 대해 평가를 실행합니다.

    Args:
        config: 평가 설정

    Returns:
        (개별 결과, 집계 메트릭, 메타데이터)
    """
    domain_dir_name = DOMAIN_DIRS.get(config.domain)
    if not domain_dir_name:
        raise ValueError(f"Unknown domain: {config.domain}. Available: {list(DOMAIN_DIRS.keys())}")

    output_dir = project_root / domain_dir_name
    if not output_dir.exists():
        raise FileNotFoundError(f"Output directory not found: {output_dir}")

    logger.info(f"Evaluating domain: {config.domain}")
    logger.info(f"Output directory: {output_dir}")

    # 1. 데이터셋 로드
    dataset = load_qa_from_pipeline_output(
        output_dir,
        limit=config.limit,
        qa_types=config.qa_types,
    )

    if len(dataset) == 0:
        logger.error("No QA items loaded. Check if pipeline_output.json exists and contains valid data.")
        return [], AggregatedMetrics(), {}

    logger.info(f"Loaded {len(dataset)} QA items")
    logger.info(f"Type distribution: {dataset.get_type_distribution()}")

    # 2. 추론 요청 생성
    requests = create_inference_requests(dataset)

    # 3. vLLM 클라이언트 생성
    client = VLLMClient(
        base_url=config.vllm_url,
        model=config.model,
        max_tokens=config.max_tokens,
        temperature=config.temperature,
        timeout=config.timeout,
        max_concurrent=config.max_concurrent,
    )

    # 4. 추론 실행
    inference_output = None
    if config.output_dir:
        config.output_dir.mkdir(parents=True, exist_ok=True)
        inference_output = config.output_dir / f"{config.domain}_inference.json"

    logger.info(f"Running inference on {len(requests)} requests...")
    responses = await run_inference(client, requests, output_path=inference_output)

    # 5. 평가
    predictions = [
        {
            "id": r.id,
            "prediction": r.prediction,
            "ground_truth": r.ground_truth,
            "qa_type": r.qa_type,
            "question": dataset.items[i].question if i < len(dataset.items) else "",
        }
        for i, r in enumerate(responses)
    ]

    # Judge 클라이언트 설정
    judge_client = None
    if config.use_judge:
        judge_client = create_judge_client(
            provider=config.judge_provider,
            model=config.judge_model,
            api_key=config.judge_api_key,
        )

    questions = [item.question for item in dataset.items]
    results, aggregated = await evaluate_predictions(
        predictions,
        use_judge=config.use_judge,
        judge_client=judge_client,
        questions=questions,
    )

    # 메타데이터
    metadata = {
        "domain": config.domain,
        "model": config.model,
        "vllm_url": config.vllm_url,
        "total_items": len(dataset),
        "type_distribution": dataset.get_type_distribution(),
        "timestamp": datetime.now().isoformat(),
    }

    return results, aggregated, metadata


async def evaluate_all_domains(
    config: EvalConfig,
) -> Dict[str, tuple[List[EvalResult], AggregatedMetrics]]:
    """
    모든 도메인에 대해 평가를 실행합니다.

    Args:
        config: 기본 평가 설정 (domain 필드는 무시됨)

    Returns:
        도메인별 결과 딕셔너리
    """
    all_results = {}

    for domain in DOMAIN_DIRS.keys():
        domain_config = EvalConfig(
            domain=domain,
            vllm_url=config.vllm_url,
            model=config.model,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            max_concurrent=config.max_concurrent,
            timeout=config.timeout,
            use_judge=config.use_judge,
            judge_provider=config.judge_provider,
            judge_model=config.judge_model,
            judge_api_key=config.judge_api_key,
            output_dir=config.output_dir,
            limit=config.limit,
            qa_types=config.qa_types,
        )

        try:
            results, aggregated, metadata = await evaluate_domain(domain_config)
            all_results[domain] = (results, aggregated, metadata)
            print_report(aggregated)
        except Exception as e:
            logger.error(f"Failed to evaluate domain {domain}: {e}")
            all_results[domain] = ([], AggregatedMetrics(), {"error": str(e)})

    return all_results


def save_results(
    results: List[EvalResult],
    aggregated: AggregatedMetrics,
    metadata: Dict[str, Any],
    output_dir: Path,
    domain: str,
) -> None:
    """결과를 파일로 저장합니다."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 전체 리포트
    report = generate_report(results, aggregated, metadata)
    report_path = output_dir / f"{domain}_evaluation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, ensure_ascii=False, indent=2, fp=f)
    logger.info(f"Saved report to {report_path}")

    # 요약 결과 (CSV 친화적)
    summary_path = output_dir / f"{domain}_summary.json"
    summary = {
        "domain": domain,
        "total_count": aggregated.total_count,
        "exact_match": aggregated.exact_match_avg,
        "f1_score": aggregated.f1_score_avg,
        "contains_match": aggregated.contains_match_avg,
        "bleu_score": aggregated.bleu_score_avg,
        "by_type": aggregated.by_type,
    }
    if aggregated.judge_overall_avg is not None:
        summary["judge_overall"] = aggregated.judge_overall_avg
        summary["judge_accuracy"] = aggregated.judge_accuracy

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, ensure_ascii=False, indent=2, fp=f)
    logger.info(f"Saved summary to {summary_path}")


def main():
    parser = argparse.ArgumentParser(
        description="vLLM 서버를 사용한 Table QA 평가",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 단일 도메인 평가
  python -m eval.evaluate_vllm --domain public --vllm-url http://localhost:8000/v1

  # 모든 도메인 평가
  python -m eval.evaluate_vllm --all-domains --vllm-url http://localhost:8000/v1

  # 특정 모델 사용
  python -m eval.evaluate_vllm --domain business --model Qwen/Qwen2-VL-7B-Instruct

  # LLM-as-Judge 포함
  python -m eval.evaluate_vllm --domain finance --use-judge --judge-model gpt-4o

  # 특정 QA 타입만 평가
  python -m eval.evaluate_vllm --domain public --qa-types lookup compare

  # 제한된 샘플로 테스트
  python -m eval.evaluate_vllm --domain public --limit 10
        """,
    )

    # 필수 인자
    parser.add_argument(
        "--domain",
        choices=list(DOMAIN_DIRS.keys()),
        help="평가할 도메인",
    )
    parser.add_argument(
        "--all-domains",
        action="store_true",
        help="모든 도메인 평가",
    )

    # vLLM 설정
    parser.add_argument(
        "--vllm-url",
        default="http://localhost:8000/v1",
        help="vLLM 서버 URL (default: http://localhost:8000/v1)",
    )
    parser.add_argument(
        "--model",
        default="default",
        help="사용할 모델 이름 (default: vLLM에서 로드된 모델 사용)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="최대 생성 토큰 수 (default: 512)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="생성 온도 (default: 0.0)",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=10,
        help="최대 동시 요청 수 (default: 10)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="요청 타임아웃(초) (default: 120.0)",
    )

    # Judge 설정
    parser.add_argument(
        "--use-judge",
        action="store_true",
        help="LLM-as-Judge 평가 사용",
    )
    parser.add_argument(
        "--judge-provider",
        default="openai",
        choices=["openai", "anthropic"],
        help="Judge 제공자 (default: openai)",
    )
    parser.add_argument(
        "--judge-model",
        help="Judge 모델 (default: gpt-4o-mini)",
    )
    parser.add_argument(
        "--judge-api-key",
        help="Judge API 키 (환경변수에서 가져오지 않을 경우)",
    )

    # 출력 설정
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("eval_results"),
        help="결과 저장 디렉토리 (default: eval_results)",
    )

    # 필터링 옵션
    parser.add_argument(
        "--limit",
        type=int,
        help="평가할 최대 샘플 수 (디버깅용)",
    )
    parser.add_argument(
        "--qa-types",
        nargs="+",
        help="특정 QA 타입만 평가 (예: lookup compare arithmetic)",
    )

    args = parser.parse_args()

    # 인자 검증
    if not args.domain and not args.all_domains:
        parser.error("--domain 또는 --all-domains 중 하나를 지정해야 합니다.")

    # 설정 생성
    config = EvalConfig(
        domain=args.domain or "public",  # all-domains일 때 기본값
        vllm_url=args.vllm_url,
        model=args.model,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        max_concurrent=args.max_concurrent,
        timeout=args.timeout,
        use_judge=args.use_judge,
        judge_provider=args.judge_provider,
        judge_model=args.judge_model,
        judge_api_key=args.judge_api_key,
        output_dir=args.output_dir,
        limit=args.limit,
        qa_types=args.qa_types,
    )

    # 평가 실행
    if args.all_domains:
        all_results = asyncio.run(evaluate_all_domains(config))

        # 전체 요약 저장
        if config.output_dir:
            config.output_dir.mkdir(parents=True, exist_ok=True)

            all_summary = {}
            for domain, (results, aggregated, metadata) in all_results.items():
                if results:
                    save_results(results, aggregated, metadata, config.output_dir, domain)
                    all_summary[domain] = {
                        "total_count": aggregated.total_count,
                        "exact_match": aggregated.exact_match_avg,
                        "f1_score": aggregated.f1_score_avg,
                    }

            summary_path = config.output_dir / "all_domains_summary.json"
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(all_summary, ensure_ascii=False, indent=2, fp=f)
            logger.info(f"Saved all-domains summary to {summary_path}")
    else:
        results, aggregated, metadata = asyncio.run(evaluate_domain(config))
        print_report(aggregated)

        if config.output_dir and results:
            save_results(results, aggregated, metadata, config.output_dir, config.domain)


if __name__ == "__main__":
    main()
