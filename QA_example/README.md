# QA Dataset Generation Module

보험 테이블 마크다운 데이터를 기반으로 고품질 QA(Question-Answer) 데이터셋을 생성하는 모듈입니다.

## 주요 기능

### 1. 난이도별 QA 생성
- **IR (Information Retrieval)**: 단순 정보 검색 (Level 1)
- **Analysis**: 분석적 질문 (Level 2)
- **Compare (Multi-hop)**: 비교 및 다중 추론 (Level 3)
- **Aggregation**: 집계 연산 (Level 4)
- **Reasoning**: 복합 추론 (Level 5)
- **Insight**: 통찰 도출 (Level 6)

### 2. 다양한 답변 유형
- **Exact Match**: 단답형 (숫자, 예/아니오) - 정확한 매칭 평가
- **Descriptive**: 서술형 - LLM-as-Judge 평가
- **Calculation**: 수치 계산 결과 - Python 코드로 검증

### 3. 고급 기능
- **Multi-Table QA**: 복수 테이블 참조 필요 질문
- **Follow-up QA**: 꼬리 질문 체인 생성
- **Evol-Instruct**: 질문 난이도 진화
- **LLM-as-Judge**: 품질 평가

## 사용법

### 기본 사용

```python
from QA_example import InsuranceTableQAGenerator, QADifficulty

# 테이블 데이터 준비
tables = {
    "table_1": "| 구분 | 값 |\n|---|---|\n| A | 100 |",
    "table_2": "| 항목 | 금액 |\n|---|---|\n| B | 200 |"
}

# Generator 초기화
generator = InsuranceTableQAGenerator()

# 특정 난이도 QA 생성
ir_qa = generator.generate_qa_by_difficulty(tables, QADifficulty.IR, num_questions=3)

# 종합 데이터셋 생성
dataset = generator.generate_comprehensive_qa_dataset(
    tables,
    questions_per_difficulty=2,
    include_followup=True,
    include_evolution=True
)
```

### 간편 함수 사용

```python
from QA_example import generate_qa_from_tables

# 모든 난이도 QA 생성
all_qa = generate_qa_from_tables(tables, num_questions=2)

# 특정 난이도만 생성
ir_only = generate_qa_from_tables(tables, difficulty=QADifficulty.IR)
```

## 커버되는 QA 양상

| # | 양상 | 설명 | 구현 방식 |
|---|------|------|----------|
| 1 | Multi-table QA | 복수 테이블 참조 | `generate_multi_table_qa()` |
| 2 | 난이도별 QA | 6단계 난이도 체계 | `QADifficulty` Enum |
| 3 | 다양한 답변 유형 | Exact Match, Descriptive | `QAType` Enum |
| 4 | 수치 계산 QA | 집계, 비율 계산 | Aggregation 난이도 |
| 5 | 꼬리 질문 | Q-A 체인 | `generate_followup_qa()` |
| 6 | 셀 기반 측정 | 여러 셀 기반 | Compare, Aggregation |
| 7 | 특정 셀 Q-A | 단일 셀 검색 | IR 난이도 |
| 8 | 이미지 연관 QA | 테이블 구조 기반 | 테이블 마크다운 입력 |

## 파일 구조

```
QA_example/
├── __init__.py           # 모듈 초기화
├── prompts.py            # 프롬프트 템플릿
├── qa_generator.py       # QA 생성 핵심 로직
├── qa_generation.ipynb   # 사용 예제 노트북
├── README.md             # 이 문서
└── output/               # 생성된 데이터셋
```

## 프롬프트 전략

### Chain-of-Table
- 단계별 표 해석 과정 명시
- 동적 계획법 기반 질문 생성

### Program-of-Thought (PoT)
- 수치 계산을 Python 코드로 생성
- 계산 결과의 무결성 보장

### Tabular Chain-of-Thought
- 추론 과정을 표 형태로 구조화
- Step → Sub-question → Evidence → Reasoning

### Evol-Instruct
- 제약 조건 추가 (Adding Constraints)
- 심층 추론 (Deepening Reasoning)
- 구체화 (Concretizing)
- 입력 복잡도 증가 (Complicating Input)

## 품질 평가 (LLM-as-Judge)

생성된 QA의 품질을 5가지 차원으로 평가:

1. **정확성 (Correctness)**: 답변의 사실적 정확성
2. **충실성 (Faithfulness)**: 테이블 데이터에 대한 충실도
3. **관련성 (Relevance)**: 보험 도메인 실용성
4. **난이도 적절성**: 표기 난이도와 실제 난이도 일치
5. **명확성 (Clarity)**: 질문과 답변의 명확성

## 의존성

- `polling_gemini`: Gemini API 풀링 시스템
- `google-generativeai`: Google Gemini API
- `pyyaml`: YAML 설정 파일 처리

## 라이센스

MIT License
