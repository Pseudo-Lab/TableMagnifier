"""
Main evaluation logic for Table QA.

추론 결과를 평가하고 리포트를 생성합니다.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from .dataset import (
    EvalDataset,
    QAItem,
    load_qa_from_folder,
    create_inference_prompts,
)
from .metrics import (
    compute_metrics,
    aggregate_metrics,
    EvalResult,
    AggregatedMetrics,
)
from .inference import (
    InferenceClient,
    InferenceRequest,
    InferenceResponse,
    get_client,
    run_inference,
)

logger = logging.getLogger(__name__)


def evaluate_predictions(
    predictions: List[Dict[str, Any]],
    ground_truths: Optional[List[Dict[str, Any]]] = None,
) -> tuple[List[EvalResult], AggregatedMetrics]:
    """
    예측 결과를 평가합니다.

    Args:
        predictions: 예측 결과 리스트
            [{"id": "...", "prediction": "...", "ground_truth": "...", "qa_type": "..."}]
        ground_truths: 정답 리스트 (옵션, predictions에 ground_truth가 없을 때 사용)

    Returns:
        (개별 결과 리스트, 집계 메트릭)
    """
    results = []

    # ground_truths가 별도로 제공된 경우 매핑
    gt_map = {}
    if ground_truths:
        gt_map = {gt["id"]: gt for gt in ground_truths}

    for pred in predictions:
        pred_id = pred.get("id", "")
        prediction = pred.get("prediction", "")
        qa_type = pred.get("qa_type", "unknown")

        # ground_truth 찾기
        if "ground_truth" in pred:
            ground_truth = pred["ground_truth"]
        elif pred_id in gt_map:
            ground_truth = gt_map[pred_id].get("answer", "")
            qa_type = gt_map[pred_id].get("type", qa_type)
        else:
            logger.warning(f"No ground truth found for {pred_id}")
            ground_truth = ""

        result = compute_metrics(
            prediction=prediction,
            ground_truth=ground_truth,
            qa_type=qa_type,
            id=pred_id,
        )
        results.append(result)

    aggregated = aggregate_metrics(results)
    return results, aggregated


def load_predictions(path: Path) -> List[Dict[str, Any]]:
    """
    예측 결과 파일을 로드합니다.

    지원 형식:
    - JSON: {"responses": [...]} 또는 [...]
    - JSONL: 각 줄이 하나의 예측
    """
    path = Path(path)

    if path.suffix == ".jsonl":
        predictions = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    predictions.append(json.loads(line))
        return predictions

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "responses" in data:
        return data["responses"]
    else:
        raise ValueError(f"Unknown prediction file format: {path}")


def generate_report(
    results: List[EvalResult],
    aggregated: AggregatedMetrics,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    평가 리포트를 생성합니다.

    Args:
        results: 개별 평가 결과
        aggregated: 집계 메트릭
        metadata: 추가 메타데이터

    Returns:
        리포트 딕셔너리
    """
    report = {
        "timestamp": datetime.now().isoformat(),
        "metadata": metadata or {},
        "summary": aggregated.to_dict(),
        "detailed_results": [r.to_dict() for r in results],
    }

    return report


def print_report(aggregated: AggregatedMetrics) -> None:
    """콘솔에 평가 결과 출력"""
    print("\n" + "=" * 60)
    print("  Table QA Evaluation Results")
    print("=" * 60)

    print(f"\nTotal Samples: {aggregated.total_count}")
    print(f"\nOverall Metrics:")
    print(f"  Exact Match:    {aggregated.exact_match_avg:.4f} ({aggregated.exact_match_avg * 100:.2f}%)")
    print(f"  F1 Score:       {aggregated.f1_score_avg:.4f} ({aggregated.f1_score_avg * 100:.2f}%)")
    print(f"  Contains Match: {aggregated.contains_match_avg:.4f} ({aggregated.contains_match_avg * 100:.2f}%)")
    print(f"  BLEU Score:     {aggregated.bleu_score_avg:.4f}")

    if aggregated.by_type:
        print(f"\nMetrics by QA Type:")
        print(f"  {'Type':<20} {'Count':>6} {'EM':>8} {'F1':>8} {'CM':>8}")
        print("  " + "-" * 52)
        for qa_type, metrics in sorted(aggregated.by_type.items()):
            print(f"  {qa_type:<20} {metrics['count']:>6} "
                  f"{metrics['exact_match']:>8.4f} "
                  f"{metrics['f1_score']:>8.4f} "
                  f"{metrics['contains_match']:>8.4f}")

    print("\n" + "=" * 60)


async def run_evaluation(
    data_source: str | Path,
    provider: str = "vllm",
    output_dir: Optional[Path] = None,
    prompt_template: Optional[str] = None,
    include_images: bool = False,
    **client_kwargs,
) -> tuple[List[EvalResult], AggregatedMetrics]:
    """
    전체 평가 파이프라인을 실행합니다.

    Args:
        data_source: QA 데이터 폴더 또는 파일 경로
        provider: 추론 제공자 (vllm, openai, anthropic)
        output_dir: 결과 저장 디렉토리
        prompt_template: 프롬프트 템플릿 (옵션)
        include_images: 이미지 포함 여부 (멀티모달)
        **client_kwargs: 클라이언트 설정

    Returns:
        (개별 결과, 집계 메트릭)
    """
    # 1. 데이터셋 로드
    logger.info(f"Loading dataset from {data_source}...")
    dataset = load_qa_from_folder(Path(data_source))
    logger.info(f"Loaded {len(dataset)} QA items")
    logger.info(f"Type distribution: {dataset.get_type_distribution()}")

    # 2. 추론 요청 생성
    prompts = create_inference_prompts(
        dataset,
        prompt_template=prompt_template,
        include_image=include_images,
    )

    requests = [
        InferenceRequest(
            id=p["id"],
            prompt=p["prompt"],
            ground_truth=p["ground_truth"],
            qa_type=p["qa_type"],
            image_paths=p.get("image_paths"),
        )
        for p in prompts
    ]

    # 3. 추론 클라이언트 생성
    client = get_client(provider, **client_kwargs)

    # 4. 추론 실행
    inference_output = None
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        inference_output = output_dir / "inference_results.json"

    responses = await run_inference(
        client,
        requests,
        output_path=inference_output,
    )

    # 5. 평가
    predictions = [
        {
            "id": r.id,
            "prediction": r.prediction,
            "ground_truth": r.ground_truth,
            "qa_type": r.qa_type,
        }
        for r in responses
    ]

    results, aggregated = evaluate_predictions(predictions)

    # 6. 리포트 생성 및 저장
    print_report(aggregated)

    if output_dir:
        report = generate_report(
            results,
            aggregated,
            metadata={
                "data_source": str(data_source),
                "provider": provider,
                "total_items": len(dataset),
                "client_config": {k: str(v) for k, v in client_kwargs.items()},
            }
        )

        report_path = output_dir / "evaluation_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, ensure_ascii=False, indent=2, fp=f)
        logger.info(f"Saved evaluation report to {report_path}")

    return results, aggregated


def evaluate_from_file(
    predictions_path: Path,
    ground_truth_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> tuple[List[EvalResult], AggregatedMetrics]:
    """
    파일에서 예측 결과를 로드하여 평가합니다.

    Args:
        predictions_path: 예측 결과 파일 경로
        ground_truth_path: 정답 파일 경로 (옵션)
        output_path: 리포트 저장 경로 (옵션)

    Returns:
        (개별 결과, 집계 메트릭)
    """
    # 예측 로드
    predictions = load_predictions(predictions_path)
    logger.info(f"Loaded {len(predictions)} predictions from {predictions_path}")

    # 정답 로드 (필요시)
    ground_truths = None
    if ground_truth_path:
        ground_truths = load_predictions(ground_truth_path)
        logger.info(f"Loaded {len(ground_truths)} ground truths from {ground_truth_path}")

    # 평가
    results, aggregated = evaluate_predictions(predictions, ground_truths)

    # 결과 출력
    print_report(aggregated)

    # 리포트 저장
    if output_path:
        report = generate_report(
            results,
            aggregated,
            metadata={
                "predictions_file": str(predictions_path),
                "ground_truth_file": str(ground_truth_path) if ground_truth_path else None,
            }
        )

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, ensure_ascii=False, indent=2, fp=f)
        logger.info(f"Saved evaluation report to {output_path}")

    return results, aggregated
