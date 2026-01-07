"""
LLM-as-Judge 평가 모듈

예측 답변과 정답을 비교하여 의미적 정확도를 평가합니다.
"""

from __future__ import annotations

import json
import logging
import asyncio
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path

from .inference import InferenceClient, get_client, InferenceRequest

logger = logging.getLogger(__name__)


# LLM-as-Judge 프롬프트 템플릿
JUDGE_PROMPT_TEMPLATE = """다음 질문에 대한 모델의 예측 답변과 정답을 비교하여 평가해주세요.

## 질문
{question}

## 정답
{ground_truth}

## 모델 예측 답변
{prediction}

## 평가 기준
1. **정확성 (Correctness)**: 예측 답변이 정답과 의미적으로 일치하는가?
   - 완전 일치: 1.0
   - 부분 일치 (핵심 내용은 맞지만 표현이 다름): 0.5-0.9
   - 관련 있지만 부정확: 0.1-0.4
   - 완전히 틀림: 0.0

2. **완전성 (Completeness)**: 정답의 모든 정보를 포함하는가?
   - 모든 정보 포함: 1.0
   - 일부 정보 포함: 0.3-0.7
   - 핵심 정보 누락: 0.0-0.2

3. **관련성 (Relevance)**: 답변이 질문과 관련이 있는가?
   - 매우 관련 있음: 1.0
   - 관련 있음: 0.5-0.9
   - 관련 없음: 0.0-0.4

## 출력 형식 (JSON)
다음 형식으로 평가 결과를 출력해주세요:
```json
{{
    "correctness": 0.0-1.0,
    "completeness": 0.0-1.0,
    "relevance": 0.0-1.0,
    "overall_score": 0.0-1.0,
    "is_correct": true/false,
    "explanation": "평가 근거 설명"
}}
```

평가 결과만 출력해주세요."""


@dataclass
class JudgeResult:
    """LLM-as-Judge 평가 결과"""
    id: str
    correctness: float  # 0.0-1.0
    completeness: float  # 0.0-1.0
    relevance: float  # 0.0-1.0
    overall_score: float  # 0.0-1.0
    is_correct: bool
    explanation: str
    error: Optional[str] = None


def parse_judge_response(response: str) -> Optional[Dict[str, Any]]:
    """LLM 응답을 파싱하여 평가 결과 추출"""
    try:
        # JSON 코드 블록 제거
        response = response.strip()
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            response = response[start:end].strip()
        
        # JSON 파싱
        result = json.loads(response)
        return result
    except Exception as e:
        logger.warning(f"Failed to parse judge response: {e}\nResponse: {response[:200]}")
        return None


async def judge_single_answer(
    client: InferenceClient,
    question: str,
    ground_truth: str,
    prediction: str,
    item_id: str = "",
) -> JudgeResult:
    """
    단일 답변을 LLM-as-Judge로 평가합니다.
    
    Args:
        client: 추론 클라이언트
        question: 질문
        ground_truth: 정답
        prediction: 예측 답변
        item_id: 항목 ID
    
    Returns:
        JudgeResult
    """
    prompt = JUDGE_PROMPT_TEMPLATE.format(
        question=question,
        ground_truth=ground_truth,
        prediction=prediction,
    )
    
    try:
        response_text = await client.generate(prompt)
        result = parse_judge_response(response_text)
        
        if result:
            return JudgeResult(
                id=item_id,
                correctness=float(result.get("correctness", 0.0)),
                completeness=float(result.get("completeness", 0.0)),
                relevance=float(result.get("relevance", 0.0)),
                overall_score=float(result.get("overall_score", 0.0)),
                is_correct=bool(result.get("is_correct", False)),
                explanation=str(result.get("explanation", "")),
            )
        else:
            return JudgeResult(
                id=item_id,
                correctness=0.0,
                completeness=0.0,
                relevance=0.0,
                overall_score=0.0,
                is_correct=False,
                explanation="Failed to parse judge response",
                error="Parse error",
            )
    except Exception as e:
        logger.error(f"Judge evaluation failed for {item_id}: {e}")
        return JudgeResult(
            id=item_id,
            correctness=0.0,
            completeness=0.0,
            relevance=0.0,
            overall_score=0.0,
            is_correct=False,
            explanation="",
            error=str(e),
        )


async def judge_batch(
    client: InferenceClient,
    items: List[Dict[str, Any]],
    max_concurrent: int = 5,
    show_progress: bool = True,
) -> List[JudgeResult]:
    """
    배치로 답변들을 LLM-as-Judge로 평가합니다.
    
    Args:
        client: 추론 클라이언트
        items: 평가할 항목 리스트
            [{"id": "...", "question": "...", "ground_truth": "...", "prediction": "..."}]
        max_concurrent: 최대 동시 요청 수
        show_progress: 진행 상황 출력 여부
    
    Returns:
        JudgeResult 리스트
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    results = []
    
    async def judge_one(item: Dict[str, Any], idx: int) -> JudgeResult:
        async with semaphore:
            result = await judge_single_answer(
                client=client,
                question=item.get("question", ""),
                ground_truth=item.get("ground_truth", ""),
                prediction=item.get("prediction", ""),
                item_id=item.get("id", f"item_{idx}"),
            )
            
            if show_progress:
                logger.info(
                    f"[Judge {idx+1}/{len(items)}] {result.id} - "
                    f"Score: {result.overall_score:.2f}, "
                    f"Correct: {result.is_correct}"
                )
            
            return result
    
    tasks = [judge_one(item, i) for i, item in enumerate(items)]
    results = await asyncio.gather(*tasks)
    
    return list(results)


def create_judge_client(
    provider: str = "openai",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs
) -> InferenceClient:
    """
    LLM-as-Judge용 클라이언트를 생성합니다.
    
    Args:
        provider: 제공자 (openai, anthropic, vllm)
        model: 모델 이름
        api_key: API 키
        **kwargs: 추가 설정
    
    Returns:
        InferenceClient
    """
    judge_kwargs = {
        "max_tokens": kwargs.get("max_tokens", 512),
        "temperature": kwargs.get("temperature", 0.0),
        "max_concurrent": kwargs.get("max_concurrent", 5),
    }
    
    if provider == "openai":
        judge_kwargs["model"] = model or "gpt-4o-mini"
        if api_key:
            judge_kwargs["api_key"] = api_key
    elif provider in ["anthropic", "claude"]:
        judge_kwargs["model"] = model or "claude-sonnet-4-20250514"
        if api_key:
            judge_kwargs["api_key"] = api_key
    elif provider == "vllm":
        judge_kwargs["base_url"] = kwargs.get("base_url", "http://localhost:8000/v1")
        judge_kwargs["model"] = model or "default"
        judge_kwargs["api_key"] = api_key or "EMPTY"
    
    return get_client(provider, **judge_kwargs)

