# Action Schema

이 문서는 현재 구현된 workbook benchmark 액션 계약을 설명합니다.

## 설계 원칙

- 액션은 시트/페이지/영역 탐색을 중심으로 한다.
- `click(x, y)`는 저수준 좌표 입력이지만, 의미적으로는 "영역 grounding"이어야 한다.
- 액션 처리는 결정론적이어야 한다.
- 모든 액션은 replay에서 재현 가능해야 한다.
- 사용자 노출 문구는 한국어로, API 식별자는 영어로 유지한다.

## MVP 액션

- `zoom_in`
- `zoom_out`
- `pan_up`
- `pan_down`
- `pan_left`
- `pan_right`
- `select_sheet(name_or_index)`
- `next_page`
- `prev_page`
- `click_region(x, y)`
- `submit_answer(text)`

## 액션 의미

### `select_sheet(name_or_index)`

- 입력값은 observation에 노출된 탭 이름 또는 0-based index다.
- 이미 열린 시트를 다시 여는 경우 no-op이어야 한다.
- 시트 변경 시 기본 페이지와 기본 줌 상태로 이동하는 정책을 권장한다.

예시:

```json
{"type": "select_sheet", "sheet": "부록"}
```

### `next_page` / `prev_page`

- 현재 활성 시트 내부에서만 이동한다.
- 시트 밖으로 넘어가면 안 된다.
- 페이지 전환 후 선택된 영역과 열린 노트는 초기화하는 쪽을 기본 정책으로 둔다.

### `click_region(x, y)`

- 현재 viewport 좌표계에서 처리한다.
- 빌드 pass에서는 셀 id를 직접 노출하지 않고, 클릭 결과를 가장 가까운 `region`으로 해석해야 한다.
- 클릭 결과는 다음 중 하나여야 한다.
  - 유효한 region으로 resolve되어 해당 영역 중심으로 이동
  - note marker / legend marker / appendix marker를 선택
  - 빈 공간 클릭으로 no-op

replay metadata 권장 필드:

- `page_coordinates`
- `resolved_region.public_id`
- `resolved_region.role`
- `resolved_region.visible_label`
- `resolved_region.sheet`
- `resolved_region.page`

예시:

```json
{"type": "click_region", "x": 320, "y": 180}
```

### `submit_answer(text)`

- 최종 답안을 제출하고 episode를 종료한다.
- 정답 채점은 환경 밖의 scorer가 담당하되, 기본 env reward는 correctness와 정렬되게 유지해도 된다.

예시:

```json
{"type": "submit_answer", "text": "462000000"}
```

## Observation과의 관계

agent mode observation에는 다음만 포함하는 것을 권장한다.

- `viewport_svg`
- `question`
- `remaining_action_budget`
- `active_sheet`
- `sheet_tabs`
- `current_page_index`
- `page_count_in_sheet`
- `action_history_summary`

다음은 기본적으로 금지한다.

- raw spreadsheet data
- hidden region map
- answer logic
- invisible note ids
- full structured workbook dump
