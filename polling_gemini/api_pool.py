"""
Gemini API Pool Manager
여러 개의 Gemini API 키를 로테이션하며 사용하는 풀링 시스템
무료 사용량이 끝나면 자동으로 다음 API 키로 전환
"""

import os
import yaml
import time
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class APIKeyInfo:
    """API 키 정보를 저장하는 데이터 클래스"""
    key: str
    name: str
    enabled: bool
    failed_count: int = 0
    last_error: Optional[str] = None


class GeminiAPIPool:
    """
    Gemini API 키 풀링 매니저
    
    여러 개의 API 키를 관리하고, 사용량 제한이나 에러 발생 시
    자동으로 다음 키로 전환합니다.
    """
    
    # 리소스 소진 관련 에러 코드들
    QUOTA_ERRORS = [
        'RESOURCE_EXHAUSTED',
        'QUOTA_EXCEEDED',
        'RATE_LIMIT_EXCEEDED',
        'TOO_MANY_REQUESTS',
    ]
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Args:
            config_path: API 키 설정 파일 경로. None이면 기본 경로 사용
        """
        if config_path is None:
            # 기본 경로: apis/gemini_keys.yaml
            base_dir = Path(__file__).parent.parent
            config_path = base_dir / "apis" / "gemini_keys.yaml"
        
        self.config_path = Path(config_path)
        self.api_keys: List[APIKeyInfo] = []
        self.current_key_index: int = 0
        self.settings: Dict[str, Any] = {}
        self.current_model = None
        
        self._load_config()
        self._initialize_current_key()
    
    def _load_config(self):
        """YAML 설정 파일 로드"""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"API 키 설정 파일을 찾을 수 없습니다: {self.config_path}\n"
                f"apis/gemini_keys.yaml 파일을 생성하고 API 키를 입력하세요."
            )
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # API 키 정보 로드
        for key_config in config.get('api_keys', []):
            if key_config.get('enabled', True):
                api_key_info = APIKeyInfo(
                    key=key_config['key'],
                    name=key_config.get('name', 'unknown'),
                    enabled=True
                )
                self.api_keys.append(api_key_info)
        
        if not self.api_keys:
            raise ValueError("활성화된 API 키가 없습니다. gemini_keys.yaml을 확인하세요.")
        
        # 설정 로드
        self.settings = config.get('settings', {})
        logger.info(f"총 {len(self.api_keys)}개의 API 키를 로드했습니다.")
    
    def _initialize_current_key(self):
        """현재 API 키로 Gemini 모델 초기화"""
        current_key = self.api_keys[self.current_key_index]
        genai.configure(api_key=current_key.key)
        
        model_name = self.settings.get('model', 'gemini-1.5-flash')
        self.current_model = genai.GenerativeModel(model_name)
        
        logger.info(f"API 키 '{current_key.name}' 사용 중 (모델: {model_name})")
    
    def _rotate_key(self) -> bool:
        """
        다음 API 키로 전환
        
        Returns:
            성공 여부 (모든 키를 시도했으면 False)
        """
        original_index = self.current_key_index
        
        # 다음 키로 이동
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        
        # 모든 키를 한 바퀴 돌았는지 확인
        if self.current_key_index == original_index:
            logger.error("모든 API 키가 사용 불가능합니다.")
            return False
        
        try:
            self._initialize_current_key()
            return True
        except Exception as e:
            logger.error(f"키 전환 실패: {e}")
            # 재귀적으로 다음 키 시도
            return self._rotate_key()
    
    def _is_quota_error(self, error: Exception) -> bool:
        """에러가 할당량 관련 에러인지 확인"""
        error_str = str(error).upper()
        return any(quota_err in error_str for quota_err in self.QUOTA_ERRORS)
    
    def generate_content(
        self,
        prompt: str,
        return_full_response: bool = False,
        **kwargs
    ) -> str:
        """
        Gemini API로 컨텐츠 생성 (자동 키 로테이션 포함)
        
        Args:
            prompt: 입력 프롬프트
            return_full_response: True면 (text, usage_metadata) 튜플 반환
            **kwargs: GenerativeModel.generate_content에 전달할 추가 인자
            
        Returns:
            생성된 텍스트, 또는 (텍스트, usage_metadata) 튜플
            
        Raises:
            Exception: 모든 API 키로 시도했으나 실패한 경우
        """
        max_retries = self.settings.get('max_retries', 3)
        retry_delay = self.settings.get('retry_delay', 2)
        
        last_error = None
        attempts = 0
        max_attempts = len(self.api_keys) * max_retries
        
        while attempts < max_attempts:
            current_key = self.api_keys[self.current_key_index]
            
            try:
                # kwargs에서 temperature 추출 (있으면 사용, 없으면 설정값 사용)
                temperature = kwargs.pop('temperature', self.settings.get('temperature', 0.7))
                
                # generation_config 구성
                generation_config = {
                    'temperature': temperature,
                }
                generation_config.update(kwargs.pop('generation_config', {}))
                
                # API 호출 (generation_config만 전달)
                response = self.current_model.generate_content(
                    prompt, 
                    generation_config=generation_config
                )
                
                # 성공 시 실패 카운트 리셋
                current_key.failed_count = 0
                current_key.last_error = None
                
                if return_full_response:
                    # usage_metadata 추출
                    usage_metadata = getattr(response, 'usage_metadata', None)
                    return response.text, usage_metadata
                return response.text
                
            except google_exceptions.ResourceExhausted as e:
                # 할당량 초과 - 즉시 키 로테이션
                logger.warning(f"API 키 '{current_key.name}' 할당량 초과. 다음 키로 전환합니다.")
                current_key.failed_count += 1
                current_key.last_error = str(e)
                last_error = e
                
                if not self._rotate_key():
                    break
                    
            except Exception as e:
                # 기타 에러
                logger.warning(f"API 호출 실패 (키: {current_key.name}): {e}")
                current_key.failed_count += 1
                current_key.last_error = str(e)
                last_error = e
                
                # 할당량 관련 에러인 경우 키 로테이션
                if self._is_quota_error(e):
                    logger.info("할당량 관련 에러로 판단되어 키를 전환합니다.")
                    if not self._rotate_key():
                        break
                else:
                    # 일반 에러는 재시도
                    time.sleep(retry_delay)
            
            attempts += 1
        
        # 모든 시도 실패
        error_msg = f"모든 API 키로 시도했으나 실패했습니다. 마지막 에러: {last_error}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    async def agenerate_content(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """
        Gemini API로 컨텐츠 생성 (비동기, 자동 키 로테이션 포함)
        
        Args:
            prompt: 입력 프롬프트
            **kwargs: GenerativeModel.generate_content에 전달할 추가 인자
            
        Returns:
            생성된 텍스트
            
        Raises:
            Exception: 모든 API 키로 시도했으나 실패한 경우
        """
        max_retries = self.settings.get('max_retries', 3)
        retry_delay = self.settings.get('retry_delay', 2)
        
        last_error = None
        attempts = 0
        max_attempts = len(self.api_keys) * max_retries
        
        while attempts < max_attempts:
            current_key = self.api_keys[self.current_key_index]
            
            try:
                # kwargs에서 temperature 추출 (있으면 사용, 없으면 설정값 사용)
                temperature = kwargs.pop('temperature', self.settings.get('temperature', 0.7))
                
                # generation_config 구성
                generation_config = {
                    'temperature': temperature,
                }
                generation_config.update(kwargs.pop('generation_config', {}))
                
                # 비동기 API 호출 (동기 메서드를 asyncio로 래핑)
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.current_model.generate_content(
                        prompt, 
                        generation_config=generation_config
                    )
                )
                
                # 성공 시 실패 카운트 리셋
                current_key.failed_count = 0
                current_key.last_error = None
                
                return response.text
                
            except google_exceptions.ResourceExhausted as e:
                # 할당량 초과 - 즉시 키 로테이션
                logger.warning(f"API 키 '{current_key.name}' 할당량 초과. 다음 키로 전환합니다.")
                current_key.failed_count += 1
                current_key.last_error = str(e)
                last_error = e
                
                if not self._rotate_key():
                    break
                    
            except Exception as e:
                # 기타 에러
                logger.warning(f"API 호출 실패 (키: {current_key.name}): {e}")
                current_key.failed_count += 1
                current_key.last_error = str(e)
                last_error = e
                
                # 할당량 관련 에러인 경우 키 로테이션
                if self._is_quota_error(e):
                    logger.info("할당량 관련 에러로 판단되어 키를 전환합니다.")
                    if not self._rotate_key():
                        break
                else:
                    # 일반 에러는 재시도
                    await asyncio.sleep(retry_delay)
            
            attempts += 1
        
        # 모든 시도 실패
        error_msg = f"모든 API 키로 시도했으나 실패했습니다. 마지막 에러: {last_error}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    def get_current_key_info(self) -> Dict[str, Any]:
        """현재 사용 중인 API 키 정보 반환"""
        current_key = self.api_keys[self.current_key_index]
        return {
            'name': current_key.name,
            'index': self.current_key_index,
            'total_keys': len(self.api_keys),
            'failed_count': current_key.failed_count,
            'last_error': current_key.last_error,
        }
    
    def get_all_keys_status(self) -> List[Dict[str, Any]]:
        """모든 API 키의 상태 반환"""
        return [
            {
                'name': key.name,
                'enabled': key.enabled,
                'failed_count': key.failed_count,
                'last_error': key.last_error,
            }
            for key in self.api_keys
        ]


# 싱글톤 인스턴스 생성을 위한 헬퍼 함수
_global_pool: Optional[GeminiAPIPool] = None


def get_gemini_pool(config_path: Optional[str] = None) -> GeminiAPIPool:
    """
    전역 GeminiAPIPool 인스턴스를 가져옵니다 (싱글톤 패턴)
    
    Args:
        config_path: API 키 설정 파일 경로
        
    Returns:
        GeminiAPIPool 인스턴스
    """
    global _global_pool
    if _global_pool is None:
        _global_pool = GeminiAPIPool(config_path)
    return _global_pool


def reset_gemini_pool():
    """전역 GeminiAPIPool 인스턴스 리셋 (주로 테스트용)"""
    global _global_pool
    _global_pool = None
