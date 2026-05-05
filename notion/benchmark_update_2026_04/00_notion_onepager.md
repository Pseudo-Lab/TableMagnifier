# table-env-bench 업데이트 요약

## 한 줄 요약

이번 패스에서는 `canonical benchmark 난이도 상향`과 `OpenAI-compatible LLM 평가 러너 추가`를 함께 진행했다.

## 왜 이 작업을 했나

기존 저장소는 env, renderer, UI, replay, baseline, API까지 기본 골격은 이미 갖춰져 있었다. 하지만 canonical benchmark가 실제로 얼마나 강한 Visual TableQA-rooted reasoning을 재는지, 그리고 그 benchmark를 LLM API로 어떻게 평가할지에 대한 운영 레이어는 더 명확해질 필요가 있었다.

이번 변경의 목적은 두 가지였다.

1. 기존 canonical family를 더 shortcut-resistant하게 만들기
2. 외부 LLM을 같은 env/evaluator/replay contract 위에서 평가할 수 있게 만들기

## 이번에 바뀐 핵심

### 1. canonical family 난이도 상향

난이도는 단순히 페이지 수를 늘리는 방향이 아니라 아래 축으로 강화했다.

- 실제로 읽어야 하는 evidence surface 증가
- counterexample pressure 강화
- operator order 민감도 강화
- scope disambiguation 강화
- text-only shortcut 차단

이를 위해 canonical/eval_hard manifest와 catalog에 아래 항목을 더 강하게 채우도록 바꿨다.

- `required_sheet_ids`
- `required_page_refs`
- `required_actions`
- `required_evidence`
- `required_visual_cues`
- `shortcut_probes`
- `level_rationale`
- `difficulty_tier`

이제 각 episode가 “무엇을 읽어야 풀리는지”를 artifact 차원에서 더 명확히 추적할 수 있다.

### 2. family별 강화 포인트

#### `channel_policy_transfer`

- Level 2부터 example 보강 페이지가 중요해짐
- Level 3에서는 appendix/note가 실제 rule 확정에 필요
- 막으려는 shortcut:
  - 첫 example만 읽고 전이
  - scope band 무시
  - icon만 단순 매칭

![channel_policy_transfer](assets/channel_policy_transfer_l3_query.png)

#### `inventory_exception_disambiguation`

- counterexample sheet를 optional 참고 자료가 아니라 wrong rule 제거 장치로 다룸
- Level 2 이상에서는 추가 counterexample page나 note를 읽지 않으면 규칙이 충분히 고정되지 않게 설계
- 막으려는 shortcut:
  - single-page submit
  - counterexample 무시
  - text-only guess

![inventory_exception_disambiguation](assets/inventory_exception_disambiguation_l3_counterexample.png)

#### `report_scope_reconciliation`

- merged header, indentation, subtotal boundary를 결합 cue로 취급
- Level 2 이상에서는 notes sheet가 범위 확정 근거가 되도록 강화
- 막으려는 shortcut:
  - hierarchy 무시
  - subtotal row를 데이터 row로 오인

![report_scope_reconciliation](assets/report_scope_reconciliation_l3_overview.png)

#### `legend_operator_composition`

- legend mapping과 worked example을 분리
- operator order를 따로 읽지 않으면 query 해석이 흔들리도록 설계
- 막으려는 shortcut:
  - operator order 무시
  - query table만 보고 포함/제외를 추정

![legend_operator_composition](assets/legend_operator_composition_l3_legend.png)

### 3. `eval_hard` 의미 강화

`eval_hard`는 canonical보다 한 단계 더 강한 상호작용 요구를 명시한다.

- decisive evidence를 여러 surface에서 읽어야 함
- premature submit이 명확히 불이익을 받음
- counterfactual pair를 구분해야 함
- restricted baseline이 낮은 evidence coverage를 보이도록 설계

즉, `eval_hard`는 정확도뿐 아니라 “제대로 읽었는가”를 더 강하게 드러내는 트랙이다.

## LLM 평가 러너 추가

### 설계 원칙

첫 버전은 가장 단순하고 결정론적인 경로를 택했다.

- `WorkbookEnv`를 Python 안에서 직접 실행
- 모델 입력은 `viewport_svg + question + compact state`
- 모델 출력은 JSON action 1개만 허용
- provider 범위는 `OpenAI-compatible` API만 지원

즉, benchmark core를 바꾸지 않고, 기존 action schema 위에 LLM을 얹었다.

### 추가된 구성요소

- `LLMAgent`
  - observation 직렬화
  - 모델 응답 파싱
  - parse retry
  - run metadata 누적
- OpenAI-compatible client
  - `model`
  - `base_url`
  - `api_key`
- `eval_llm.py`
  - `canonical_dev`
  - `eval_hard_dev`
  - `eval_hard_holdout`
  - family / level / template / seed 필터 지원

### LLM artifact에 추가 기록되는 정보

- `model_config`
- `llm_trace`
- `usage`
- `latency_ms`
- `finish_reason`
- `parse_retry_count`
- `api_error`

이 덕분에 단순 accuracy뿐 아니라 파싱 안정성, 토큰 사용량, 응답 실패 패턴까지 함께 볼 수 있다.

## 실행 예시

```bash
cd /mnt/c/Users/imssh/Documents/poc_1
OPENAI_API_KEY=... uv run python -m table_env_bench.scripts.eval_llm --suite canonical_dev --model gpt-4o-mini
```

## 검증

관련 테스트는 아래 범위에서 통과했다.

- `tests/test_llm_agent.py`
- `tests/test_scripts.py`
- `tests/test_pilot_families.py`
- `tests/test_eval_hard.py`
- `tests/test_scoring.py`

## 대표 화면

전체 preview gallery:

![Preview Gallery](assets/gallery_overview.png)

## 참고 자료

- 상세 요약: `01_overview.md`
- 난이도 상향 정리: `02_difficulty_ramp.md`
- LLM 평가 러너 정리: `03_llm_eval_runner.md`
- 예시 캡처 모음: `04_example_gallery.md`
- 원본 SVG preview: `raw_previews/`
