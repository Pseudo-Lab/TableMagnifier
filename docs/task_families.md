# Task Families

현재 benchmark는 `canonical_real_tableqa` track 아래 두 generator family만 canonical registry에 등록한다.

## Active Families

### 우선 family

- `marker_position_rule_transfer`

### Active canonical/dev families

- `excel_viewport_sheet_navigation`

`marker_position_rule_transfer`는 `/api/catalog`에서 `family_status == preferred`, `is_preferred == true`로 노출된다.
`excel_viewport_sheet_navigation`은 `family_status == active`, `is_preferred == false`로 노출된다.

deprecated generator family는 canonical registry에서 제거했다. UI/API 기본 catalog와 generated benchmark suite에는 deprecated record가 노출되지 않는다.

## `marker_position_rule_transfer`

핵심 문제 구조:

- `예시` 시트에서 worked example를 읽는다.
- `범례` 시트에서 같은 삼각 표식이라도 셀 내부 모서리 위치가 다른 의미를 갖는다는 mapping을 확인한다.
- `반례` 시트에서 marker shape만 따라가는 wrong hypothesis를 제거한다.
- Level 3에서는 `반례` 시트의 openable note가 적용 묶음을 고정한다.
- `질의` 시트에서 현재 표에 대해 맞는 statement choice를 고른다.

현재 템플릿:

- `corner_anchor_statement`

답 형식:

- `statement_choice`

## `excel_viewport_sheet_navigation`

핵심 문제 구조:

- `사례` 시트에서 넓은 worksheet의 기준 열과 target 열 관계를 읽는다.
- Level 2에서는 `사례` 시트의 두 번째 페이지까지 확인한다.
- Level 3에서는 `연산자` 시트에서 같은 행 라벨과 target 열 이동 규칙을 확인한다.
- `질의` 시트에서 초기 viewport 오른쪽의 target 열까지 zoom/pan으로 이동한 뒤 최종 값을 선택한다.
- `required_navigation.required_viewport_states`가 `zoom_in`, `pan_right`, target rect center-in-viewbox 조건을 요구한다.

현재 템플릿:

- `wide_sheet_rule_transfer`

답 형식:

- `statement_choice`

## Level Progression

### `marker_position_rule_transfer`

- Level 1: `예시 + 범례 + 반례 + 질의`, 두 anchor mapping과 짧은 contrast로 위치 규칙을 전이
- Level 2: `예시 p1 + 예시 p2 + 범례 + 반례 + 질의`, 네 모서리 anchor와 row group variation을 함께 사용
- Level 3: `예시 p1 + 예시 p2 + 범례 + 반례 표 + 반례 note + 질의`, note는 적용 묶음을 고정

### `excel_viewport_sheet_navigation`

- Level 1: `사례 + 질의`, 사례의 target 열 이동 규칙을 질의 시트의 오른쪽 target column에 적용
- Level 2: `사례 p1 + 사례 p2 + 질의`, 두 번째 사례 페이지로 열 이동 규칙의 반복성을 확인
- Level 3: `사례 p1 + 사례 p2 + 연산자 + 질의`, 연산자 시트가 같은 행 라벨과 target 열 이동 규칙을 고정

## Instance Pack Note

현재 repo는 frozen `public_*` instance pack을 포함하지 않는다. family generator가 authoring/dev source-of-truth이고, workbench의 기본 노출 경로도 generator catalog다.
