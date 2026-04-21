# Difficulty Ramp v1

이번 버전의 난이도 상향은 `report_scope_reconciliation` 한 family 안에서만 진행한다.

## 핵심 원칙

- family 수를 늘리지 않는다
- 한 표 안의 density와 scope ambiguity를 올린다
- Level이 올라가도 모든 축을 한 번에 올리지 않는다
- `eval_hard`는 required evidence를 명시적으로 강제한다

## Base Table Profile

기본 표 구조는 아래를 따른다.

- `3개 지역`
- `지역당 3개 팀`
- `상반기 / 하반기`
- 각 반기 아래 `구간 / 매출 / 마진`
- 지역 소계
- 전체 총계

이 구조의 목적은 repeated label과 subtotal boundary를 한 표 안에서 계속 충돌시키는 것이다.

## Level 1

- dense grouped table만으로 풀게 한다
- notes sheet는 없다
- merged header와 repeated team label을 기본 범위 해석 cue로 쓴다
- reasoning target: 2-3 step

대표 실패:

- 같은 `1팀`을 다른 지역에서 고른다
- `상반기/하반기` scope를 놓친다

## Level 2

- `메모` 시트를 추가한다
- 지역 소계와 전체 총계를 함께 둔다
- repeated label distractor를 강화한다
- reasoning target: 3-4 step

대표 실패:

- subtotal row를 data row로 읽는다
- note를 안 보고 잘못된 범위를 확정한다

## Level 3

- repeated metric과 repeated label을 더 강하게 겹친다
- total/subtotal distractor를 더 공격적으로 섞는다
- answer indirection 또는 stronger statement disambiguation을 넣는다
- reasoning target: 4-5 step

대표 실패:

- 총계와 지역 소계를 혼동한다
- 같은 label/metric 조합을 다른 block에서 가져온다

## `eval_hard`

`eval_hard`는 같은 family의 Level 2/3 위에 base/counterfactual pair를 얹는다.

- `eval_hard_dev`: Level 2 pair
- `eval_hard_holdout`: Level 3 pair

필수 메타데이터:

- `required_sheet_ids`
- `required_page_refs`
- `required_actions`
- `required_evidence`
- `shortcut_probes`
- `pair_group`
- `variant`

운영 원칙:

- `개요 + 메모 + 질의`를 모두 봐야 한다
- note open 없이 제출하면 premature submit으로 잡힌다
- base와 counterfactual은 layout을 유지하고 decisive cue만 바꾼다
