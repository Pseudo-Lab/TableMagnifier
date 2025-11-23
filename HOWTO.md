# generate_synthetic_table

LangGraph 기반의 Agentic 플로우를 이용해 한국어 표 이미지를 합성 데이터로 변환합니다. 입력 이미지를 HTML 표로 변환한 뒤, 내용을 분석하여 동일한 구조를 가진 라이선스 프리 합성 데이터를 생성하고 JSON으로 파싱합니다.

## 구성

플로우는 다음 5단계로 구성되어 있습니다.

1. **Image2HTML** – 표 이미지를 HTML `<table>` 구조로 복원합니다.
2. **Parse Contents** – 표의 열/행 정보를 요약하고 패턴을 추출합니다.
3. **Generate Synthetic Dataset** – 동일한 구조를 유지하면서 합성 데이터를 채운 HTML 표를 생성합니다.
4. **Self-Reflection** – 생성된 표가 라이선스/개인정보 이슈가 없는지 점검하고, 필요시 재생성을 요청합니다.
5. **Parse Synthetic Table** – 최종 생성된 합성 HTML 표를 구조화된 JSON 포맷으로 변환합니다.

## 주요 코드 설명 (Code Review Guide)

코드 리뷰 시 참고할 주요 파일과 핵심 로직에 대한 설명입니다.

### 1. `generate_synthetic_table/flow.py`
핵심 로직인 LangGraph 플로우가 정의된 파일입니다.

- **`TableState` (TypedDict)**:
  - 플로우 전체에서 공유되는 상태 객체입니다.
  - `image_path`: 입력 이미지 경로
  - `html_table`: 이미지에서 추출된 원본 HTML
  - `table_summary`: 표 구조 및 데이터 패턴 요약
  - `synthetic_table`: 생성된 합성 데이터 HTML
  - `synthetic_json`: 최종 파싱된 JSON 데이터
  - `reflection`, `passed`, `attempts`: 자기 점검 및 재시도 로직을 위한 필드들

- **`build_synthetic_table_graph`**:
  - LangGraph의 노드와 엣지를 연결하여 파이프라인을 구성합니다.
  - `image_to_html` -> `parse_contents` -> `generate_synthetic_table` -> `self_reflection` 순으로 진행됩니다.
  - `self_reflection` 결과에 따라 `revise_synthetic_table`로 이동하여 재시도하거나, 성공 시 `parse_synthetic_table`로 이동하여 종료합니다.

- **Nodes**:
  - `image_to_html_node`: VLM을 사용해 이미지를 HTML로 변환합니다.
  - `parse_synthetic_table_node`: 합성된 HTML을 최종적으로 JSON으로 파싱하여 활용하기 쉽게 만듭니다.

### 2. `generate_synthetic_table/runner.py`
CLI 실행 및 파일 입출력을 담당합니다.

- **`run_with_args`**:
  - `argparse`로 받은 인자를 처리하고 플로우를 실행합니다.
  - 실행 결과(`html_table`, `synthetic_table`, `synthetic_json`)를 각각 파일로 저장하는 로직이 포함되어 있습니다.

### 3. Prompts (`generate_synthetic_table/prompts/`)
LLM에게 전달되는 지시사항들입니다. 영문으로 작성되어 성능을 최적화했습니다.

- **`image_to_html.txt`**: 이미지에서 표 구조(rowspan, colspan 포함)를 정확히 추출하도록 지시합니다.
- **`generate_synthetic_table.txt`**: 원본 구조를 유지하되, 내용은 합성 데이터로 완전히 대체하도록 지시합니다.
- **`self_reflection.txt`**: 생성된 데이터의 품질과 구조적 정확성을 검증하는 QA 프롬프트입니다.
- **`parse_synthetic_table.txt`**: HTML을 JSON으로 변환하는 규칙을 정의합니다.

## 설치

프로젝트 루트에 `.env` 파일을 만들고 OpenAI 키를 설정합니다.

```bash
echo "OPENAI_API_KEY=sk-..." > .env
```

의존성은 `pyproject.toml`을 통해 관리되므로 원하는 패키지 매니저로 설치합니다. `uv`를 사용하는 경우:

```bash
uv sync
```

또는 일반 `pip`를 사용할 경우:

```bash
pip install .
```

## 사용법

명령행 인터페이스를 이용해 플로우를 실행할 수 있습니다.

```bash
# 기본 실행 (결과를 result.json 및 관련 파일로 저장)
python main.py I_table_78.png --save-json result.json

# 모델 및 옵션 지정
python main.py I_table_78.png --model gpt-4o --temperature 0.1 --save-json output.json
```

- `image_path`: (필수) 변환할 표 이미지 파일 경로
- `--model`: 사용할 OpenAI 모델 이름 (기본값: `gpt-4.1-mini`)
- `--temperature`: 모델 온도 (기본값: `0.2`)
- `--save-json`: 최종 상태를 JSON 파일로 저장합니다. (파생된 HTML 및 JSON 파일들도 함께 저장됩니다)

실행 결과에는 HTML 표, 내용 요약, 합성 표, 자기 점검 결과, 그리고 파싱된 JSON 데이터가 포함됩니다.
