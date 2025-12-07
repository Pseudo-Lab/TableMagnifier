"""
QA Generation Prompts for Insurance Table Data
보험 테이블 기반 QA 생성을 위한 프롬프트 템플릿

난이도별 QA 유형:
1. IR (Information Retrieval): 단순 정보 검색
2. Analysis: 분석적 질문
3. Compare (Multi-hop): 비교 및 다중 추론
4. Aggregation: 집계 연산
5. Reasoning: 복합 추론
6. Insight: 통찰 도출

답변 유형:
- Exact Match: 단답형 (숫자, 예/아니오)
- Descriptive: 서술형 (LLM Judge 평가)
"""

# =============================================================================
# System Prompts
# =============================================================================

QA_GENERATOR_SYSTEM_PROMPT = """# Role Definition
당신은 보험 도메인 전문가이자 고품질 QA 데이터셋 구축 전문가입니다.
주어진 보험 테이블 데이터를 기반으로 다양한 난이도와 유형의 질문-답변 쌍을 생성해야 합니다.

# Core Principles
1. **정확성(Accuracy):** 모든 답변은 주어진 테이블 데이터에 근거해야 합니다. 테이블에 없는 정보를 추측하지 마십시오.
2. **다양성(Diversity):** 단순 검색부터 복잡한 추론까지 다양한 난이도의 질문을 생성해야 합니다.
3. **실용성(Practicality):** 실제 보험 고객이 물어볼 수 있는 현실적인 질문을 생성해야 합니다.
4. **명확성(Clarity):** 질문과 답변 모두 명확하고 모호하지 않아야 합니다.

# Difficulty Levels (난이도)
- **IR (Level 1):** 특정 셀의 값을 직접 찾는 단순 검색
- **Analysis (Level 2):** 단일 테이블 내에서의 분석적 질문
- **Compare (Level 3):** 여러 행/열 또는 복수 테이블 간 비교
- **Aggregation (Level 4):** 합계, 평균, 최대/최소 등의 집계 연산
- **Reasoning (Level 5):** 여러 정보를 종합한 복합 추론
- **Insight (Level 6):** 데이터로부터 통찰이나 시사점 도출

# Answer Types (답변 유형)
- **exact_match:** 숫자, 예/아니오, 특정 텍스트 등 정확히 일치해야 하는 답변
- **descriptive:** 설명이 필요한 서술형 답변 (LLM-as-Judge로 평가)
- **calculation:** 수치 계산 결과 (계산 과정 포함)
- **comparison:** 비교 결과 및 근거"""

# =============================================================================
# QA Generation Prompts by Difficulty
# =============================================================================

IR_QA_PROMPT = """## Task: Information Retrieval (IR) Level QA 생성
단일 테이블에서 특정 셀의 값을 직접 검색하는 간단한 QA를 생성하세요.

### Input Tables
{tables}

### Requirements
1. 특정 행과 열이 교차하는 지점의 값을 묻는 질문
2. 단답형으로 대답 가능한 질문
3. 테이블에서 바로 찾을 수 있는 정보만 질문

### Output Format (JSON)
```json
{{
    "questions": [
        {{
            "id": "IR_001",
            "difficulty": "IR",
            "answer_type": "exact_match",
            "question": "질문 내용",
            "answer": "정확한 답변",
            "evidence": {{
                "table_id": "table_1",
                "row": "행 정보",
                "column": "열 정보"
            }},
            "tags": ["single_cell", "numeric"]
        }}
    ]
}}
```

### Generate {num_questions} IR-level QA pairs."""

ANALYSIS_QA_PROMPT = """## Task: Analysis Level QA 생성
단일 테이블 내에서 데이터를 분석하는 질문을 생성하세요.

### Input Tables
{tables}

### Requirements
1. 특정 조건을 만족하는 행/열 찾기
2. 최대값/최소값을 가진 항목 식별
3. 특정 범위 내의 데이터 확인
4. 단답형 또는 짧은 설명형 답변

### Output Format (JSON)
```json
{{
    "questions": [
        {{
            "id": "ANALYSIS_001",
            "difficulty": "Analysis",
            "answer_type": "exact_match",
            "question": "질문 내용",
            "answer": "정확한 답변",
            "reasoning": "답을 도출하는 과정 설명",
            "evidence": {{
                "table_id": "table_1",
                "relevant_cells": ["셀 위치1", "셀 위치2"]
            }},
            "tags": ["conditional_search", "extrema"]
        }}
    ]
}}
```

### Generate {num_questions} Analysis-level QA pairs."""

COMPARE_QA_PROMPT = """## Task: Compare (Multi-hop) Level QA 생성
여러 행, 열, 또는 복수 테이블 간 비교가 필요한 질문을 생성하세요.

### Input Tables
{tables}

### Requirements
1. 두 개 이상의 셀 값을 비교하는 질문
2. 시계열 변화를 비교하는 질문
3. 복수 테이블의 정보를 연결하는 질문
4. 차이, 비율, 증감률 등을 묻는 질문

### Output Format (JSON)
```json
{{
    "questions": [
        {{
            "id": "COMPARE_001",
            "difficulty": "Compare",
            "answer_type": "calculation",
            "question": "질문 내용",
            "answer": "정확한 답변",
            "calculation": "계산 과정",
            "reasoning": "비교 논리 설명",
            "evidence": {{
                "table_ids": ["table_1", "table_2"],
                "compared_cells": [
                    {{"table": "table_1", "row": "행1", "column": "열1", "value": "값1"}},
                    {{"table": "table_1", "row": "행2", "column": "열2", "value": "값2"}}
                ]
            }},
            "tags": ["multi_hop", "comparison", "calculation"]
        }}
    ]
}}
```

### Generate {num_questions} Compare-level QA pairs."""

AGGREGATION_QA_PROMPT = """## Task: Aggregation Level QA 생성
합계, 평균, 누적값 등 집계 연산이 필요한 질문을 생성하세요.

### Input Tables
{tables}

### Requirements
1. 특정 열/행의 합계를 구하는 질문
2. 평균값을 계산하는 질문
3. 누적 증가율을 구하는 질문
4. 조건부 집계 (특정 조건을 만족하는 항목들의 합계 등)

### Python Code for Verification
답변의 정확성 검증을 위해 Python 코드도 함께 생성하세요.

### Output Format (JSON)
```json
{{
    "questions": [
        {{
            "id": "AGG_001",
            "difficulty": "Aggregation",
            "answer_type": "calculation",
            "question": "질문 내용",
            "answer": "정확한 수치 답변",
            "calculation": "단계별 계산 과정",
            "python_verification": "import pandas as pd\\n# 검증 코드",
            "evidence": {{
                "table_id": "table_1",
                "aggregated_cells": ["셀1", "셀2", "셀3"]
            }},
            "tags": ["aggregation", "sum", "average"]
        }}
    ]
}}
```

### Generate {num_questions} Aggregation-level QA pairs."""

REASONING_QA_PROMPT = """## Task: Reasoning Level QA 생성
여러 정보를 종합하여 복합적인 추론이 필요한 질문을 생성하세요.

### Input Tables
{tables}

### Requirements
1. 조건부 로직을 적용한 추론 질문
2. 가정(Assumption)을 포함한 시나리오 기반 질문
3. 인과관계를 파악하는 질문
4. 여러 단계의 논리적 추론이 필요한 질문

### Chain-of-Thought Reasoning
답변 도출 과정을 단계별로 명시하세요.

### Output Format (JSON)
```json
{{
    "questions": [
        {{
            "id": "REASON_001",
            "difficulty": "Reasoning",
            "answer_type": "descriptive",
            "question": "질문 내용",
            "answer": "답변",
            "chain_of_thought": [
                "Step 1: ...",
                "Step 2: ...",
                "Step 3: ..."
            ],
            "assumptions": ["가정1", "가정2"],
            "evidence": {{
                "table_ids": ["table_1"],
                "relevant_data": ["관련 데이터 포인트"]
            }},
            "tags": ["multi_step_reasoning", "conditional_logic"]
        }}
    ]
}}
```

### Generate {num_questions} Reasoning-level QA pairs."""

INSIGHT_QA_PROMPT = """## Task: Insight Level QA 생성
데이터로부터 통찰이나 시사점을 도출하는 고난도 질문을 생성하세요.

### Input Tables
{tables}

### Requirements
1. 데이터 추세(Trend)를 파악하는 질문
2. 이상치(Anomaly)나 특이 패턴을 발견하는 질문
3. 데이터 기반 예측이나 권고를 요청하는 질문
4. 비즈니스적 함의를 도출하는 질문

### Output Format (JSON)
```json
{{
    "questions": [
        {{
            "id": "INSIGHT_001",
            "difficulty": "Insight",
            "answer_type": "descriptive",
            "question": "질문 내용",
            "answer": "통찰 및 답변",
            "supporting_analysis": "분석 과정",
            "key_findings": ["발견1", "발견2"],
            "evidence": {{
                "table_ids": ["table_1", "table_2"],
                "data_points": ["근거 데이터"]
            }},
            "tags": ["trend_analysis", "insight", "recommendation"]
        }}
    ]
}}
```

### Generate {num_questions} Insight-level QA pairs."""

# =============================================================================
# Follow-up Question Prompts (꼬리 질문)
# =============================================================================

FOLLOWUP_QA_PROMPT = """## Task: Follow-up Question (꼬리 질문) 생성
주어진 초기 QA에 대해 연속적인 후속 질문을 생성하세요.

### Original QA
{original_qa}

### Input Tables
{tables}

### Requirements
1. 원래 질문의 맥락을 유지하면서 심화된 질문
2. 원래 답변에서 파생되는 추가 질문
3. 관련된 다른 데이터 포인트를 탐색하는 질문
4. 2-3개의 연속적인 후속 질문 체인 생성

### Output Format (JSON)
```json
{{
    "original_qa": {{
        "question": "원래 질문",
        "answer": "원래 답변"
    }},
    "followup_chain": [
        {{
            "id": "FOLLOWUP_001_1",
            "question": "후속 질문 1",
            "answer": "답변 1",
            "reasoning": "이전 답변과의 연결고리"
        }},
        {{
            "id": "FOLLOWUP_001_2",
            "question": "후속 질문 2 (질문1 기반)",
            "answer": "답변 2",
            "reasoning": "이전 답변과의 연결고리"
        }}
    ]
}}
```

### Generate follow-up questions chain."""

# =============================================================================
# Multi-Table QA Prompts
# =============================================================================

MULTI_TABLE_QA_PROMPT = """## Task: Multi-Table QA 생성
복수의 테이블을 참조해야 답변 가능한 질문을 생성하세요.

### Input Tables
{tables}

### Requirements
1. 반드시 2개 이상의 테이블 정보를 조합해야 답변 가능한 질문
2. 테이블 간 연결 키(Key)를 활용한 질문
3. 서로 다른 테이블의 수치를 비교/연산하는 질문
4. 종합적인 분석이 필요한 질문

### Output Format (JSON)
```json
{{
    "questions": [
        {{
            "id": "MULTI_001",
            "difficulty": "Compare",
            "answer_type": "calculation",
            "question": "질문 내용",
            "answer": "답변",
            "required_tables": ["table_1", "table_2"],
            "join_logic": "테이블 연결 방법 설명",
            "reasoning": "답변 도출 과정",
            "tags": ["multi_table", "join", "cross_reference"]
        }}
    ]
}}
```

### Generate {num_questions} Multi-Table QA pairs."""

# =============================================================================
# Evol-Instruct Prompts (난이도 진화)
# =============================================================================

EVOL_INSTRUCT_PROMPT = """## Task: Evol-Instruct - 질문 난이도 진화
주어진 기본 질문을 더 복잡하고 도전적인 질문으로 진화시키세요.

### Original Question
{original_question}

### Evolution Strategies
다음 전략 중 하나 이상을 적용하여 질문을 진화시키세요:

1. **제약 조건 추가 (Adding Constraints):**
   - 특정 조건(나이, 기간, 금액 범위 등)을 추가
   
2. **심층 추론 (Deepening Reasoning):**
   - 다단계 논리적 사고를 요구하도록 변환
   
3. **구체화 (Concretizing):**
   - 추상적 질문을 구체적 시나리오로 대체
   
4. **입력 복잡도 증가 (Complicating Input):**
   - 복수 테이블이나 추가 조건을 참조하도록 변환

### Input Tables
{tables}

### Output Format (JSON)
```json
{{
    "original": {{
        "question": "원래 질문",
        "difficulty": "원래 난이도"
    }},
    "evolved": {{
        "question": "진화된 질문",
        "difficulty": "새로운 난이도",
        "evolution_strategy": "적용된 전략",
        "answer": "새로운 답변",
        "reasoning": "답변 도출 과정"
    }}
}}
```

### Evolve the question."""

# =============================================================================
# Quality Evaluation Prompts (LLM-as-Judge)
# =============================================================================

QA_EVALUATION_PROMPT = """## Task: QA 품질 평가 (LLM-as-Judge)
생성된 QA 쌍의 품질을 다면적으로 평가하세요.

### QA to Evaluate
{qa_pair}

### Reference Tables
{tables}

### Evaluation Criteria (1-5점 척도)

1. **정확성 (Correctness):** 
   - 답변이 테이블 데이터에 정확히 근거하는가?
   - 수치 계산이 정확한가?

2. **충실성 (Faithfulness):**
   - 테이블에 없는 정보를 날조(Hallucination)하지 않았는가?
   - 근거 데이터가 명확한가?

3. **관련성 (Relevance):**
   - 질문이 보험 도메인에서 실용적인가?
   - 실제 고객이 물어볼 법한 질문인가?

4. **난이도 적절성 (Difficulty Appropriateness):**
   - 표기된 난이도와 실제 난이도가 일치하는가?

5. **명확성 (Clarity):**
   - 질문과 답변이 명확하고 모호하지 않은가?

### Output Format (JSON)
```json
{{
    "evaluation": {{
        "correctness": {{"score": 5, "comment": "평가 코멘트"}},
        "faithfulness": {{"score": 5, "comment": "평가 코멘트"}},
        "relevance": {{"score": 5, "comment": "평가 코멘트"}},
        "difficulty_appropriateness": {{"score": 5, "comment": "평가 코멘트"}},
        "clarity": {{"score": 5, "comment": "평가 코멘트"}}
    }},
    "overall_score": 5.0,
    "pass": true,
    "improvement_suggestions": ["개선 제안1", "개선 제안2"]
}}
```

### Evaluate the QA pair."""


# =============================================================================
# Helper Functions
# =============================================================================

def get_qa_prompt_by_difficulty(difficulty: str) -> str:
    """난이도에 따른 프롬프트 반환"""
    prompts = {
        "IR": IR_QA_PROMPT,
        "Analysis": ANALYSIS_QA_PROMPT,
        "Compare": COMPARE_QA_PROMPT,
        "Aggregation": AGGREGATION_QA_PROMPT,
        "Reasoning": REASONING_QA_PROMPT,
        "Insight": INSIGHT_QA_PROMPT,
    }
    return prompts.get(difficulty, IR_QA_PROMPT)


def format_tables_for_prompt(tables: dict) -> str:
    """테이블 딕셔너리를 프롬프트용 문자열로 변환"""
    formatted = []
    for table_id, table_content in tables.items():
        formatted.append(f"### {table_id}\n```markdown\n{table_content}\n```\n")
    return "\n".join(formatted)
