"""
QA Generator for Insurance Table Data
보험 테이블 기반 QA 데이터셋 생성기

이 모듈은 Gemini API를 활용하여 보험 테이블 마크다운 데이터로부터
다양한 난이도와 유형의 QA 데이터셋을 생성합니다.

주요 기능:
1. 난이도별 QA 생성 (IR, Analysis, Compare, Aggregation, Reasoning, Insight)
2. Multi-table QA 생성
3. 꼬리 질문 (Follow-up) 생성
4. Evol-Instruct 기반 난이도 진화
5. LLM-as-Judge 품질 평가
"""

import json
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, asdict
from enum import Enum
import sys

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from polling_gemini import get_gemini_pool, GeminiAPIPool

from .prompts import (
    QA_GENERATOR_SYSTEM_PROMPT,
    IR_QA_PROMPT,
    ANALYSIS_QA_PROMPT,
    COMPARE_QA_PROMPT,
    AGGREGATION_QA_PROMPT,
    REASONING_QA_PROMPT,
    INSIGHT_QA_PROMPT,
    FOLLOWUP_QA_PROMPT,
    MULTI_TABLE_QA_PROMPT,
    EVOL_INSTRUCT_PROMPT,
    QA_EVALUATION_PROMPT,
    get_qa_prompt_by_difficulty,
    format_tables_for_prompt,
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QADifficulty(Enum):
    """QA 난이도 레벨"""
    IR = "IR"                    # Level 1: 단순 정보 검색
    ANALYSIS = "Analysis"        # Level 2: 분석적 질문
    COMPARE = "Compare"          # Level 3: 비교/Multi-hop
    AGGREGATION = "Aggregation"  # Level 4: 집계 연산
    REASONING = "Reasoning"      # Level 5: 복합 추론
    INSIGHT = "Insight"          # Level 6: 통찰 도출


class QAType(Enum):
    """QA 답변 유형"""
    EXACT_MATCH = "exact_match"      # 단답형 (정확히 일치)
    DESCRIPTIVE = "descriptive"       # 서술형 (LLM Judge 평가)
    CALCULATION = "calculation"       # 계산형 (수치 결과)
    COMPARISON = "comparison"         # 비교형 (비교 결과 및 근거)


@dataclass
class QAPair:
    """QA 쌍 데이터 클래스"""
    id: str
    difficulty: str
    answer_type: str
    question: str
    answer: str
    reasoning: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    python_verification: Optional[str] = None
    chain_of_thought: Optional[List[str]] = None
    # 추가 필드들 (LLM이 생성할 수 있는 다양한 필드)
    calculation: Optional[str] = None
    calculation_steps: Optional[List[str]] = None
    assumptions: Optional[List[str]] = None
    supporting_analysis: Optional[str] = None
    key_findings: Optional[List[str]] = None
    required_tables: Optional[List[str]] = None
    join_logic: Optional[str] = None
    python_code: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None  # 기타 알 수 없는 필드용
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QAPair':
        """딕셔너리에서 QAPair 생성 (알 수 없는 필드는 extra에 저장)"""
        # QAPair의 필드 목록
        known_fields = {
            'id', 'difficulty', 'answer_type', 'question', 'answer',
            'reasoning', 'evidence', 'tags', 'python_verification',
            'chain_of_thought', 'calculation', 'calculation_steps',
            'assumptions', 'supporting_analysis', 'key_findings',
            'required_tables', 'join_logic', 'python_code', 'extra'
        }
        
        # 알려진 필드와 알 수 없는 필드 분리
        known_data = {}
        extra_data = {}
        
        for key, value in data.items():
            if key in known_fields:
                known_data[key] = value
            else:
                extra_data[key] = value
        
        # 필수 필드 기본값 설정
        known_data.setdefault('id', 'UNKNOWN')
        known_data.setdefault('difficulty', 'Unknown')
        known_data.setdefault('answer_type', 'unknown')
        known_data.setdefault('question', '')
        known_data.setdefault('answer', '')
        
        # extra 필드가 있으면 추가
        if extra_data:
            known_data['extra'] = extra_data
        
        return cls(**known_data)


@dataclass 
class EvaluationResult:
    """QA 평가 결과 데이터 클래스"""
    correctness: Dict[str, Any]
    faithfulness: Dict[str, Any]
    relevance: Dict[str, Any]
    difficulty_appropriateness: Dict[str, Any]
    clarity: Dict[str, Any]
    overall_score: float
    passed: bool
    improvement_suggestions: List[str]


class InsuranceTableQAGenerator:
    """
    보험 테이블 기반 QA 데이터셋 생성기
    
    Gemini API Pool을 활용하여 자동 키 로테이션을 지원하며,
    다양한 난이도와 유형의 QA를 생성합니다.
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        model_name: str = "gemini-2.0-flash",
    ):
        """
        Args:
            config_path: API 키 설정 파일 경로
            model_name: 사용할 Gemini 모델
        """
        self.pool = get_gemini_pool(config_path)
        self.model_name = model_name
        self.system_prompt = QA_GENERATOR_SYSTEM_PROMPT
        
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """LLM 응답에서 JSON 추출 및 파싱"""
        try:
            # JSON 블록 추출 시도
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()
            
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
            logger.debug(f"원본 응답: {response}")
            return {"error": str(e), "raw_response": response}
    
    def _build_prompt(
        self,
        base_prompt: str,
        tables: Dict[str, str],
        **kwargs
    ) -> str:
        """프롬프트 구성"""
        formatted_tables = format_tables_for_prompt(tables)
        
        prompt = f"{self.system_prompt}\n\n{base_prompt}"
        prompt = prompt.format(tables=formatted_tables, **kwargs)
        
        return prompt
    
    def generate_qa_by_difficulty(
        self,
        tables: Dict[str, str],
        difficulty: QADifficulty,
        num_questions: int = 3,
        **kwargs
    ) -> List[QAPair]:
        """
        특정 난이도의 QA 생성
        
        Args:
            tables: 테이블 딕셔너리 {table_id: markdown_content}
            difficulty: QA 난이도
            num_questions: 생성할 질문 수
            
        Returns:
            생성된 QA 쌍 리스트
        """
        base_prompt = get_qa_prompt_by_difficulty(difficulty.value)
        prompt = self._build_prompt(
            base_prompt, 
            tables, 
            num_questions=num_questions
        )
        
        try:
            response = self.pool.generate_content(prompt)
            result = self._parse_json_response(response)
            
            if "questions" in result:
                return [QAPair.from_dict(q) for q in result["questions"]]
            else:
                logger.warning(f"예상치 못한 응답 형식: {result}")
                return []
                
        except Exception as e:
            logger.error(f"QA 생성 실패: {e}")
            return []
    
    async def agenerate_qa_by_difficulty(
        self,
        tables: Dict[str, str],
        difficulty: QADifficulty,
        num_questions: int = 3,
        **kwargs
    ) -> List[QAPair]:
        """난이도별 QA 생성 (비동기)"""
        base_prompt = get_qa_prompt_by_difficulty(difficulty.value)
        prompt = self._build_prompt(
            base_prompt,
            tables,
            num_questions=num_questions
        )
        
        try:
            response = await self.pool.agenerate_content(prompt)
            result = self._parse_json_response(response)
            
            if "questions" in result:
                return [QAPair.from_dict(q) for q in result["questions"]]
            else:
                return []
                
        except Exception as e:
            logger.error(f"비동기 QA 생성 실패: {e}")
            return []
    
    def generate_multi_table_qa(
        self,
        tables: Dict[str, str],
        num_questions: int = 3,
    ) -> List[QAPair]:
        """
        Multi-table QA 생성
        
        복수의 테이블을 참조해야 답변 가능한 질문 생성
        """
        if len(tables) < 2:
            logger.warning("Multi-table QA는 최소 2개의 테이블이 필요합니다.")
            # 단일 테이블이라도 시도
            
        prompt = self._build_prompt(
            MULTI_TABLE_QA_PROMPT,
            tables,
            num_questions=num_questions
        )
        
        try:
            response = self.pool.generate_content(prompt)
            result = self._parse_json_response(response)
            
            if "questions" in result:
                return [QAPair.from_dict(q) for q in result["questions"]]
            return []
            
        except Exception as e:
            logger.error(f"Multi-table QA 생성 실패: {e}")
            return []
    
    def generate_followup_qa(
        self,
        tables: Dict[str, str],
        original_qa: QAPair,
    ) -> Dict[str, Any]:
        """
        꼬리 질문 (Follow-up) 생성
        
        원래 QA를 기반으로 연속적인 후속 질문 체인 생성
        """
        original_qa_str = json.dumps(original_qa.to_dict(), ensure_ascii=False, indent=2)
        
        prompt = self._build_prompt(
            FOLLOWUP_QA_PROMPT,
            tables,
            original_qa=original_qa_str
        )
        
        try:
            response = self.pool.generate_content(prompt)
            return self._parse_json_response(response)
            
        except Exception as e:
            logger.error(f"Follow-up QA 생성 실패: {e}")
            return {}
    
    def evolve_question(
        self,
        tables: Dict[str, str],
        original_question: str,
    ) -> Dict[str, Any]:
        """
        Evol-Instruct: 질문 난이도 진화
        
        기본 질문을 더 복잡한 질문으로 진화
        """
        prompt = self._build_prompt(
            EVOL_INSTRUCT_PROMPT,
            tables,
            original_question=original_question
        )
        
        try:
            response = self.pool.generate_content(prompt)
            return self._parse_json_response(response)
            
        except Exception as e:
            logger.error(f"Evol-Instruct 실패: {e}")
            return {}
    
    def evaluate_qa(
        self,
        tables: Dict[str, str],
        qa_pair: QAPair,
    ) -> EvaluationResult:
        """
        LLM-as-Judge: QA 품질 평가
        
        생성된 QA 쌍의 품질을 다면적으로 평가
        """
        qa_str = json.dumps(qa_pair.to_dict(), ensure_ascii=False, indent=2)
        
        prompt = self._build_prompt(
            QA_EVALUATION_PROMPT,
            tables,
            qa_pair=qa_str
        )
        
        try:
            response = self.pool.generate_content(prompt)
            result = self._parse_json_response(response)
            
            if "evaluation" in result:
                eval_data = result["evaluation"]
                return EvaluationResult(
                    correctness=eval_data.get("correctness", {}),
                    faithfulness=eval_data.get("faithfulness", {}),
                    relevance=eval_data.get("relevance", {}),
                    difficulty_appropriateness=eval_data.get("difficulty_appropriateness", {}),
                    clarity=eval_data.get("clarity", {}),
                    overall_score=result.get("overall_score", 0.0),
                    passed=result.get("pass", False),
                    improvement_suggestions=result.get("improvement_suggestions", [])
                )
            else:
                logger.warning(f"평가 결과 파싱 실패: {result}")
                return None
                
        except Exception as e:
            logger.error(f"QA 평가 실패: {e}")
            return None
    
    def generate_comprehensive_qa_dataset(
        self,
        tables: Dict[str, str],
        questions_per_difficulty: int = 2,
        include_followup: bool = True,
        include_evolution: bool = True,
        evaluate_quality: bool = False,
    ) -> Dict[str, Any]:
        """
        종합적인 QA 데이터셋 생성
        
        모든 난이도의 QA를 생성하고 선택적으로 꼬리질문, 진화, 평가를 수행
        
        Args:
            tables: 테이블 딕셔너리
            questions_per_difficulty: 난이도별 질문 수
            include_followup: 꼬리질문 포함 여부
            include_evolution: Evol-Instruct 포함 여부
            evaluate_quality: 품질 평가 수행 여부
            
        Returns:
            종합 QA 데이터셋
        """
        dataset = {
            "metadata": {
                "tables_count": len(tables),
                "questions_per_difficulty": questions_per_difficulty,
            },
            "qa_pairs": [],
            "followup_chains": [],
            "evolved_questions": [],
            "evaluations": [],
        }
        
        # 1. 각 난이도별 QA 생성
        for difficulty in QADifficulty:
            logger.info(f"Generating {difficulty.value} level QA...")
            qa_pairs = self.generate_qa_by_difficulty(
                tables, difficulty, questions_per_difficulty
            )
            
            for qa in qa_pairs:
                qa_dict = qa.to_dict()
                dataset["qa_pairs"].append(qa_dict)
                
                # 2. 꼬리질문 생성 (선택적)
                if include_followup and difficulty in [QADifficulty.IR, QADifficulty.ANALYSIS]:
                    followup = self.generate_followup_qa(tables, qa)
                    if followup:
                        dataset["followup_chains"].append(followup)
                
                # 3. 질문 진화 (선택적)
                if include_evolution and difficulty in [QADifficulty.IR, QADifficulty.ANALYSIS]:
                    evolved = self.evolve_question(tables, qa.question)
                    if evolved:
                        dataset["evolved_questions"].append(evolved)
                
                # 4. 품질 평가 (선택적)
                if evaluate_quality:
                    evaluation = self.evaluate_qa(tables, qa)
                    if evaluation:
                        dataset["evaluations"].append({
                            "qa_id": qa.id,
                            "evaluation": asdict(evaluation)
                        })
        
        # 5. Multi-table QA (테이블이 2개 이상인 경우)
        if len(tables) >= 2:
            logger.info("Generating Multi-table QA...")
            multi_qa = self.generate_multi_table_qa(tables, questions_per_difficulty)
            for qa in multi_qa:
                dataset["qa_pairs"].append(qa.to_dict())
        
        # 메타데이터 업데이트
        dataset["metadata"]["total_qa_pairs"] = len(dataset["qa_pairs"])
        dataset["metadata"]["total_followups"] = len(dataset["followup_chains"])
        dataset["metadata"]["total_evolved"] = len(dataset["evolved_questions"])
        
        return dataset
    
    async def agenerate_comprehensive_qa_dataset(
        self,
        tables: Dict[str, str],
        questions_per_difficulty: int = 2,
    ) -> Dict[str, Any]:
        """종합 QA 데이터셋 생성 (비동기)"""
        dataset = {
            "metadata": {
                "tables_count": len(tables),
                "questions_per_difficulty": questions_per_difficulty,
            },
            "qa_pairs": [],
        }
        
        # 모든 난이도에 대해 병렬로 QA 생성
        tasks = [
            self.agenerate_qa_by_difficulty(tables, difficulty, questions_per_difficulty)
            for difficulty in QADifficulty
        ]
        
        results = await asyncio.gather(*tasks)
        
        for qa_list in results:
            for qa in qa_list:
                dataset["qa_pairs"].append(qa.to_dict())
        
        dataset["metadata"]["total_qa_pairs"] = len(dataset["qa_pairs"])
        
        return dataset


# =============================================================================
# Convenience Functions
# =============================================================================

def generate_qa_from_tables(
    tables: Dict[str, str],
    difficulty: Optional[QADifficulty] = None,
    num_questions: int = 3,
    config_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    테이블에서 QA 생성 (간편 함수)
    
    Args:
        tables: 테이블 딕셔너리 {table_id: markdown_content}
        difficulty: 난이도 (None이면 모든 난이도)
        num_questions: 난이도별 질문 수
        config_path: API 설정 파일 경로
        
    Returns:
        생성된 QA 리스트
    """
    generator = InsuranceTableQAGenerator(config_path=config_path)
    
    if difficulty:
        qa_pairs = generator.generate_qa_by_difficulty(tables, difficulty, num_questions)
        return [qa.to_dict() for qa in qa_pairs]
    else:
        dataset = generator.generate_comprehensive_qa_dataset(
            tables,
            questions_per_difficulty=num_questions,
            include_followup=False,
            include_evolution=False,
            evaluate_quality=False,
        )
        return dataset["qa_pairs"]


async def agenerate_qa_from_tables(
    tables: Dict[str, str],
    num_questions: int = 3,
    config_path: Optional[str] = None,
) -> Dict[str, Any]:
    """테이블에서 QA 생성 (비동기 간편 함수)"""
    generator = InsuranceTableQAGenerator(config_path=config_path)
    return await generator.agenerate_comprehensive_qa_dataset(tables, num_questions)
