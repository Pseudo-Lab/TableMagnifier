"""
Evaluation metrics for Table QA.

다양한 평가 메트릭을 계산합니다:
- Exact Match (EM)
- F1 Score (token-level)
- BLEU Score
- Contains Match (포함 여부)
"""

from __future__ import annotations

import re
import string
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from collections import Counter

logger = logging.getLogger(__name__)


def normalize_answer(text: str) -> str:
    """
    정답 텍스트를 정규화합니다.

    - 소문자 변환
    - 구두점 제거
    - 관사 제거 (영어)
    - 공백 정규화
    - 한국어 조사 처리
    """
    if not text:
        return ""

    text = str(text).lower()

    # 구두점 제거
    text = text.translate(str.maketrans("", "", string.punctuation))

    # 영어 관사 제거
    text = re.sub(r"\b(a|an|the)\b", " ", text)

    # 한국어 종결어미 정규화
    text = re.sub(r"(입니다|습니다|니다|예요|이에요|에요)\.?$", "", text)
    text = re.sub(r"(이다|다)\.?$", "", text)

    # 공백 정규화
    text = " ".join(text.split())

    return text.strip()


def get_tokens(text: str) -> List[str]:
    """텍스트를 토큰으로 분리 (공백 기반)"""
    normalized = normalize_answer(text)
    return normalized.split() if normalized else []


def exact_match(prediction: str, ground_truth: str) -> float:
    """
    Exact Match 점수를 계산합니다.

    Args:
        prediction: 예측 답변
        ground_truth: 정답

    Returns:
        1.0 (일치) 또는 0.0 (불일치)
    """
    return float(normalize_answer(prediction) == normalize_answer(ground_truth))


def contains_match(prediction: str, ground_truth: str) -> float:
    """
    정답이 예측에 포함되어 있는지 확인합니다.

    Args:
        prediction: 예측 답변
        ground_truth: 정답

    Returns:
        1.0 (포함) 또는 0.0 (미포함)
    """
    pred_norm = normalize_answer(prediction)
    gt_norm = normalize_answer(ground_truth)
    return float(gt_norm in pred_norm or pred_norm in gt_norm)


def f1_score(prediction: str, ground_truth: str) -> float:
    """
    Token-level F1 점수를 계산합니다.

    Args:
        prediction: 예측 답변
        ground_truth: 정답

    Returns:
        F1 점수 (0.0 ~ 1.0)
    """
    pred_tokens = get_tokens(prediction)
    gt_tokens = get_tokens(ground_truth)

    if not pred_tokens and not gt_tokens:
        return 1.0
    if not pred_tokens or not gt_tokens:
        return 0.0

    common = Counter(pred_tokens) & Counter(gt_tokens)
    num_common = sum(common.values())

    if num_common == 0:
        return 0.0

    precision = num_common / len(pred_tokens)
    recall = num_common / len(gt_tokens)
    f1 = (2 * precision * recall) / (precision + recall)

    return f1


def bleu_score(prediction: str, ground_truth: str, max_n: int = 4) -> float:
    """
    간단한 BLEU 점수를 계산합니다.

    Args:
        prediction: 예측 답변
        ground_truth: 정답
        max_n: 최대 n-gram 크기

    Returns:
        BLEU 점수 (0.0 ~ 1.0)
    """
    pred_tokens = get_tokens(prediction)
    gt_tokens = get_tokens(ground_truth)

    if not pred_tokens or not gt_tokens:
        return 0.0

    # Brevity penalty
    bp = min(1.0, len(pred_tokens) / len(gt_tokens)) if gt_tokens else 0.0

    # N-gram precision
    precisions = []
    for n in range(1, min(max_n + 1, len(pred_tokens) + 1)):
        pred_ngrams = Counter(
            tuple(pred_tokens[i:i+n]) for i in range(len(pred_tokens) - n + 1)
        )
        gt_ngrams = Counter(
            tuple(gt_tokens[i:i+n]) for i in range(len(gt_tokens) - n + 1)
        )

        matches = sum((pred_ngrams & gt_ngrams).values())
        total = sum(pred_ngrams.values())

        if total > 0:
            precisions.append(matches / total)
        else:
            precisions.append(0.0)

    if not precisions or all(p == 0 for p in precisions):
        return 0.0

    # Geometric mean of precisions
    import math
    log_precisions = [math.log(p) if p > 0 else -float('inf') for p in precisions]
    avg_log_precision = sum(log_precisions) / len(log_precisions)

    if avg_log_precision == -float('inf'):
        return 0.0

    bleu = bp * math.exp(avg_log_precision)
    return bleu


def numeric_match(prediction: str, ground_truth: str, tolerance: float = 0.01) -> float:
    """
    숫자 값의 일치 여부를 확인합니다.

    Args:
        prediction: 예측 답변
        ground_truth: 정답
        tolerance: 허용 오차 (상대적)

    Returns:
        1.0 (일치) 또는 0.0 (불일치)
    """
    # 숫자 추출
    pred_numbers = re.findall(r'[\d,]+\.?\d*', prediction.replace(',', ''))
    gt_numbers = re.findall(r'[\d,]+\.?\d*', ground_truth.replace(',', ''))

    if not pred_numbers or not gt_numbers:
        return 0.0

    try:
        pred_val = float(pred_numbers[0].replace(',', ''))
        gt_val = float(gt_numbers[0].replace(',', ''))

        if gt_val == 0:
            return float(pred_val == 0)

        rel_diff = abs(pred_val - gt_val) / abs(gt_val)
        return float(rel_diff <= tolerance)
    except (ValueError, IndexError):
        return 0.0


@dataclass
class EvalResult:
    """단일 평가 결과"""
    id: str
    prediction: str
    ground_truth: str
    qa_type: str
    exact_match: float
    f1_score: float
    contains_match: float
    bleu_score: float = 0.0
    numeric_match: Optional[float] = None
    # LLM-as-Judge 결과
    judge_correctness: Optional[float] = None
    judge_completeness: Optional[float] = None
    judge_relevance: Optional[float] = None
    judge_overall_score: Optional[float] = None
    judge_is_correct: Optional[bool] = None
    judge_explanation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "prediction": self.prediction,
            "ground_truth": self.ground_truth,
            "qa_type": self.qa_type,
            "exact_match": self.exact_match,
            "f1_score": self.f1_score,
            "contains_match": self.contains_match,
            "bleu_score": self.bleu_score,
        }
        if self.numeric_match is not None:
            result["numeric_match"] = self.numeric_match
        if self.judge_overall_score is not None:
            result["judge_correctness"] = self.judge_correctness
            result["judge_completeness"] = self.judge_completeness
            result["judge_relevance"] = self.judge_relevance
            result["judge_overall_score"] = self.judge_overall_score
            result["judge_is_correct"] = self.judge_is_correct
            result["judge_explanation"] = self.judge_explanation
        return result


@dataclass
class AggregatedMetrics:
    """집계된 메트릭"""
    total_count: int = 0
    exact_match_avg: float = 0.0
    f1_score_avg: float = 0.0
    contains_match_avg: float = 0.0
    bleu_score_avg: float = 0.0
    judge_overall_avg: Optional[float] = None
    judge_correctness_avg: Optional[float] = None
    judge_completeness_avg: Optional[float] = None
    judge_relevance_avg: Optional[float] = None
    judge_accuracy: Optional[float] = None  # judge_is_correct의 비율
    by_type: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "total_count": self.total_count,
            "exact_match": self.exact_match_avg,
            "f1_score": self.f1_score_avg,
            "contains_match": self.contains_match_avg,
            "bleu_score": self.bleu_score_avg,
            "by_type": self.by_type,
        }
        if self.judge_overall_avg is not None:
            result["judge_overall_avg"] = self.judge_overall_avg
            result["judge_correctness_avg"] = self.judge_correctness_avg
            result["judge_completeness_avg"] = self.judge_completeness_avg
            result["judge_relevance_avg"] = self.judge_relevance_avg
            result["judge_accuracy"] = self.judge_accuracy
        return result


def compute_metrics(
    prediction: str,
    ground_truth: str,
    qa_type: str,
    id: str = "",
) -> EvalResult:
    """
    단일 예측에 대한 모든 메트릭을 계산합니다.

    Args:
        prediction: 예측 답변
        ground_truth: 정답
        qa_type: QA 유형
        id: 항목 ID

    Returns:
        EvalResult
    """
    em = exact_match(prediction, ground_truth)
    f1 = f1_score(prediction, ground_truth)
    cm = contains_match(prediction, ground_truth)
    bleu = bleu_score(prediction, ground_truth)

    # 계산 유형의 경우 숫자 매칭도 확인
    num_match = None
    if qa_type in ["calculation", "arithmetic", "aggregate"]:
        num_match = numeric_match(prediction, ground_truth)

    return EvalResult(
        id=id,
        prediction=prediction,
        ground_truth=ground_truth,
        qa_type=qa_type,
        exact_match=em,
        f1_score=f1,
        contains_match=cm,
        bleu_score=bleu,
        numeric_match=num_match,
    )


def aggregate_metrics(results: List[EvalResult]) -> AggregatedMetrics:
    """
    여러 평가 결과를 집계합니다.

    Args:
        results: EvalResult 리스트

    Returns:
        AggregatedMetrics
    """
    if not results:
        return AggregatedMetrics()

    total = len(results)
    em_sum = sum(r.exact_match for r in results)
    f1_sum = sum(r.f1_score for r in results)
    cm_sum = sum(r.contains_match for r in results)
    bleu_sum = sum(r.bleu_score for r in results)

    # LLM-as-Judge 메트릭 집계
    judge_results = [r for r in results if r.judge_overall_score is not None]
    judge_overall_avg = None
    judge_correctness_avg = None
    judge_completeness_avg = None
    judge_relevance_avg = None
    judge_accuracy = None
    
    if judge_results:
        judge_overall_avg = sum(r.judge_overall_score for r in judge_results) / len(judge_results)
        judge_correctness_avg = sum(r.judge_correctness for r in judge_results) / len(judge_results)
        judge_completeness_avg = sum(r.judge_completeness for r in judge_results) / len(judge_results)
        judge_relevance_avg = sum(r.judge_relevance for r in judge_results) / len(judge_results)
        judge_accuracy = sum(1 for r in judge_results if r.judge_is_correct) / len(judge_results)

    # 유형별 집계
    by_type: Dict[str, Dict[str, List[float]]] = {}
    for r in results:
        if r.qa_type not in by_type:
            by_type[r.qa_type] = {
                "exact_match": [],
                "f1_score": [],
                "contains_match": [],
                "count": 0,
            }
        by_type[r.qa_type]["exact_match"].append(r.exact_match)
        by_type[r.qa_type]["f1_score"].append(r.f1_score)
        by_type[r.qa_type]["contains_match"].append(r.contains_match)
        by_type[r.qa_type]["count"] += 1

    # 유형별 평균 계산
    type_metrics = {}
    for qa_type, metrics in by_type.items():
        count = metrics["count"]
        type_metrics[qa_type] = {
            "count": count,
            "exact_match": sum(metrics["exact_match"]) / count if count > 0 else 0.0,
            "f1_score": sum(metrics["f1_score"]) / count if count > 0 else 0.0,
            "contains_match": sum(metrics["contains_match"]) / count if count > 0 else 0.0,
        }

    return AggregatedMetrics(
        total_count=total,
        exact_match_avg=em_sum / total,
        f1_score_avg=f1_sum / total,
        contains_match_avg=cm_sum / total,
        bleu_score_avg=bleu_sum / total,
        judge_overall_avg=judge_overall_avg,
        judge_correctness_avg=judge_correctness_avg,
        judge_completeness_avg=judge_completeness_avg,
        judge_relevance_avg=judge_relevance_avg,
        judge_accuracy=judge_accuracy,
        by_type=type_metrics,
    )
