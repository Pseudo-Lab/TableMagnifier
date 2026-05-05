# Canonical Quality Audit

이 문서는 active canonical family가 `docs/episode_validation_checklist.md`와 `docs/level_design_policy.md`를 얼마나 충실히 따르는지 점검하는 품질 기준표다.

## 공통 pass 기준

- 모든 template는 `primary_operator`, `support_operator`, `required_visual_cues`, `expected_reasoning_steps`를 가진다
- 모든 template는 `text_only_failure_modes`, `distractor_failure_modes`, `level_rationale`를 가진다
- 모든 template는 적어도 1개의 non-text cue가 필요해야 한다
- 모든 template는 family topology에 맞는 `required_sheet_ids`와 `required_page_refs`를 가진다
- full-seed readability audit에서 `invalidLayout == false`, `layoutErrors == []`, text clipping zero를 만족해야 한다

## 1. `channel_policy_transfer`

### family-level audit

- 핵심 topology: `examples -> query`, L2는 `examples p2`, L3는 `appendix` 추가
- 핵심 cue: `icon_anchor`, `band_scope`, `row_group_band`, `note_scope`
- 핵심 risk: example이나 appendix를 건너뛰고 query만 OCR 하는 shortcut

### template audit

| template | answer form | primary / support | text-only shortcut to reject | distractor focus |
| --- | --- | --- | --- | --- |
| `icon_scope_cell` | `cell_choice` | `select_scope` / `transfer` | band, group, anchor를 무시한 query-only shortcut | 다른 band, 다른 group, wrong anchor |

### level progression

- L1: 2-3 step, 예시 1페이지 + query
- L2: 3-4 step, 예시 보강 페이지 추가
- L3: 4-5 step, appendix 메모로 anchor 해석 보정

## 2. `report_scope_reconciliation`

### family-level audit

- 핵심 topology: `overview -> query`, Level 2/3은 `notes` 추가
- 핵심 cue: `merged_header_scope`, `indentation_depth`, `subtotal_block`
- 핵심 risk: 표의 hierarchy를 평평한 row/column 텍스트로만 읽는 shortcut

### template audit

| template | answer form | primary / support | text-only shortcut to reject | distractor focus |
| --- | --- | --- | --- | --- |
| `merged_scope_cell` | `cell_choice` | `select_scope` / `match` | 헤더 depth와 들여쓰기 무시 | 다른 팀 셀, 소계 행, 다른 반기 열 |
| `grouped_statement` | `statement_choice` | `verify_statement` / `scope_resolution` | adjacency만 읽고 group boundary 무시 | 모든 팀 합, 바로 위 한 행 복사 |
| `subtotal_row_label` | `row_label_choice` | `classify` / `scope_resolution` | 소계 라벨만 읽고 실제 묶음 미확인 | 단일 팀, 전체 팀 묶음 |

### level progression

- L1: 2-3 step, shallow hierarchy
- L2: 3-4 step, 메모로 group boundary 고정
- L3: 4-5 step, nested scope + answer indirection

## 3. `inventory_exception_disambiguation`

### family-level audit

- 핵심 topology: `examples -> exception -> query`, L2/L3는 `exception-p2`와 note가 추가됨
- 핵심 cue: `pattern_marker`, `icon_anchor`, `row_group_band`, `note_scope`
- 핵심 risk: 반례나 note를 건너뛰고 examples만 보고 규칙을 확정하는 shortcut

### template audit

| template | answer form | primary / support | text-only shortcut to reject | distractor focus |
| --- | --- | --- | --- | --- |
| `pattern_vs_icon_statement` | `statement_choice` | `verify_statement` / `disambiguate_by_exception` | examples만 읽고 pattern rule을 그대로 고르는 shortcut | wrong pattern, wrong icon, wrong group scope |

### level progression

- L1: 3-4 step, examples와 예외 사례를 비교해 wrong rule을 버린다
- L2: 3-4 step, exception-p2 note로 group scope를 고정한다
- L3: 4-5 step, note를 반영한 뒤 query의 다른 surface format으로 전이한다

## 4. `marker_position_rule_transfer`

### family-level audit

- 핵심 topology: `examples -> legend -> exception -> query`, Level 2/3은 `examples-p2`, Level 3은 exception note가 추가됨
- 핵심 cue: `icon_anchor`, `legend_mapping`, `exception_contrast`, `note_scope`
- 핵심 risk: triangle shape만 보고 marker position과 legend/exception surface를 건너뛰는 shortcut

### template audit

| template | answer form | primary / support | text-only shortcut to reject | distractor focus |
| --- | --- | --- | --- | --- |
| `corner_anchor_statement` | `statement_choice` | `match_mapping` / `convert_representation` | marker shape이나 query text만 읽고 anchor 위치를 무시하는 shortcut | wrong anchor, legend skip, exception skip, note-scope skip |

### level progression

- L1: 3 step, 예시/범례/반례로 두 anchor mapping을 전이
- L2: 3-4 step, 추가 예시 페이지와 네 모서리 variation을 함께 사용
- L3: 4-5 step, exception note로 적용 묶음을 고정하고 anchor 의미를 조합 판정

## 5. `excel_viewport_sheet_navigation`

### family-level audit

- 핵심 topology: `examples -> query`, Level 2는 `examples-p2`, Level 3은 `operators` 추가
- 핵심 cue: `wide_grid`, `column_offset`, `viewport_pan`, `sheet_page_state`
- 핵심 risk: 초기 viewport에 보이는 점검 열 값을 고르거나, 사례/연산자 시트를 건너뛰고 query만 읽는 shortcut

### template audit

| template | answer form | primary / support | text-only shortcut to reject | distractor focus |
| --- | --- | --- | --- | --- |
| `wide_sheet_rule_transfer` | `statement_choice` | `match_column_offset` / `rule_transfer` | zoom/pan 없이 초기 viewport 값이나 row text만 읽는 shortcut | initial check value, wrong row target, skipped operator rule |

### level progression

- L1: 3-4 step, 사례에서 target 열 규칙을 읽고 질의의 오른쪽 target column까지 이동
- L2: 4-5 step, 두 번째 사례 페이지로 반복 규칙을 확인한 뒤 질의에 적용
- L3: 5 step, 연산자 시트가 같은 행 라벨과 target 열 이동 규칙을 고정

### navigation integrity checks

- `required_navigation.required_viewport_states`는 최소 `sheet_id`, `page_id`, `min_zoom_index`, `required_action_types`, `match`, `target_rects`를 가져야 한다.
- `target_center_in_viewbox`는 target center가 현재 viewbox 안에 들어와야 visited로 본다.
- `initial_viewport_only`, `no_pan_zoom`, `sheet_skip` shortcut probes가 모두 meaningful하게 실패해야 한다.

## 운영 메모

- 이 문서는 새 canonical family를 추가할 때도 같은 형식으로 확장한다
- manifest/test에서 이미 보장되는 항목은 여기서 다시 자유서술로만 남기지 않는다
- text-only shortcut과 distractor failure mode는 generator 수정 시 함께 갱신한다
- readability는 스타일 문제가 아니라 benchmark integrity requirement다
