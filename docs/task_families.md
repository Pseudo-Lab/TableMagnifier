# Task Families

현재 benchmark는 `korean_visual_table_agent_reasoning` track 아래 `k_vis_table_arc` generator family만 canonical registry에 등록한다.

## Active Family

- `k_vis_table_arc`

`k_vis_table_arc`는 `/api/catalog`에서 `family_status == preferred`, `is_preferred == true`로 노출된다.
이전 `marker_position_rule_transfer`, `excel_viewport_sheet_navigation` 데이터 family는 canonical registry에서 제거했고 기본 UI/API catalog에 노출하지 않는다.

## `k_vis_table_arc`

핵심 정의:

- 한국어로 작성된 시각적 테이블/문서 환경에서 에이전트가 제한된 관찰과 행동으로 탐색한다.
- 정적 `{table, question, answer}` 샘플이 아니라 sheet/page/action budget/replay를 갖는 episode를 평가 단위로 삼는다.
- 에이전트는 원본 CSV나 구조화 grid dump를 받지 않고 rendered viewport, 질문, 상태, action feedback만 사용한다.
- 최종 답뿐 아니라 evidence coverage, navigation efficiency, robustness, calibration을 평가 축으로 둔다.

현재 template:

- `symbol_rule_induction`: 완성 행에서 특수 기호 규칙을 유도하고 미완성 행에 적용한다.
- `merged_header_scope`: 병합 헤더와 계층 scope를 따라가며 범위 계산을 수행한다.
- `abbrev_doc_reference`: 합성 약어와 단위를 별도 문서에서 확인한 뒤 계산한다.
- `wide_table_navigation`: 50+ 열 환경을 탐색해 유사 열명을 구분하고 단위 변환 계산을 한다.
- `color_condition_rule_induction`: 완성 예시에서 색상/패턴/테두리 조건 규칙을 유도하고 질의 표에 적용한다.
- `legend_color_exception_scope`: 범례의 색상/패턴 의미와 질의 표의 예외 테두리를 함께 반영해 대상을 분류한다.
- `wide_table_viewport_trace`: 예시에서 학습한 열 오프셋을 넓은 질의 표에 적용하려면 pan/zoom과 위치 기억이 필요하다.
- `merged_header_pan_scope`: 병합 헤더가 정한 원거리 열 범위를 기억한 채 넓은 표를 이동해 값을 비교한다.
- `zoom_micro_marker_exception`: 작은 코너 마커의 위치가 예외 적용 범위를 바꾸므로 확대 관찰 후 계산한다.

답 형식:

- `number`와 `count`를 사용한다.
- 금액/수량 답은 canonical numeric string과 accepted alias를 함께 둔다.
- 질의 페이지의 선택지 ID도 accepted alias로 등록될 수 있다.

## Level Progression

- Level 1: 작은 표와 단일 규칙, 2-3 reasoning steps.
- Level 2: 추가 cue 또는 support document를 요구하며 3-4 reasoning steps.
- Level 3: 예외/보조 페이지가 wrong rule을 제거하며 4-5 reasoning steps.

## Splits And OOD Axes

현재 코드의 generated split/suite 축:

- `dev_public`: 디버깅과 예시 공개.
- `test_holdout`: manifest index 기준 holdout template/seed slot.
- `canonical_dev`: `dev_public` records를 노출하는 현재 기본 generated suite.

각 template manifest에는 `holdout_group`, `generalization_group`, `shortcut_probes`, `required_evidence`, `required_navigation` metadata가 들어간다. OOD 축은 이 metadata를 기준으로 확장한다.

## Instance Pack Note

현재 repo는 frozen `public_*` instance pack을 포함하지 않는다. family generator가 authoring/dev source-of-truth이고, workbench의 기본 노출 경로도 generator catalog다.
