"""
TableMagnifier Evaluation Module

vLLM 및 기타 LLM 서버에서 Table QA 성능을 평가하기 위한 모듈
"""

from .dataset import (
    QAItem,
    EvalDataset,
    load_qa_from_file,
    load_qa_from_folder,
    create_eval_dataset,
)
from .metrics import (
    exact_match,
    f1_score,
    normalize_answer,
    compute_metrics,
    EvalResult,
)
from .inference import (
    InferenceClient,
    VLLMClient,
    OpenAIClient,
    run_inference,
)
from .evaluate import (
    evaluate_predictions,
    run_evaluation,
)

__all__ = [
    # Dataset
    "QAItem",
    "EvalDataset",
    "load_qa_from_file",
    "load_qa_from_folder",
    "create_eval_dataset",
    # Metrics
    "exact_match",
    "f1_score",
    "normalize_answer",
    "compute_metrics",
    "EvalResult",
    # Inference
    "InferenceClient",
    "VLLMClient",
    "OpenAIClient",
    "run_inference",
    # Evaluate
    "evaluate_predictions",
    "run_evaluation",
]
