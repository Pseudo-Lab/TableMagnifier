# Episode Rulebook

이 문서는 canonical episode를 구성하는 `rule 단위`를 정의한다.

여기서 rule은 episode 전체가 아니라, episode를 이루는 작은 reasoning mechanic을 뜻한다.  
좋은 episode는 rule을 무작정 많이 쌓는 것이 아니라, `primary rule`과 `support rule`을 명확히 조합한다.

## 1. rulebook의 목적

- family proposal을 더 작고 재사용 가능한 unit으로 쪼갠다
- generator code 안에만 mechanic이 숨어 있지 않게 한다
- episode draft 단계에서 operator, cue, answer form을 함께 점검한다

## 2. rule unit schema

새 rule을 정의할 때는 아래 항목을 채운다.

- `rule_id`
- 한 줄 설명
- `primary_visual_cue`
- `secondary_visual_cue` optional
- `operator_type`
- `input_surface`
- `output_expectation`
- `compatible_families`
- `recommended_levels`
- `compatible_answer_forms`
- `common_failure_modes`
- `disallowed_shortcuts`

## 3. Rule 타입

### 3.1 `scope_by_merged_header`

설명:

- merged header span이 target scope를 결정한다

대표 cue:

- merged-cell span direction

대표 answer form:

- target cell
- row/column label

추천 family:


### 3.2 `membership_by_marker`

설명:

- marker의 모양, 위치, 개수가 포함/제외 조건을 결정한다

대표 cue:

- marker morphology
- icon anchor position

대표 answer form:

- count
- target subtotal cell
- mini-table choice

추천 family:

- `legend_operator_composition`

### 3.3 `membership_by_pattern_not_color`

설명:

- 색이 아니라 fill pattern 또는 texture가 실제 기준이 된다

대표 cue:

- conditional formatting pattern

대표 answer form:

- statement choice
- target cell

추천 family:


### 3.4 `hierarchy_by_indentation`

설명:

- 들여쓰기 깊이가 row hierarchy를 결정한다

대표 cue:

- indentation depth
- row group band

대표 answer form:

- row label
- target subtotal cell

추천 family:


### 3.5 `section_boundary_by_band`

설명:

- 두꺼운 line, band, section separator가 rule boundary를 정한다

대표 cue:

- border / band semantics

대표 answer form:

- target section choice
- statement choice

추천 family:

- `order_sensitive_worksheet_pipeline`

### 3.6 `table_chart_anchor_match`

설명:

- chart glyph와 table block 사이의 대응 관계를 복원한다

대표 cue:

- chart-to-table alignment

대표 answer form:

- row label
- statement choice

추천 family:

- `cross_format_table_reasoning`

### 3.7 `exception_by_note_attachment`

설명:

- note text 자체보다 note가 붙은 위치가 rule 예외 범위를 정한다

대표 cue:

- note anchor

대표 answer form:

- statement choice
- target cell

추천 family:

- `cross_format_table_reasoning`

### 3.8 `stage_order_matters`

설명:

- operator stage의 순서가 결과를 바꾼다

대표 cue:

- operator strip
- stage band order

대표 answer form:

- mini-table choice
- short symbolic output

추천 family:

- `order_sensitive_worksheet_pipeline`

### 3.9 `viewport_pan_to_target_column`

설명:

- 초기 viewport에 보이지 않는 target column까지 zoom/pan으로 이동해야 같은 행의 최종 값을 읽을 수 있다

대표 cue:

- wide worksheet grid
- column offset
- viewport window / viewbox position

대표 answer form:

- statement choice
- target cell
- value choice

추천 family:

- `excel_viewport_sheet_navigation`

disallowed shortcuts:

- `initial_viewport_only`
- `no_pan_zoom`
- `sheet_skip`

필수 metadata:

- `required_navigation.required_viewport_states`
- `required_navigation.forbidden_shortcuts`

## 4. episode 조합 규칙

하나의 episode는 보통 아래 조합을 권장한다.

- Level 1
  - primary rule 1개
  - optional support rule 0-1개
- Level 2
  - primary rule 1개
  - support rule 1개
- Level 3
  - primary rule 1개
  - support rule 1-2개
  - disambiguation rule 1개 가능

좋은 예:

- primary: `scope_by_merged_header`
- support: `membership_by_marker`

좋은 예:

- primary: `membership_by_pattern_not_color`
- disambiguation: `exception_by_note_attachment`

나쁜 예:

- rule 5개를 한 episode에 다 넣어 level만 높다고 주장하는 것

## 5. rule 선택 기준

- rule 하나가 실제 visual cue에 anchored 되어 있는가?
- text-only shortcut 없이 설명 가능한가?
- family identity와 맞는가?
- answer form과 자연스럽게 연결되는가?

## 6. 구현 전에 꼭 적어야 하는 것

새 episode 초안을 만들 때는 최소한 아래 두 줄을 먼저 적는다.

- primary rule:
- why text-only fails:

이 두 줄을 못 쓰면 아직 episode가 준비되지 않은 것이다.

## 7. 문서 연결

- [docs/visual_cue_inventory.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/visual_cue_inventory.md)
- [docs/real_data_authoring_policy.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/real_data_authoring_policy.md)
- [docs/domain_vocab_policy.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/domain_vocab_policy.md)
- [docs/human_readability_checklist.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/human_readability_checklist.md)
- [docs/operator_taxonomy.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/operator_taxonomy.md)
- [docs/answer_form_policy.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/answer_form_policy.md)
- [docs/level_design_policy.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/level_design_policy.md)
- [docs/episode_validation_checklist.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/episode_validation_checklist.md)
