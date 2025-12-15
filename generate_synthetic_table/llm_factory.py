from __future__ import annotations

import os
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

# polling_gemini 모듈에서 GeminiPoolChatModel 임포트
from polling_gemini import GeminiPoolChatModel, create_gemini_chat_model


def get_llm(
    provider: str,
    model: str,
    temperature: float = 0.2,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    config_path: Optional[str] = None,
) -> BaseChatModel:
    """
    Factory to create a Chat Model based on the provider.

    Args:
        provider: 'openai', 'gemini', 'gemini_pool', or 'vllm'
        model: Model name (e.g., 'gpt-4', 'gemini-1.5-flash')
        temperature: Sampling temperature
        base_url: Optional base URL for vLLM or custom OpenAI endpoints
        api_key: Optional API key override
        config_path: Optional config path for gemini_pool (apis/gemini_keys.yaml)

    Returns:
        A configured LangChain Chat Model
    """
    provider = provider.lower()

    if provider == "openai":
        kwargs = {
            "model": model,
            "temperature": temperature,
            "base_url": base_url,
        }
        if api_key:
            kwargs["api_key"] = api_key

        return ChatOpenAI(**kwargs)

    elif provider == "gemini":
        if not os.getenv("GOOGLE_API_KEY") and not api_key:
             # Fallback or check environment variable in a more user-friendly way if needed
             pass
        
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=api_key, # type: ignore
        )

    elif provider == "gemini_pool":
        # polling_gemini를 사용한 API 키 풀링 지원
        # config_path가 지정되지 않으면 기본 경로(apis/gemini_keys.yaml) 사용
        return create_gemini_chat_model(
            config_path=config_path,
            temperature=temperature,
        )

    elif provider == "vllm":
        # vLLM is OpenAI-compatible
        if not base_url:
            # Default to local vLLM if not specified, though usually user should provide it
            base_url = "http://localhost:8000/v1"
        
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            base_url=base_url,
            api_key=api_key or "EMPTY", # vLLM often doesn't require a real key
        )

    else:
        raise ValueError(f"Unsupported provider: {provider}")
