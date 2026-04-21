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

## 운영 메모

- 이 문서는 새 canonical family를 추가할 때도 같은 형식으로 확장한다
- manifest/test에서 이미 보장되는 항목은 여기서 다시 자유서술로만 남기지 않는다
- text-only shortcut과 distractor failure mode는 generator 수정 시 함께 갱신한다
- readability는 스타일 문제가 아니라 benchmark integrity requirement다
