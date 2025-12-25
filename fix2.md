# Fix 2: 도메인 맞춤형 프롬프트 (YAML 기반)

## 개요 (Overview)
도메인별 최적화된 프롬프트 관리를 용이하게 하기 위해 기존 텍스트 파일 기반 시스템을 YAML 기반 시스템으로 교체했습니다. 이를 통해 입력 파일의 키나 CLI 인자를 기반으로 특정 도메인(예: 공공/정부 데이터)에 맞는 프롬프트를 자동으로 로드할 수 있습니다.

## 프롬프트 파일 (Prompt Files)
- **`generate_synthetic_table/prompts/default.yaml`**: 파이프라인의 12개 이상의 단계에서 사용되는 기본 프롬프트들을 모두 포함합니다.
- **`generate_synthetic_table/prompts/public.yaml`**: 도메인별 오버라이드 내용을 포함합니다.
  - 예시: `generate_qa_from_image` 프롬프트가 공공 부문 용어에 맞춰 커스터마이징되어 있습니다.

## `generate_synthetic_table/flow.py` 변경 사항
- `_load_yaml_prompts` 함수 구현: YAML 파일 로드 및 캐싱 기능.
- `_load_prompt(name, domain)` 함수 업데이트: `{domain}.yaml`을 먼저 확인하고, 없으면 `default.yaml`을 사용하도록 로직 변경 (Fallback).
- 모든 노드(Node) 함수 업데이트:
  1. `TableState`에서 `domain` 정보를 읽어옴.
  2. 노드 실행 시 `_load_prompt(..., domain)`을 동적으로 호출하여 프롬프트 결정.

```python
# flow.py 내 동적 로딩 예시
def generate_qa_node(llm: ChatOpenAI) -> Callable[[TableState], TableState]:
    def _node(state: TableState) -> TableState:
        # state의 도메인 정보에 따라 프롬프트 로드
        prompt_template = _load_prompt("generate_qa", state.get("domain"))
        # ... 나머지 로직
    return _node
```

## `generate_synthetic_table/runner.py` 변경 사항
- CLI 인자 추가: `--domain`.
- **자동 감지 로직 (Auto-Detection Logic)** 구현:
  - 입력 파일/폴더 이름이 `P_`로 시작하는 경우, 자동으로 `domain="public"`으로 설정.
  - 이 `domain` 값을 `run_synthetic_table_flow`로 전달하여 `TableState`에 반영.

## 사용 방법 (Usage)
`data/P_origin_1`과 같은 폴더를 처리할 때 시스템은 자동으로 'public' 도메인 프롬프트를 적용합니다.
수동으로 지정할 수도 있습니다:
```bash
uv run python main.py data/MyTable --domain public
```
