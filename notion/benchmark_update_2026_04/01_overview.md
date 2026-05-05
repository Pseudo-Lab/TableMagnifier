# table-env-bench 업데이트 요약

## 이번 패스 목표

이번 작업은 두 축으로 진행했다.

1. 기존 canonical family의 난이도 상향
2. OpenAI-compatible LLM API 기반 평가 러너 추가

핵심은 새 family를 급하게 늘리는 것이 아니라, 현재 canonical family가 실제로 더 강한 상호작용형 Visual TableQA reasoning을 재도록 만드는 것이었다.

## 이번에 바뀐 것

### 1. canonical family 메타데이터 강화

기존에는 family별 operator, cue, answer form 중심 메타데이터가 주로 남아 있었다. 이번에는 각 episode/manifest가 실제로 어떤 evidence를 읽어야 하는지 더 명확히 남기도록 확장했다.

추가로 강조한 항목:

- `required_sheet_ids`
- `required_page_refs`
- `required_actions`
- `required_evidence`
- `level_rationale`
- `difficulty_tier`

이제 단순히 "어려운 문제"가 아니라, 왜 어려운지와 어떤 shortcut을 막으려는지 artifact 수준에서 추적 가능해졌다.

### 2. difficulty ramp 문서화

난이도 상향 기준을 새 문서로 고정했다.

- Level 2/3와 `eval_hard`는 단순히 페이지 수를 늘리는 방식이 아니라,
  - 실제 읽어야 하는 근거 증가
  - counterfactual 압력 강화
  - operator order 민감도 강화
  - scope disambiguation 강화
  - text-only shortcut 차단
  쪽으로 설계 기준을 명확히 했다.

### 3. LLM evaluation runner 추가

첫 버전은 가장 단순하고 결정론적인 경로를 택했다.

- `WorkbookEnv`를 Python 안에서 직접 실행
- 모델 입력은 `viewport_svg + question + compact state`
- 모델 출력은 기존 action schema와 동일
- provider 범위는 `OpenAI-compatible` API로 제한

즉, 현재 benchmark의 core contract를 바꾸지 않고, 외부 LLM이 같은 action space 위에서 성능을 낼 수 있게 연결했다.

## 왜 중요한가

이 변경으로 benchmark는 두 가지 면에서 더 쓸모 있어졌다.

### benchmark 설계 측면

- canonical family가 "보기에만 workbook-like"한 문제가 아니라
- 실제로 sheet/page/evidence navigation이 필요한 문제인지
- shortcut-resistant한지
- reasoning depth가 level별로 올라가는지

를 더 명시적으로 통제할 수 있게 됐다.

### 평가 측면

- heuristic baseline뿐 아니라
- API 기반 LLM도 같은 env/evaluator/replay 체계 위에서 비교 가능해졌다.

즉, 앞으로는 family별, level별, cue/operator slice별로 모델의 실패 패턴을 더 직접적으로 볼 수 있다.

## 산출물

- 난이도 정책 문서
- eval protocol 보강
- LLM agent/client 추가
- `eval_llm.py` 스크립트 추가
- 대표 episode 화면 캡처

## 대표 화면

![Preview Gallery](assets/gallery_overview.png)
