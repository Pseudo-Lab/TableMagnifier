# Evaluation Protocol

채점은 correctness와 efficiency를 분리해 기록하고, environment core는 특정 결합식에 종속되지 않게 둡니다.

## Episode 결과 계약

최소 기록 필드:

- `correctness`
- `efficiency`
- `overall`
- `action_count`
- `sheet_switch_count`
- `page_switch_count`
- `note_open_count`
- `replay_trace`

현재 `EpisodeEvaluator` / `ActionCountEfficiencyScorer` 인터페이스는 그대로 재사용할 수 있습니다.

## 정답 판정

현재 correctness는 normalized exact match를 유지합니다.

- 공백 정리
- 쉼표 허용
- 한국어 접미어 `원`, `만원`, `개`, `%` 등 일부 허용
- `accepted` alias 허용

워크북 과제에서도 exact numeric answer는 가능하면 표, 범례, note, appendix에서 읽을 수 있게 설계합니다. 차트는 주로 탐색 신호로 사용하고, pixel-perfect OCR 없이는 답하기 어려운 문제는 피합니다.

## 효율 점수

### 현재 코드와의 정렬

- 현재 repo는 action count 기반 효율 scorer를 이미 갖고 있다.
- 현재 이 scorer를 기본값으로 유지한다.

### workbook용 추가 metadata

효율 scorer 교체를 위해 replay에 아래 metadata를 남기는 것을 권장합니다.

- `sheet_switch_count`
- `page_switch_count`
- `unique_sheets_visited`
- `unique_pages_visited`
- `blank_click_count`
- `resolved_region_count`
- `note_open_count`

### 권장 정책

- 기본 로컬 scorer
  - action count 기반
- 향후 확장 scorer
  - human-normalized navigation efficiency
  - family-aware expected-cost scorer

## Overall score

기본 로컬 runner는 현재처럼 `correctness * efficiency`를 사용해도 됩니다. 다만 benchmark artifact에는 항상 component score를 함께 남겨야 하며, leaderboard나 논문용 집계는 별도 combiner를 사용해도 되게 유지합니다.

## Replay logging requirements

replay event마다 최소한 아래를 포함해야 합니다.

- `action`
- `before`
- `after`
- `reward`
- `terminated`
- `truncated`
- `metadata.page_coordinates`
- `metadata.resolved_region` 또는 `metadata.resolved_target`
- `metadata.opened_note`

`before/after`에는 workbook navigation state가 남아야 합니다.

- `sheet_index`
- `page_index`
- `zoom_index`
- `viewbox`
- `selected_region_id`
- `open_note_id`

## 집계 단위

- family별 평균
- level별 평균
- overall 평균
- human / agent / dev mode는 분리 집계

human evaluation 결과를 저장할 때도 같은 replay schema를 사용하되, `metadata.source = "human"` 같은 출처 필드를 남기는 것을 권장합니다.

## LLM runner artifact

Tool-calling LLM runner는 baseline artifact에 아래 필드를 추가로 남깁니다.

- `model_config`
  - `model`
  - `base_url`
  - `prompt_template_version`
- `response_mode`
  - 현재 기본값은 `tool_calls`
- `provider_mode`
  - `responses` 또는 `chat_completions`
- `reasoning_effort`
- `llm_trace`
  - step별 action, tool name/arguments, latency, finish_reason, usage, estimated cost 요약
- `usage`
  - total input/cached_input/output/reasoning/total tokens
- `latency_ms`
- `finish_reason`
- `parse_retry_count`
- `tool_retry_count`
- `estimated_cost_usd`
- `api_error`

LLM runner도 correctness / efficiency / overall 계산은 기존 `EpisodeEvaluator`를 그대로 사용합니다.
