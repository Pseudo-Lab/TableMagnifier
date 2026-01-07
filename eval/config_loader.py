"""
설정 파일 로더

vLLM 설정을 JSON 파일에서 로드합니다.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


DEFAULT_CONFIG_PATH = Path(__file__).parent / "vllm_config.json"


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    설정 파일을 로드합니다.
    
    Args:
        config_path: 설정 파일 경로 (None이면 기본 경로 사용)
    
    Returns:
        설정 딕셔너리
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        logger.warning(f"Config file not found: {config_path}, using defaults")
        return get_default_config()
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # 기본값 병합
        default = get_default_config()
        config = merge_config(default, config)
        
        logger.info(f"Loaded config from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        logger.info("Using default config")
        return get_default_config()


def get_default_config() -> Dict[str, Any]:
    """기본 설정을 반환합니다."""
    return {
        "base_url": "http://localhost:8000/v1",
        "model": "default",
        "api_key": "EMPTY",
        "max_tokens": 512,
        "temperature": 0.0,
        "max_concurrent": 10,
        "judge": {
            "enabled": False,
            "provider": "vllm",
            "model": "default",
            "base_url": "http://localhost:8000/v1",
            "api_key": "EMPTY",
            "max_tokens": 512,
            "temperature": 0.0,
            "max_concurrent": 5,
        }
    }


def merge_config(default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """기본 설정과 사용자 설정을 병합합니다."""
    merged = default.copy()
    
    for key, value in user.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_config(merged[key], value)
        else:
            merged[key] = value
    
    return merged


def get_inference_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """추론용 설정을 추출합니다."""
    return {
        "base_url": config.get("base_url", "http://localhost:8000/v1"),
        "model": config.get("model", "default"),
        "api_key": config.get("api_key", "EMPTY"),
        "max_tokens": config.get("max_tokens", 512),
        "temperature": config.get("temperature", 0.0),
        "max_concurrent": config.get("max_concurrent", 10),
    }


def get_judge_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Judge용 설정을 추출합니다."""
    judge_config = config.get("judge", {})
    
    return {
        "enabled": judge_config.get("enabled", False),
        "provider": judge_config.get("provider", "vllm"),
        "model": judge_config.get("model", config.get("model", "default")),
        "base_url": judge_config.get("base_url", config.get("base_url", "http://localhost:8000/v1")),
        "api_key": judge_config.get("api_key", config.get("api_key", "EMPTY")),
        "max_tokens": judge_config.get("max_tokens", 512),
        "temperature": judge_config.get("temperature", 0.0),
        "max_concurrent": judge_config.get("max_concurrent", 5),
    }

