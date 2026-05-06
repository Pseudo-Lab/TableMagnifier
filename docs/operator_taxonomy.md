# Operator Taxonomy

이 문서는 canonical family가 반복적으로 `subset aggregation`에만 머무르지 않도록, episode에서 사용할 수 있는 operator space를 정의한다.

핵심 원칙:

- operator는 표 안에서 무언가를 "어떻게" 해야 하는지를 나타낸다
- 하나의 family는 한 operator만 볼 수도 있지만, 전체 benchmark는 여러 operator를 골고루 다뤄야 한다
- aggregate는 중요한 operator이지만, benchmark의 기본값이 되어서는 안 된다

## 1. operator 설계 원칙

- 각 episode에는 `primary operator`가 하나 있어야 한다
- Level 2 이상에서는 `support operator` 하나를 더 붙일 수 있다
- 예외 사례나 note는 흔히 `disambiguation operator` 역할을 한다
- answer form은 operator와 자연스럽게 맞아야 한다

예:

- select -> target cell / row label
- classify -> statement choice / mini-table choice
- rank -> row label / statement choice
- aggregate -> value choice / target subtotal cell

## 2. Primary Operator 목록

### 2.1 `select_scope`

정의:

- 어떤 header band, row group, block, section이 현재 relevant scope인지 고른다

좋은 cue:

- merged header
- border band
- indentation

좋은 answer form:

- target cell
- row/column label
- statement choice

### 2.2 `filter_members`

정의:

- 어떤 row/cell만 포함되고 어떤 row/cell은 제외되는지 정한다

좋은 cue:

- marker
- fill pattern
- filter chip

좋은 answer form:

- count
- target subset choice
- mini-table choice

### 2.3 `match_mapping`

정의:

- 한 surface의 항목을 다른 surface의 항목과 대응시킨다

좋은 cue:

- chart/table alignment
- legend item
- note anchor

좋은 answer form:

- statement choice
- row label
- target cell

### 2.4 `order_sequence`

정의:

- 순서에 따라 결과가 달라지는 transformation이나 workflow를 적용한다

좋은 cue:

- operator strip
- stage band
- directional arrow

좋은 answer form:

- mini-table choice
- statement choice
- target stage output

### 2.5 `rank_compare`

정의:

- 특정 scope 안에서 더 크다, 더 먼저 온다, 더 우선이다 같은 비교를 수행한다

좋은 cue:

- grouped row
- chart inset
- conditional formatting

좋은 answer form:

- row label
- statement choice
- top-k choice

### 2.6 `classify_state`

정의:

- 각 row/cell/block을 특정 상태로 분류하거나, 어느 상태에 속하는지 판단한다

좋은 cue:

- icon morphology
- fill pattern
- note anchor

좋은 answer form:

- statement choice
- target class label
- mini-table choice

### 2.7 `verify_statement`

정의:

- 주어진 진술 후보 중 표와 시각 cue를 모두 반영했을 때 참인 것을 고른다

좋은 cue:

- exception surface
- note
- merged header

좋은 answer form:

- A/B/C/D statement choice

### 2.8 `aggregate`

정의:

- 특정 scope 안의 값을 합치거나 count한다

좋은 cue:

- subtotal band
- marker filter
- grouped row

좋은 answer form:

- target subtotal cell
- value choice
- count

주의:

- aggregate를 써도 좋지만, benchmark가 계속 이 operator로만 수렴하면 안 된다

### 2.9 `match_column_offset`

정의:

- 한 sheet에서 학습한 기준 열과 target 열 사이의 위치 관계를 다른 sheet의 같은 구조에 적용한다

좋은 cue:

- wide worksheet grid
- column offset
- viewport window
- repeated row labels

좋은 answer form:

- target cell
- value choice
- statement choice

주의:

- 단순 column lookup이 아니라 사례/연산자 surface에서 유도한 열 이동 규칙을 query에 전이해야 한다
- 초기 viewport 값과 target column 값이 달라야 pan/zoom shortcut을 걸러낼 수 있다

## 3. Support Operator 목록

support operator는 primary operator를 돕는다.

- `resolve_scope`
  - merged header나 hierarchy를 읽어 primary scope를 좁힘
- `disambiguate_by_exception`
  - plausible wrong rule을 제거
- `convert_representation`
  - chart / note / legend surface를 table rule로 번역
- `follow_exception`
  - note나 appendix가 기본 rule을 수정
- `rule_transfer`
  - examples, legend, operators sheet에서 유도한 rule을 query sheet에 적용

## 4. Level별 operator 조합

- Level 1
  - primary operator 1개
  - support operator 0-1개
- Level 2
  - primary operator 1개
  - support operator 1개
- Level 3
  - primary operator 1개
  - support operator 1-2개
  - disambiguation operator가 들어갈 수 있음

좋은 progression 예:

- L1: `select_scope`
- L2: `select_scope + filter_members`
- L3: `select_scope + filter_members + disambiguate_by_exception`

나쁜 progression 예:

- L1부터 `select + filter + aggregate + rank + note exception`을 한 번에 넣기

## 5. family별 operator 추천

  - primary: `select_scope`, `filter_members`, `match_mapping`
  - primary: `verify_statement`, `select_scope`
  - support: `disambiguate_by_exception`
- `legend_operator_composition`
  - primary: `order_sequence`, `match_mapping`
- `cross_format_table_reasoning`
  - primary: `match_mapping`, `classify_state`
  - primary: `select_scope`, `rank_compare`
- `marker_position_rule_transfer`
  - primary: `match_mapping`, `verify_statement`
  - support: `convert_representation`, `disambiguate_by_exception`
- `excel_viewport_sheet_navigation`
  - primary: `match_column_offset`
  - support: `rule_transfer`
- `order_sensitive_worksheet_pipeline`
  - primary: `order_sequence`

## 6. operator coverage 목표

family 수가 적은 초기 canonical 단계에서도 coverage를 의식해야 한다.

초기 목표:

- aggregate-heavy family 1개 이하
- statement 또는 classification family 1개 이상
- target cell / row label family 1개 이상
- mini-table choice family 1개 이상

## 7. validation 질문

- 이 episode의 primary operator가 무엇인지 한 줄로 말할 수 있는가?
- support operator가 primary를 돕는지, 그냥 복잡도만 늘리는지 구분되는가?
- answer form이 operator와 자연스럽게 맞는가?
- aggregate 없이도 benchmark가 충분히 굴러가는가?
