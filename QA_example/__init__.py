"""
QA Dataset Generation Module for Insurance Tables
보험 테이블 기반 QA 데이터셋 생성 모듈
"""

from .qa_generator import (
    InsuranceTableQAGenerator,
    QADifficulty,
    QAType,
    generate_qa_from_tables,
)

__all__ = [
    'InsuranceTableQAGenerator',
    'QADifficulty',
    'QAType',
    'generate_qa_from_tables',
]

__version__ = '0.1.0'
