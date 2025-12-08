# 출력 파일 및 워크플로우 문서

`generate_synthetic_table`을 실행할 때 `--save-json <PATH>` 옵션을 사용하면, 해당 경로를 기반으로 여러 결과 파일이 생성됩니다.

예를 들어, `--save-json output/result.json`으로 실행했을 경우:

| 파일명 | 설명 |
|--------|------|
| `result.json` | **메인 결과 파일**. 생성 과정에 대한 메타데이터, 다른 파일들의 경로, 에러 로그, 테이블 요약, 자가 성찰(Reflection) 로그 등을 포함합니다. |
| `result_parsed.html` | **파싱된 HTML**. 원본 이미지에서 추출된 중간 단계의 HTML 표현입니다 (PyMuPDF 또는 LLM 사용). 합성 데이터 생성의 기초가 됩니다. |
| `result_synthetic.html` | **합성 HTML**. 원본 이미지의 구조와 내용을 모방하여 새롭게 생성된 최종 HTML 테이블입니다. |
| `result_synthetic.json` | **합성 데이터 JSON**. 합성 HTML을 파싱하여 구조화한 JSON 데이터입니다. |

## JSON 구조 (`result.json`)

```json
{
  "image_path": "path/to/original/image.png",
  "table_summary": "테이블 구조 요약...",
  "reflection": "LLM의 자가 성찰 결과 텍스트...",
  "errors": [],
  "synthetic_json": { ... },
  "html_table_path": "output/result_parsed.html",
  "synthetic_table_path": "output/result_synthetic.html"
}
```

---

## LangGraph 워크플로우 노드별 상세 출력

이 프로젝트는 LangGraph를 사용하여 단계별로 처리를 수행합니다. 각 노드는 `TableState` 딕셔너리를 업데이트하며, 주요 출력값은 다음과 같습니다.

### 1. 입력 처리 및 파싱 단계

| 노드 (Node) | 역할 | 주요 상태 업데이트 (`TableState`) |
|-------------|------|-----------------------------------|
| `load_html_input` | HTML 파일을 입력받을 경우 내용을 로드합니다. | `html_table`: 로드된 HTML 내용 |
| `image_to_html` | 이미지를 LLM에게 보내 HTML로 변환합니다. | `html_table`: LLM이 생성한 HTML |
| `pymupdf_parse` | PyMuPDF 라이브러리를 사용해 규칙 기반으로 테이블을 파싱합니다. | `html_table`: 파싱된 간단한 HTML 구조 |
| `validate_parsed_table` | PyMuPDF 파싱 결과가 유효한지 LLM이 검사합니다. | `valid_pymupdf`: 유효성 여부 (`True`/`False`) |

### 2. 분석 및 생성 단계

| 노드 (Node) | 역할 | 주요 상태 업데이트 (`TableState`) |
|-------------|------|-----------------------------------|
| `analyze_table` | 파싱된 HTML(`html_table`)을 분석하여 구조를 요약합니다. | `table_summary`: 테이블 구조 및 내용 요약문 |
| `generate_synthetic_table` | 원본 HTML과 요약을 바탕으로, 새로운 값으로 채워진 합성 테이블을 생성합니다. | `synthetic_table`: 새로 생성된 합성 HTML |
| `generate_synthetic_table_from_image` | (고성능 모델용) 이미지에서 직접 합성 테이블을 생성합니다. | `synthetic_table`: 이미지 기반으로 생성된 합성 HTML |

### 3. 검증 및 수정 단계 (반복 가능)

| 노드 (Node) | 역할 | 주요 상태 업데이트 (`TableState`) |
|-------------|------|-----------------------------------|
| `self_reflection` | 생성된 합성 테이블이 원본의 구조를 잘 따르는지 평가합니다. | `reflection`: 평가 텍스트<br>`reflection_json`: 구조화된 평가 결과<br>`passed`: 통과 여부<br>`revision_instructions`: 수정 지침 |
| `revise_synthetic_table` | 평가 결과(`revision_instructions`)를 바탕으로 테이블을 수정합니다. | `synthetic_table`: 수정된 합성 HTML<br>`attempts`: 시도 횟수 증가 |

### 4. 최종 변환 단계

| 노드 (Node) | 역할 | 주요 상태 업데이트 (`TableState`) |
|-------------|------|-----------------------------------|
| `parse_synthetic_table` | 최종 확정된 합성 HTML을 JSON 형식으로 변환합니다. | `synthetic_json`: 최종 데이터의 JSON 표현 |
| `generate_qa` | 합성된 데이터를 바탕으로 QA(질문-답변) 쌍을 생성합니다. | `qa_results`: 생성된 QA 리스트 |

## 사용 예시

```bash
python main.py data/table_image.png \
  --provider gemini \
  --save-json outcomes/my_table_result.json
```

위 명령어는 다음 파일들을 생성합니다:
- `outcomes/my_table_result.json`
- `outcomes/my_table_result_parsed.html`
- `outcomes/my_table_result_synthetic.html`
- `outcomes/my_table_result_synthetic.json`
