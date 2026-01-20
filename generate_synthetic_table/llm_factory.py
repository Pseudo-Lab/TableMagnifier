from __future__ import annotations

import os
import yaml
from pathlib import Path
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic

# polling_gemini 모듈에서 GeminiPoolChatModel 임포트
from polling_gemini import GeminiPoolChatModel, create_gemini_chat_model


def _load_azure_config_from_yaml(config_path: Optional[str] = None) -> dict:
    """Load Azure OpenAI configuration from gemini_keys.yaml file."""
    if not config_path:
        config_path = "apis/gemini_keys.yaml"
    
    config_file = Path(config_path)
    if not config_file.exists():
        return {}
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return {
            'api_key': config.get('AZURE_OPENAI_API_KEY'),
            'endpoint': config.get('AZURE_OPENAI_ENDPOINT'),
            'api_version': config.get('AZURE_OPENAI_API_VERSION'),
            'deployment': config.get('AZURE_OPENAI_DEPLOYMENT_NAME'),
        }
    except Exception:
        return {}


def get_llm(
    provider: str,
    model: str,
    temperature: float = 0.2,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    config_path: Optional[str] = None,
    azure_deployment: Optional[str] = None,
    azure_endpoint: Optional[str] = None,
) -> BaseChatModel:
    """
    Factory to create a Chat Model based on the provider.

    Args:
        provider: 'openai', 'azure', 'gemini', 'gemini_pool', 'claude', or 'vllm'
        model: Model name (e.g., 'gpt-4', 'gemini-1.5-flash', 'claude-sonnet-4-20250514')
        temperature: Sampling temperature
        base_url: Optional base URL for vLLM or custom OpenAI endpoints
        api_key: Optional API key override
        config_path: Optional config path for gemini_pool (apis/gemini_keys.yaml)
        azure_deployment: Azure OpenAI deployment name (required for azure provider)
        azure_endpoint: Azure OpenAI endpoint URL (required for azure provider)

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

    elif provider == "azure":
        # Azure OpenAI
        # 우선순위: CLI 파라미터 > config_path의 yaml 파일 > 환경변수
        yaml_config = _load_azure_config_from_yaml(config_path)
        
        azure_key = api_key or yaml_config.get('api_key') or os.getenv("AZURE_OPENAI_API_KEY")
        azure_ep = azure_endpoint or yaml_config.get('endpoint') or os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_dep = azure_deployment or yaml_config.get('deployment') or model
        azure_ver = yaml_config.get('api_version') or os.getenv("AZURE_OPENAI_API_VERSION") or "2024-02-15-preview"
        
        if not azure_key or not azure_ep:
            raise ValueError(
                "Azure OpenAI requires AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT. "
                "Set via environment variables, --azure-* arguments, or in apis/gemini_keys.yaml."
            )
        
        return AzureChatOpenAI(
            azure_deployment=azure_dep,
            azure_endpoint=azure_ep,
            api_key=azure_key,
            api_version=azure_ver,
            temperature=temperature,
        )

    elif provider == "claude":
        # Anthropic Claude API
        # ANTHROPIC_API_KEY 환경변수 또는 api_key 파라미터 사용
        anthropic_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        return ChatAnthropic(
            model=model,
            temperature=temperature,
            api_key=anthropic_key,
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
