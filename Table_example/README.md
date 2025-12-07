# Table Example - 보험 테이블 추출기

`polling_gemini` 패키지를 활용하여 보험 문서 이미지에서 테이블을 Markdown 형식으로 추출하는 예제입니다.

## 주요 특징

- **VLM + OCR 하이브리드 접근**: Gemini의 시각적 추론 능력과 OCR 텍스트를 결합
- **보험 도메인 특화 프롬프트**: 계층적 헤더, 셀 병합, 복합 데이터 처리에 최적화
- **자동 API 키 로테이션**: `polling_gemini` 패키지를 통한 API 키 관리
- **동기/비동기 지원**: 대용량 처리를 위한 비동기 API 지원

## 설치

프로젝트 루트에서:

```bash
uv sync
```

## 사용법

### 1. 기본 사용

```python
from Table_example import extract_table_from_image

# 이미지에서 테이블 추출
result = extract_table_from_image("insurance_table.png")
print(result)
```

### 2. OCR 참조 텍스트와 함께 사용

```python
from Table_example import extract_table_from_image

# OCR로 먼저 추출한 텍스트가 있는 경우
ocr_text = """| 구분 | 보험기간 | 납입기간 |
| 상해사망 | 80세 | 20년 |"""

result = extract_table_from_image(
    "insurance_table.png",
    ocr_markdown=ocr_text  # OCR 결과를 참조로 제공
)
```

### 3. 비동기 처리

```python
import asyncio
from Table_example import aextract_table_from_image

async def process_multiple_images():
    images = ["table1.png", "table2.png", "table3.png"]
    
    # 동시에 여러 이미지 처리
    tasks = [aextract_table_from_image(img) for img in images]
    results = await asyncio.gather(*tasks)
    
    return results

results = asyncio.run(process_multiple_images())
```

### 4. InsuranceTableExtractor 클래스 직접 사용

```python
from Table_example import InsuranceTableExtractor

# 추출기 인스턴스 생성
extractor = InsuranceTableExtractor(
    config_path="apis/gemini_keys.yaml",  # 커스텀 설정 경로
    model_name="gemini-2.5-flash"         # 모델 지정
)

# 테이블 추출
result = extractor.extract("insurance_table.png")

# API Pool 상태 확인
status = extractor.get_pool_status()
print(f"현재 API 키: {status['current_key']['name']}")
```

## 프롬프트 설계

### System Prompt 핵심 원칙

1. **구조적 완전성**: 병합된 셀을 비정규화하여 모든 행에 값 채우기
2. **헤더 평탄화**: 다중 행 헤더를 언더스코어(_)로 연결하여 단일 행으로 변환
3. **데이터 무결성**: 금액 포맷 정리, 퍼센트 유지, 부가 정보 제거
4. **Hybrid Reference**: OCR 텍스트 참조로 오타 교정

### User Prompt Chain-of-Table 단계

1. **구조 분석**: 레이아웃, 헤더 행 수, 병합 셀 식별
2. **헤더 처리**: 다중 행 헤더 → 단일 행 변환
3. **데이터 추출**: 값 추출 및 병합 셀 반복 입력
4. **포맷팅 검증**: 금액 정리, 컬럼 개수 확인

## 테스트

```bash
cd TableMagnifier
python -m Table_example.test_extraction
```

### 테스트 이미지 준비

`Table_example/sample_images/` 폴더에 테스트할 보험 테이블 이미지를 추가하세요:
- 지원 형식: PNG, JPG, JPEG, GIF, WebP, BMP
- 권장: 해상도가 높은 테이블 이미지

## 출력 예시

입력 이미지:
```
┌─────────────┬────────────────────────────┐
│             │        해지환급금          │
│    구분     ├──────────────┬─────────────┤
│             │     금액     │   환급률    │
├─────────────┼──────────────┼─────────────┤
│   1년       │  100,000원   │    10%      │
│   5년       │  500,000원   │    50%      │
│   10년      │ 1,000,000원  │   100%      │
└─────────────┴──────────────┴─────────────┘
```

출력 Markdown:
```markdown
| 구분 | 해지환급금_금액 | 해지환급금_환급률 |
| :--- | :--- | :--- |
| 1년 | 100000 | 10% |
| 5년 | 500000 | 50% |
| 10년 | 1000000 | 100% |
```

## 파일 구조

```
Table_example/
├── __init__.py           # 패키지 초기화
├── prompts.py            # 시스템/사용자 프롬프트 정의
├── table_extractor.py    # 테이블 추출기 클래스
├── test_extraction.py    # 테스트 코드
├── sample_images/        # 테스트 이미지 폴더
└── README.md             # 이 문서
```

## API 키 설정

`apis/gemini_keys.yaml` 파일에 Gemini API 키를 설정하세요:

```yaml
api_keys:
  - key: "YOUR_GEMINI_API_KEY"
    name: "key1"
    enabled: true

settings:
  model: "gemini-2.5-flash"
  temperature: 0.1
  max_retries: 3
  retry_delay: 2
```

## 라이센스

MIT License
