"""
보험 테이블 추출기
polling_gemini 패키지를 사용하여 이미지에서 테이블을 Markdown으로 변환
"""

import os
import asyncio
import base64
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from .prompts import SYSTEM_PROMPT, get_user_prompt

# polling_gemini 패키지에서 API Pool 가져오기
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from polling_gemini import get_gemini_pool, GeminiAPIPool

# 로깅 설정
logger = logging.getLogger(__name__)


def load_image_as_base64(image_path: Union[str, Path]) -> str:
    """이미지 파일을 Base64로 인코딩"""
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {image_path}")
    
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_image_mime_type(image_path: Union[str, Path]) -> str:
    """이미지 파일의 MIME 타입 반환"""
    image_path = Path(image_path)
    suffix = image_path.suffix.lower()
    
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    
    return mime_types.get(suffix, "image/jpeg")


class InsuranceTableExtractor:
    """
    보험 문서 이미지에서 테이블을 추출하는 클래스
    
    polling_gemini의 GeminiAPIPool을 활용하여 자동 API 키 로테이션을 지원합니다.
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        model_name: str = "gemini-2.5-flash",
    ):
        """
        Args:
            config_path: API 키 설정 파일 경로 (None이면 기본 경로 사용)
            model_name: 사용할 Gemini 모델 이름
        """
        self.pool = get_gemini_pool(config_path)
        self.model_name = model_name
        self.system_prompt = SYSTEM_PROMPT
        
    def _create_multimodal_content(
        self,
        image_path: Union[str, Path],
        ocr_markdown: str = "N/A"
    ) -> list:
        """
        멀티모달 콘텐츠 생성 (이미지 + 텍스트)
        
        Args:
            image_path: 이미지 파일 경로
            ocr_markdown: 참조용 OCR 마크다운 텍스트
            
        Returns:
            Gemini API에 전달할 콘텐츠 리스트
        """
        # 이미지 로드
        image_data = load_image_as_base64(image_path)
        mime_type = get_image_mime_type(image_path)
        
        # 사용자 프롬프트 생성
        user_prompt = get_user_prompt(ocr_markdown)
        
        # 멀티모달 콘텐츠 구성
        content = [
            # 시스템 프롬프트를 포함한 전체 프롬프트
            f"{self.system_prompt}\n\n{user_prompt}",
            # 이미지 데이터
            {
                "mime_type": mime_type,
                "data": image_data
            }
        ]
        
        return content
    
    def extract(
        self,
        image_path: Union[str, Path],
        ocr_markdown: str = "N/A",
        **kwargs
    ) -> str:
        """
        이미지에서 테이블을 추출하여 Markdown으로 반환 (동기)
        
        Args:
            image_path: 테이블이 포함된 이미지 파일 경로
            ocr_markdown: 참조용 OCR 마크다운 텍스트 (선택적)
            **kwargs: 추가 생성 파라미터
            
        Returns:
            추출된 Markdown 테이블 문자열
        """
        content = self._create_multimodal_content(image_path, ocr_markdown)
        
        # API Pool의 현재 설정된 모델 사용
        # 멀티모달 요청을 위해 직접 genai 호출
        max_retries = self.pool.settings.get('max_retries', 3)
        retry_delay = self.pool.settings.get('retry_delay', 2)
        
        last_error = None
        attempts = 0
        max_attempts = len(self.pool.api_keys) * max_retries
        
        while attempts < max_attempts:
            current_key = self.pool.api_keys[self.pool.current_key_index]
            
            try:
                # 현재 키로 Gemini 설정
                genai.configure(api_key=current_key.key)
                model = genai.GenerativeModel(self.model_name)
                
                # 생성 설정
                generation_config = {
                    'temperature': self.pool.settings.get('temperature', 0.1),
                }
                generation_config.update(kwargs.get('generation_config', {}))
                
                # API 호출
                response = model.generate_content(
                    content,
                    generation_config=generation_config
                )
                
                # 성공 시 실패 카운트 리셋
                current_key.failed_count = 0
                current_key.last_error = None
                
                return response.text
                
            except google_exceptions.ResourceExhausted as e:
                logger.warning(f"API 키 '{current_key.name}' 할당량 초과. 다음 키로 전환합니다.")
                current_key.failed_count += 1
                current_key.last_error = str(e)
                last_error = e
                
                if not self.pool._rotate_key():
                    break
                    
            except Exception as e:
                logger.warning(f"API 호출 실패 (키: {current_key.name}): {e}")
                current_key.failed_count += 1
                current_key.last_error = str(e)
                last_error = e
                
                if self.pool._is_quota_error(e):
                    if not self.pool._rotate_key():
                        break
                else:
                    import time
                    time.sleep(retry_delay)
            
            attempts += 1
        
        error_msg = f"모든 API 키로 시도했으나 실패했습니다. 마지막 에러: {last_error}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    async def aextract(
        self,
        image_path: Union[str, Path],
        ocr_markdown: str = "N/A",
        **kwargs
    ) -> str:
        """
        이미지에서 테이블을 추출하여 Markdown으로 반환 (비동기)
        
        Args:
            image_path: 테이블이 포함된 이미지 파일 경로
            ocr_markdown: 참조용 OCR 마크다운 텍스트 (선택적)
            **kwargs: 추가 생성 파라미터
            
        Returns:
            추출된 Markdown 테이블 문자열
        """
        # 동기 메서드를 비동기로 래핑
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.extract(image_path, ocr_markdown, **kwargs)
        )
    
    def get_pool_status(self) -> Dict[str, Any]:
        """현재 API Pool 상태 반환"""
        return {
            'current_key': self.pool.get_current_key_info(),
            'all_keys': self.pool.get_all_keys_status()
        }


# 편의 함수들

def extract_table_from_image(
    image_path: Union[str, Path],
    ocr_markdown: str = "N/A",
    config_path: Optional[str] = None,
    **kwargs
) -> str:
    """
    이미지에서 보험 테이블을 추출하는 간편 함수 (동기)
    
    Args:
        image_path: 테이블이 포함된 이미지 파일 경로
        ocr_markdown: 참조용 OCR 마크다운 텍스트 (선택적)
        config_path: API 키 설정 파일 경로
        **kwargs: 추가 생성 파라미터
        
    Returns:
        추출된 Markdown 테이블 문자열
        
    Example:
        ```python
        from Table_example import extract_table_from_image
        
        # 기본 사용
        result = extract_table_from_image("insurance_table.png")
        print(result)
        
        # OCR 참조 텍스트와 함께 사용
        result = extract_table_from_image(
            "insurance_table.png",
            ocr_markdown="| 구분 | 금액 |\\n| 보험료 | 10000 |"
        )
        ```
    """
    extractor = InsuranceTableExtractor(config_path=config_path)
    return extractor.extract(image_path, ocr_markdown, **kwargs)


async def aextract_table_from_image(
    image_path: Union[str, Path],
    ocr_markdown: str = "N/A",
    config_path: Optional[str] = None,
    **kwargs
) -> str:
    """
    이미지에서 보험 테이블을 추출하는 간편 함수 (비동기)
    
    Args:
        image_path: 테이블이 포함된 이미지 파일 경로
        ocr_markdown: 참조용 OCR 마크다운 텍스트 (선택적)
        config_path: API 키 설정 파일 경로
        **kwargs: 추가 생성 파라미터
        
    Returns:
        추출된 Markdown 테이블 문자열
        
    Example:
        ```python
        import asyncio
        from Table_example import aextract_table_from_image
        
        async def main():
            result = await aextract_table_from_image("insurance_table.png")
            print(result)
        
        asyncio.run(main())
        ```
    """
    extractor = InsuranceTableExtractor(config_path=config_path)
    return await extractor.aextract(image_path, ocr_markdown, **kwargs)
