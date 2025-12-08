from __future__ import annotations

import os
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI


def get_llm(
    provider: str,
    model: str,
    temperature: float = 0.2,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> BaseChatModel:
    """
    Factory to create a Chat Model based on the provider.

    Args:
        provider: 'openai', 'gemini', or 'vllm'
        model: Model name (e.g., 'gpt-4', 'gemini-1.5-flash')
        temperature: Sampling temperature
        base_url: Optional base URL for vLLM or custom OpenAI endpoints
        api_key: Optional API key override

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
        
        # Use polling_gemini for robust API key management
        from polling_gemini.langgraph_integration import create_gemini_chat_model
        
        return create_gemini_chat_model(
            model=model,
            temperature=temperature,
            # google_api_key is handled by the pool config, but if passed explicitly we might want to respect it?
            # The current pool implementation relies on config file. 
            # If api_key is provided here, it might be ignored by the pool wrapper or needs adaptation.
            # For now, we assume the user relies on the pool's config if they choose 'gemini' provider 
            # in this new setup.
            # If specific api_key is needed, it might be better to use google_genai directly or add support in wrapper.
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
