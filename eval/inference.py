"""
Inference clients for Table QA evaluation.

vLLM, OpenAI API, 및 기타 LLM 서버에서 추론을 수행합니다.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class InferenceRequest:
    """추론 요청"""
    id: str
    prompt: str
    ground_truth: str
    qa_type: str
    image_paths: Optional[List[str]] = None


@dataclass
class InferenceResponse:
    """추론 응답"""
    id: str
    prediction: str
    ground_truth: str
    qa_type: str
    latency_ms: float
    error: Optional[str] = None


class InferenceClient(ABC):
    """추론 클라이언트 베이스 클래스"""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """단일 프롬프트에 대한 응답 생성"""
        pass

    @abstractmethod
    async def generate_batch(
        self,
        requests: List[InferenceRequest],
        **kwargs
    ) -> List[InferenceResponse]:
        """배치 추론"""
        pass


class VLLMClient(InferenceClient):
    """
    vLLM OpenAI-compatible API 클라이언트

    Usage:
        client = VLLMClient(base_url="http://localhost:8000/v1")
        responses = await client.generate_batch(requests)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        model: str = "default",
        api_key: str = "EMPTY",
        max_tokens: int = 512,
        temperature: float = 0.0,
        timeout: float = 60.0,
        max_concurrent: int = 10,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.max_concurrent = max_concurrent

        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

    async def generate(self, prompt: str, **kwargs) -> str:
        """단일 프롬프트에 대한 응답 생성"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {
                "model": kwargs.get("model", self.model),
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature),
            }

            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()

            return data["choices"][0]["message"]["content"]

    async def generate_batch(
        self,
        requests: List[InferenceRequest],
        show_progress: bool = True,
        **kwargs
    ) -> List[InferenceResponse]:
        """배치 추론 (동시성 제어)"""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        responses = []

        async def process_one(req: InferenceRequest, idx: int) -> InferenceResponse:
            async with semaphore:
                start_time = time.time()
                error = None
                prediction = ""

                try:
                    prediction = await self.generate(req.prompt, **kwargs)
                except Exception as e:
                    error = str(e)
                    logger.warning(f"Request {req.id} failed: {e}")

                latency = (time.time() - start_time) * 1000

                if show_progress:
                    logger.info(f"[{idx+1}/{len(requests)}] {req.id} - {latency:.0f}ms")

                return InferenceResponse(
                    id=req.id,
                    prediction=prediction,
                    ground_truth=req.ground_truth,
                    qa_type=req.qa_type,
                    latency_ms=latency,
                    error=error,
                )

        tasks = [process_one(req, i) for i, req in enumerate(requests)]
        responses = await asyncio.gather(*tasks)

        return list(responses)


class OpenAIClient(InferenceClient):
    """
    OpenAI API 클라이언트 (GPT-4 등)

    Usage:
        client = OpenAIClient(api_key="sk-...")
        responses = await client.generate_batch(requests)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        max_tokens: int = 512,
        temperature: float = 0.0,
        timeout: float = 60.0,
        max_concurrent: int = 5,
    ):
        import os
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.max_concurrent = max_concurrent

        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.base_url = "https://api.openai.com/v1"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    async def generate(
        self,
        prompt: str,
        image_paths: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """단일 프롬프트에 대한 응답 생성 (이미지 지원)"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            content = [{"type": "text", "text": prompt}]

            # 이미지 추가 (멀티모달)
            if image_paths:
                for img_path in image_paths:
                    img_data = self._encode_image(img_path)
                    if img_data:
                        content.append({
                            "type": "image_url",
                            "image_url": {"url": img_data}
                        })

            payload = {
                "model": kwargs.get("model", self.model),
                "messages": [{"role": "user", "content": content}],
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature),
            }

            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()

            return data["choices"][0]["message"]["content"]

    def _encode_image(self, image_path: str) -> Optional[str]:
        """이미지를 base64로 인코딩"""
        try:
            path = Path(image_path)
            if not path.exists():
                return None

            mime = "image/png"
            suffix = path.suffix.lower()
            if suffix in {".jpg", ".jpeg"}:
                mime = "image/jpeg"
            elif suffix == ".webp":
                mime = "image/webp"

            encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
            return f"data:{mime};base64,{encoded}"
        except Exception as e:
            logger.warning(f"Failed to encode image {image_path}: {e}")
            return None

    async def generate_batch(
        self,
        requests: List[InferenceRequest],
        show_progress: bool = True,
        **kwargs
    ) -> List[InferenceResponse]:
        """배치 추론"""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        responses = []

        async def process_one(req: InferenceRequest, idx: int) -> InferenceResponse:
            async with semaphore:
                start_time = time.time()
                error = None
                prediction = ""

                try:
                    prediction = await self.generate(
                        req.prompt,
                        image_paths=req.image_paths,
                        **kwargs
                    )
                except Exception as e:
                    error = str(e)
                    logger.warning(f"Request {req.id} failed: {e}")

                latency = (time.time() - start_time) * 1000

                if show_progress:
                    logger.info(f"[{idx+1}/{len(requests)}] {req.id} - {latency:.0f}ms")

                return InferenceResponse(
                    id=req.id,
                    prediction=prediction,
                    ground_truth=req.ground_truth,
                    qa_type=req.qa_type,
                    latency_ms=latency,
                    error=error,
                )

        tasks = [process_one(req, i) for i, req in enumerate(requests)]
        responses = await asyncio.gather(*tasks)

        return list(responses)


class AnthropicClient(InferenceClient):
    """
    Anthropic Claude API 클라이언트

    Usage:
        client = AnthropicClient(api_key="sk-ant-...")
        responses = await client.generate_batch(requests)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 512,
        temperature: float = 0.0,
        timeout: float = 60.0,
        max_concurrent: int = 5,
    ):
        import os
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.max_concurrent = max_concurrent

        if not self.api_key:
            raise ValueError("Anthropic API key is required")

        self.base_url = "https://api.anthropic.com/v1"
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

    async def generate(
        self,
        prompt: str,
        image_paths: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """단일 프롬프트에 대한 응답 생성"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            content = []

            # 이미지 추가
            if image_paths:
                for img_path in image_paths:
                    img_data = self._encode_image(img_path)
                    if img_data:
                        content.append(img_data)

            content.append({"type": "text", "text": prompt})

            payload = {
                "model": kwargs.get("model", self.model),
                "messages": [{"role": "user", "content": content}],
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature),
            }

            response = await client.post(
                f"{self.base_url}/messages",
                json=payload,
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()

            return data["content"][0]["text"]

    def _encode_image(self, image_path: str) -> Optional[Dict[str, Any]]:
        """이미지를 Anthropic 형식으로 인코딩"""
        try:
            path = Path(image_path)
            if not path.exists():
                return None

            media_type = "image/png"
            suffix = path.suffix.lower()
            if suffix in {".jpg", ".jpeg"}:
                media_type = "image/jpeg"
            elif suffix == ".webp":
                media_type = "image/webp"
            elif suffix == ".gif":
                media_type = "image/gif"

            encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": encoded,
                }
            }
        except Exception as e:
            logger.warning(f"Failed to encode image {image_path}: {e}")
            return None

    async def generate_batch(
        self,
        requests: List[InferenceRequest],
        show_progress: bool = True,
        **kwargs
    ) -> List[InferenceResponse]:
        """배치 추론"""
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def process_one(req: InferenceRequest, idx: int) -> InferenceResponse:
            async with semaphore:
                start_time = time.time()
                error = None
                prediction = ""

                try:
                    prediction = await self.generate(
                        req.prompt,
                        image_paths=req.image_paths,
                        **kwargs
                    )
                except Exception as e:
                    error = str(e)
                    logger.warning(f"Request {req.id} failed: {e}")

                latency = (time.time() - start_time) * 1000

                if show_progress:
                    logger.info(f"[{idx+1}/{len(requests)}] {req.id} - {latency:.0f}ms")

                return InferenceResponse(
                    id=req.id,
                    prediction=prediction,
                    ground_truth=req.ground_truth,
                    qa_type=req.qa_type,
                    latency_ms=latency,
                    error=error,
                )

        tasks = [process_one(req, i) for i, req in enumerate(requests)]
        responses = await asyncio.gather(*tasks)

        return list(responses)


def get_client(
    provider: str,
    **kwargs
) -> InferenceClient:
    """
    제공자에 따른 클라이언트 생성

    Args:
        provider: "vllm", "openai", "anthropic"
        **kwargs: 클라이언트별 설정

    Returns:
        InferenceClient 인스턴스
    """
    provider = provider.lower()

    if provider == "vllm":
        return VLLMClient(**kwargs)
    elif provider == "openai":
        return OpenAIClient(**kwargs)
    elif provider in ["anthropic", "claude"]:
        return AnthropicClient(**kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")


async def run_inference(
    client: InferenceClient,
    requests: List[InferenceRequest],
    output_path: Optional[Path] = None,
    **kwargs
) -> List[InferenceResponse]:
    """
    추론을 실행하고 결과를 저장합니다.

    Args:
        client: 추론 클라이언트
        requests: 추론 요청 리스트
        output_path: 결과 저장 경로 (옵션)
        **kwargs: 추가 설정

    Returns:
        InferenceResponse 리스트
    """
    logger.info(f"Running inference on {len(requests)} requests...")

    responses = await client.generate_batch(requests, **kwargs)

    # 통계
    success_count = sum(1 for r in responses if r.error is None)
    avg_latency = sum(r.latency_ms for r in responses) / len(responses) if responses else 0

    logger.info(f"Completed: {success_count}/{len(responses)} successful")
    logger.info(f"Average latency: {avg_latency:.0f}ms")

    # 결과 저장
    if output_path:
        output_data = {
            "total": len(responses),
            "success": success_count,
            "avg_latency_ms": avg_latency,
            "responses": [
                {
                    "id": r.id,
                    "prediction": r.prediction,
                    "ground_truth": r.ground_truth,
                    "qa_type": r.qa_type,
                    "latency_ms": r.latency_ms,
                    "error": r.error,
                }
                for r in responses
            ],
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, ensure_ascii=False, indent=2, fp=f)

        logger.info(f"Saved results to {output_path}")

    return responses
