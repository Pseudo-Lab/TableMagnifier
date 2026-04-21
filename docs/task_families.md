# Task Families

현재 benchmark는 `canonical_real_tableqa` track 아래 세 active family와 frozen public pack을 중심으로 운영한다.

## Active Families

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

## `eval_hard`

`eval_hard`는 active family 안에서만 만든다.

- Level 2 `eval_hard_dev`
- Level 3 `eval_hard_holdout`

핵심 규칙:

- family topology에 맞는 decisive surface를 모두 보지 않으면 required evidence를 충족할 수 없다
- base / counterfactual pair는 레이아웃을 유지한 채 decisive cue만 바꿔 정답을 뒤집는다
- replay와 eval artifact에는 `required_actions`, `required_evidence`, `shortcut_probes`를 남긴다

## Design Intent

좋은 episode는 아래를 만족해야 한다.

- 표가 중심 evidence다
- scope를 잘못 읽으면 바로 틀린다
- note는 장식이 아니라 실제 규칙 확정 근거다
- 한 줄 텍스트만 긁어서는 못 푼다
- sheet/page 이동은 실제 reasoning 필요를 반영한다

## Public Pack Note

현재 기본 노출 경로는 `public_smoke_real_v1`, `public_dev_real_v1` frozen pack이다. family generator는 authoring/dev source-of-truth이고, 실제 benchmark-facing 실행과 release gate는 frozen instance pack 기준으로 본다.
