"""
Table Extraction Example
보험 도메인 특화 테이블 추출 예제
polling_gemini 패키지를 사용하여 이미지에서 Markdown 테이블 추출
"""

from .table_extractor import (
    InsuranceTableExtractor,
    extract_table_from_image,
    aextract_table_from_image,
)
from .prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

__all__ = [
    'InsuranceTableExtractor',
    'extract_table_from_image',
    'aextract_table_from_image',
    'SYSTEM_PROMPT',
    'USER_PROMPT_TEMPLATE',
]
