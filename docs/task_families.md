# Task Families

현재 benchmark는 `canonical_real_tableqa` track 아래 `marker_position_rule_transfer`를 우선 generator family로 운영한다.
`excel_viewport_sheet_navigation`은 pan/zoom/sheet navigation admission gate를 검증하는 active canonical/dev family로 유지하되, v1에서는 preferred family나 frozen public pack 후보로 승격하지 않는다.
기존 세 generator family는 회귀/비교용 deprecated family로 유지하며, frozen public pack은 아직 기존 frozen instance 기반으로 유지한다.

## Active Families

### 우선 family

- `marker_position_rule_transfer`

### Deprecated generator families

아래 family들은 삭제하지 않고 회귀 테스트, 비교 baseline, frozen public pack 호환을 위해 유지한다.

- `channel_policy_transfer`
- `inventory_exception_disambiguation`
- `report_scope_reconciliation`

### Active canonical/dev families

아래 family는 canonical registry에 등록되어 테스트와 authoring gate에서 검증하지만, 아직 preferred나 public-pack release family로 보지 않는다.

- `excel_viewport_sheet_navigation`

### `channel_policy_transfer`

핵심 문제 구조:

- `사례` 시트에서 worked example를 읽는다.
- active band, icon anchor, row group band를 함께 해석한다.
- Level 3에서는 `부록` 시트의 note가 anchor 해석을 최종 고정한다.
- `확인` 시트에서 정답 choice를 고른다.

대표 visual evidence:

- `기본 / 검토` band
- `top_right / bottom_left` triangle anchor
- row group band와 indented row label
- note marker

대표 reasoning:

- example-to-current transfer
- active band scope resolution
- group boundary selection
- note-grounded anchor disambiguation

현재 템플릿:

- `icon_scope_cell`

답 형식:

- `cell_choice`

### `inventory_exception_disambiguation`

핵심 문제 구조:

- `예시` 시트의 ambiguous example pair만 보면 pattern rule과 icon rule이 모두 살아 있다.
- `반례` 시트가 wrong hypothesis를 무너뜨린다.
- Level 2와 Level 3에서는 `반례` 시트의 note가 active group scope까지 고정한다.
- `선택` 시트에서 현재 표와 맞는 선택 미리보기를 고른다.

대표 visual evidence:

- diagonal stripe pattern
- triangle marker
- grouped row band
- note marker

대표 reasoning:

- hypothesis revision
- exception-based disambiguation
- active group scope confirmation
- statement / preview choice verification

현재 템플릿:

- `pattern_vs_icon_statement`

답 형식:

- `statement_choice`

구현 상태:

- canonical generator family로 등록됨
- template id: `corner_anchor_statement`
- levels: 1, 2, 3
- canonical seed capacity: level별 8
- frozen public packs에는 포함하지 않음
- base answer label은 seed별 B/C/D로 회전
- counterfactual helper는 decisive marker-position rule을 뒤집고 answer label을 바꿈
- authoring gate는 topology, L3 note opening, shortcut probes, static answer-label guard를 확인함

최신 검증:

- `uv run pytest -q` -> `69 passed`
- `cd frontend && npm run lint` -> pass
- marker 전용 Playwright surface readability -> `16 passed`
- authoring `viewport_readability` run `11130efe95ae478e8e6ffa9f4a164a13` -> passed
- final architect verification -> `PASS`

### `report_scope_reconciliation`

핵심 문제 구조:

- `개요` 시트의 dense grouped table을 읽는다.
- merged header, repeated team label, indentation, subtotal block을 함께 해석한다.
- 필요하면 `메모` 시트에서 범위 규칙을 확인한다.
- `질의` 시트에서 정답 choice를 고른다.

대표 visual evidence:

- `3개 지역 × 3개 팀` 구조
- 반복되는 `1팀 / 2팀 / 3팀` 라벨
- `상반기 / 하반기` 아래 `구간 / 매출 / 마진` 열
- 지역 소계와 전체 총계
- 들여쓰기와 grouped row band

대표 reasoning:

- merged header scope resolution
- repeated label disambiguation
- subtotal / grand total boundary parsing
- note-grounded scope confirmation

현재 템플릿:

- `merged_scope_cell`
- `grouped_statement`
- `subtotal_row_label`

답 형식:

- `cell_choice`
- `statement_choice`
- `row_label_choice`

### `marker_position_rule_transfer`

핵심 문제 구조:

- `예시` 시트에서 worked example를 읽는다.
- `범례` 시트에서 같은 삼각 표식이라도 셀 내부 모서리 위치가 다른 의미를 갖는다는 mapping을 확인한다.
- `반례` 시트에서 marker shape만 따라가는 wrong hypothesis를 제거한다.
- Level 3에서는 `반례` 시트의 openable note가 적용 묶음을 고정하고, anchor 의미는 예시/범례/반례 표를 조합해 판정한다.
- `질의` 시트에서 현재 표에 대해 맞는 statement choice를 고른다.
- 정답 choice label은 seed별로 B/C/D 사이에서 회전해 label shortcut을 만들지 않는다.

대표 visual evidence:

- `top_left / top_right / bottom_left / bottom_right` triangle anchor
- legend item과 table cell marker의 위치 대응
- 반례 표의 같은 모양/다른 위치 contrast
- Level 3 note marker

대표 reasoning:

- marker-position rule induction
- legend-to-table mapping
- exception-based disambiguation
- query table transfer

현재 템플릿:

- `corner_anchor_statement`

답 형식:

- `statement_choice`

### `excel_viewport_sheet_navigation`

핵심 문제 구조:

- `사례` 시트에서 넓은 worksheet의 기준 열과 target 열 관계를 읽는다.
- Level 2에서는 `사례` 시트의 두 번째 페이지까지 확인해 같은 열 이동 규칙이 반복되는지 본다.
- Level 3에서는 `연산자` 시트에서 같은 행 라벨과 target 열 이동 규칙을 확인한다.
- `질의` 시트에서 초기 viewport 오른쪽의 target 열까지 zoom/pan으로 이동한 뒤 최종 값을 선택한다.
- `required_navigation.required_viewport_states`가 `zoom_in`, `pan_right`, target rect center-in-viewbox 조건을 요구한다.

대표 visual evidence:

- 넓은 table의 초기 viewport 밖 target column
- 같은 행 라벨 alignment
- column offset from check/reference columns to target column
- sheet/page traversal state
- zoom/pan 후 target cell visibility

대표 reasoning:

- worked example-to-query transfer
- column-offset matching
- viewport navigation compliance
- sheet/page scope resolution

현재 템플릿:

- `wide_sheet_rule_transfer`

답 형식:

- `statement_choice`

운영 상태:

- canonical generator family로 등록됨
- levels: 1, 2, 3
- canonical seed capacity: level별 8
- `family_status == active`
- `is_preferred == false`
- frozen public packs에는 포함하지 않음
- `eval_hard`에는 아직 포함하지 않음

## Level Progression

### `channel_policy_transfer`

- Level 1: `예시 + 질의`, active band와 icon anchor를 직접 전이
- Level 2: `예시 p1 + 예시 p2 + 질의`, row group band까지 함께 사용
- Level 3: `예시 p1 + 예시 p2 + 부록 + 질의`, appendix note 없이는 anchor 해석이 고정되지 않음

### `inventory_exception_disambiguation`

- Level 1: `예시 + 반례 + 선택`, 예외 사례 1개로 wrong rule을 제거
- Level 2: `예시 + 반례 표 + 반례 note + 질의`, active group scope를 note가 추가로 고정
- Level 3: `예시 + 반례 표 + 반례 note + 질의`, query는 결과 column이 없는 다른 surface format으로 바뀜

### `report_scope_reconciliation`

- Level 1: dense grouped table만으로 범위를 읽게 한다
- Level 2: `메모` 시트와 `소계 / 총계`를 함께 사용한다
- Level 3: 같은 라벨과 metric이 더 많이 반복되고 wrong scope distractor를 강하게 섞는다

### `marker_position_rule_transfer`

- Level 1: `예시 + 범례 + 반례 + 질의`, 두 anchor mapping과 짧은 contrast로 3단계 안에 위치 규칙을 전이
- Level 2: `예시 p1 + 예시 p2 + 범례 + 반례 + 질의`, 네 모서리 anchor와 row group variation을 함께 사용
- Level 3: `예시 p1 + 예시 p2 + 범례 + 반례 표 + 반례 note + 질의`, note는 적용 묶음을 고정하고 anchor 의미는 예시/범례/반례 표 조합으로 판정

### `excel_viewport_sheet_navigation`

- Level 1: `사례 + 질의`, 사례의 target 열 이동 규칙을 질의 시트의 오른쪽 target column에 적용
- Level 2: `사례 p1 + 사례 p2 + 질의`, 두 번째 사례 페이지로 열 이동 규칙의 반복성을 확인
- Level 3: `사례 p1 + 사례 p2 + 연산자 + 질의`, 연산자 시트가 같은 행 라벨과 target 열 이동 규칙을 고정

## `eval_hard`

`eval_hard`는 canonical family에 자동으로 붙지 않는다. 현재 hard pair는 기존 비교/회귀 목적의 일부 family에만 유지하며, `excel_viewport_sheet_navigation`은 stabilization 이후 별도 PRD에서 hard pair 후보로 검토한다.

- Level 2 `eval_hard_dev`
- Level 3 `eval_hard_holdout`

핵심 규칙:

- family topology에 맞는 decisive surface를 모두 보지 않으면 required evidence를 충족할 수 없다
- base / counterfactual pair는 레이아웃을 유지한 채 decisive cue만 바꿔 정답을 뒤집는다
- replay와 eval artifact에는 `required_actions`, `required_evidence`, `shortcut_probes`를 남긴다
- viewport-navigation hard pair를 추가할 때는 `required_navigation.required_viewport_states`와 replay/workbench visited-state gate를 acceptance criteria에 포함한다

## Design Intent

좋은 episode는 아래를 만족해야 한다.

- 표가 중심 evidence다
- scope를 잘못 읽으면 바로 틀린다
- note는 장식이 아니라 실제 규칙 확정 근거다
- 한 줄 텍스트만 긁어서는 못 푼다
- sheet/page 이동은 실제 reasoning 필요를 반영한다

## Public Pack Note

현재 기본 노출 경로는 `public_smoke_real_v1`, `public_dev_real_v1` frozen pack이다. family generator는 authoring/dev source-of-truth이고, 실제 benchmark-facing 실행과 release gate는 frozen instance pack 기준으로 본다.

`excel_viewport_sheet_navigation`은 frozen public pack에 포함하지 않는다. public pack 승격은 별도 release PRD에서 full-seed readability, shortcut red-team, replay navigation compliance, public instance freeze diff를 함께 검토한 뒤 결정한다.
