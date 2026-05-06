# Pilot Episode Drafts

상태: historical design archive

이 문서는 초기 pilot draft를 보존한다. 현재 active benchmark-facing source-of-truth는 canonical family generator이며, 이 문서는 설계 배경을 참고할 때만 사용한다.

이 문서는 새 canonical family를 실제 구현으로 옮기기 전에 사용할 `pilot episode 초안`을 정리한다.

이번 버전의 목적은 특히 다음 세 가지를 반영하는 것이다.

- text-only로는 풀 수 없는 `non-text visual cue`를 핵심에 둔다
- subset aggregation에 치우치지 않고 서로 다른 operator와 answer form을 쓴다
- Level 1은 `2-3 reasoning steps` 안에서 규칙을 배울 수 있도록 낮춘다

이 문서에는 초기 pilot family 2개에 대해 각 1개씩 초안을 둔다.

- `channel_policy_transfer`
- `inventory_exception_disambiguation`

## Draft 1. `channel_policy_transfer_l1_icon_anchor_pick_v1`

### 기본 정보

- family: `channel_policy_transfer`
- target level: 1
- primary operator: `select_scope`
- support operator: 없음
- answer format: `target cell choice`
- canonical answer: `D`

### 이 draft가 보려는 것

이 문제는 `활성 merged header band`를 읽고, 그 band 안에서 `우상단에 붙은 작은 삼각 아이콘`이 있는 셀을 선택하는 규칙을 배워 query에 전이하는 능력을 본다.

핵심은 아래 두 단계다.

1. chip과 merged header를 보고 어느 band가 현재 scope인지 읽는다
2. 그 band 안에서 `아이콘 위치`가 맞는 셀을 찾는다

숫자 계산은 없다. 텍스트만 읽어서는 아이콘 위치 차이를 구분할 수 없기 때문에 visual cue가 필수다.

### latent mechanic

- 상단 chip이 현재 활성 header band를 지정한다
- 정답은 활성 band 안에서 `우상단 삼각 아이콘`이 붙은 셀이다
- 같은 아이콘이라도 좌하단에 붙은 경우는 정답이 아니다

### workbook topology

- Sheet `examples`
  - Page 1: example 1, example 2
- Sheet `query`
  - Page 1: query table + answer choice panel

### question

`예시 표와 같은 규칙을 적용했을 때 선택해야 하는 셀은 무엇인가?`

### visible surfaces

- `example_table_panel` x 2
- `query_table_panel` x 1
- `answer_choice_panel` x 1
- `merged_header_block`
- `filter_chip`
- `marker_chip`
- `selection_frame`

### example 1

```text
상단 chip: 대상 구역 = 검토
헤더 밴드: [기본] spans (상태, 조치) / [검토] spans (상태, 조치)

| 행 이름 | 기본 상태 | 기본 조치 | 검토 상태 | 검토 조치 |
| A행     | 좌하단 삼각 | 없음     | 없음      | 우상단 삼각 |
| B행     | 없음        | 없음     | 좌하단 삼각 | 없음      |
| C행     | 우상단 삼각 | 없음     | 없음      | 없음      |
```

output panel에서는 `A행 / 검토 조치` 셀이 강조된다.

### example 2

```text
상단 chip: 대상 구역 = 기본
헤더 밴드: [기본] spans (상태, 조치) / [검토] spans (상태, 조치)

| 행 이름 | 기본 상태 | 기본 조치 | 검토 상태 | 검토 조치 |
| A행     | 없음      | 없음      | 우상단 삼각 | 없음      |
| B행     | 좌하단 삼각 | 없음     | 없음      | 없음      |
| C행     | 없음      | 우상단 삼각 | 없음    | 좌하단 삼각 |
```

output panel에서는 `C행 / 기본 조치` 셀이 강조된다.

이 두 example만으로도 다음 규칙을 배울 수 있다.

- 현재 활성 band를 먼저 읽는다
- 그 band 안에서 우상단 삼각 아이콘이 붙은 셀을 선택한다
- 좌하단 삼각은 distractor다

### query

```text
상단 chip: 대상 구역 = 검토
헤더 밴드: [기본] spans (상태, 조치) / [검토] spans (상태, 조치)

| 행 이름 | 기본 상태 | 기본 조치 | 검토 상태 | 검토 조치 |
| A행     | 우상단 삼각 | 없음    | 없음      | 없음      |
| B행     | 없음      | 좌하단 삼각 | 없음   | 없음      |
| C행     | 없음      | 없음      | 좌하단 삼각 | 없음    |
| D행     | 없음      | 없음      | 없음      | 우상단 삼각 |
```

### answer choices

- A: `A행 / 기본 상태` 셀 강조
- B: `B행 / 기본 조치` 셀 강조
- C: `C행 / 검토 상태` 셀 강조
- D: `D행 / 검토 조치` 셀 강조

### 왜 이 draft가 유효한가

- table/worksheet surface가 중심이다
- merged header와 icon anchor position 둘 다 실제로 읽어야 한다
- 숫자나 subset 합산 없이도 rule transfer를 측정한다
- Level 1 기준으로 2-3 step 안에 설명 가능하다

### 주요 실패 모드

- 활성 band를 무시하고 전체 표에서 우상단 아이콘만 찾음
- 아이콘 위치를 무시하고 같은 모양이면 모두 같다고 처리
- 활성 band는 맞게 읽었지만 같은 row의 다른 cell을 고름

### level 확장 방향

- Level 2
  - icon 종류는 같고 위치만 다른 distractor를 더 많이 둠
  - band 수를 3개로 늘리거나 row 수를 늘림
- Level 3
  - 약한 note cue 또는 second example page 추가
  - icon anchor + indentation hierarchy를 함께 사용

## Draft 2. `inventory_exception_disambiguation_l1_pattern_vs_icon_statement_v1`

### 기본 정보

- family: `inventory_exception_disambiguation`
- target level: 1
- primary operator: `verify_statement`
- support operator: `disambiguate_by_exception`
- answer format: `statement choice`
- canonical answer: `B`

### 이 draft가 보려는 것

이 문제는 처음 examples만 보면 `사선 줄무늬가 있는 row`가 선택 대상처럼 보이게 만든 뒤, 예외 사례에서 실제 기준이 `우상단 깃발 아이콘`이라는 점을 확정하게 한다.

핵심은 아래 세 단계다.

1. examples에서 plausible rule 두 개를 세운다
2. 예외 사례로 `줄무늬 rule`을 제거한다
3. query에 대해 올바른 진술을 고른다

여기서 핵심 visual cue는 `conditional-format pattern`과 `icon anchor position`이다.

### latent mechanic

- 선택 대상 row는 줄무늬 fill이 아니라 `우상단 깃발 아이콘`이 있는 row다
- 배경 패턴은 초반 examples에서는 우연히 같지만, 예외 사례에서 diverge한다
- query의 정답은 "어느 row가 선택 대상인가"를 설명하는 statement choice다

### workbook topology

- Sheet `examples`
  - Page 1: ambiguous example 1, ambiguous example 2
- Sheet `exception`
  - Page 1: exception card
- Sheet `query`
  - Page 1: query table + answer choice panel

### question

`반례까지 반영했을 때 query 표에 대해 올바른 설명은 무엇인가?`

### visible surfaces

- `example_table_panel` x 2
- `exception_card` x 1
- `query_table_panel` x 1
- `answer_choice_panel` x 1
- `marker_chip`
- `selection_frame`

### ambiguous example 1

```text
줄무늬 row = A행, C행
우상단 깃발 row = A행, C행

| 행 이름 | 상태 |
| A행     | 줄무늬 + 우상단 깃발 |
| B행     | 없음                 |
| C행     | 줄무늬 + 우상단 깃발 |
| D행     | 없음                 |
```

output panel에서는 `A행, C행이 선택 대상`인 mini summary가 보인다.

### ambiguous example 2

```text
줄무늬 row = B행, D행
우상단 깃발 row = B행, D행

| 행 이름 | 상태 |
| A행     | 없음                 |
| B행     | 줄무늬 + 우상단 깃발 |
| C행     | 없음                 |
| D행     | 줄무늬 + 우상단 깃발 |
```

output panel에서는 `B행, D행이 선택 대상`인 mini summary가 보인다.

### exception surface

```text
줄무늬 row = A행, C행
우상단 깃발 row = B행, C행

| 행 이름 | 상태 |
| A행     | 줄무늬               |
| B행     | 우상단 깃발          |
| C행     | 줄무늬 + 우상단 깃발 |
| D행     | 없음                 |
```

output panel에서는 `B행, C행이 선택 대상`인 mini summary가 보인다.

이 반례가 의미하는 것은 명확하다.

- 줄무늬 rule이면 A행과 C행이 선택되어야 한다
- 실제 output은 B행과 C행이므로, 줄무늬만으로는 설명할 수 없다
- 따라서 true rule은 `우상단 깃발 row 선택`이다

### query

```text
줄무늬 row = A행, D행
우상단 깃발 row = B행, D행

| 행 이름 | 상태 |
| A행     | 줄무늬               |
| B행     | 우상단 깃발          |
| C행     | 없음                 |
| D행     | 줄무늬 + 우상단 깃발 |
```

### answer choices

- A: `줄무늬 row인 A행과 D행이 선택 대상이다`
- B: `우상단 깃발이 있는 B행과 D행이 선택 대상이다`
- C: `줄무늬와 아이콘이 모두 있는 D행만 선택 대상이다`
- D: `줄무늬와 아이콘이 함께 있는 row만 선택 대상이다`

### 왜 이 draft가 유효한가

- table이 중심 evidence다
- pattern과 icon이라는 비텍스트 cue를 실제로 구분해야 한다
- output이 statement choice라 subset 합산 반복에서 벗어난다
- 예외 사례가 실제 wrong rule을 제거한다
- Level 1 기준으로 3 step 정도로 설명 가능하다
- 텍스트 컬럼 없이도 문제가 완결되므로 text-only shortcut이 더 어렵다

### 주요 실패 모드

- 줄무늬 cue만 보고 pattern rule을 고수
- 아이콘 위치가 아니라 아이콘 존재 여부만 대충 읽음
- 줄무늬와 아이콘의 결합 규칙을 잘못 이해해 `D행만 정답` 같은 과도한 축소 규칙을 세움

### level 확장 방향

- Level 2
  - 아이콘 위치 두 종류를 추가해 `존재`가 아니라 `위치`까지 보게 함
  - answer form을 mini-table choice로 바꿔 한 단계 더 우회
- Level 3
  - note attachment나 second exception page 추가
  - pattern + icon + group boundary를 함께 써서 stronger disambiguation 구성

## Deprecated note

이전 draft 버전은 두 family 모두 subset aggregation / subtotal 선택 쪽으로 수렴해 operator 폭이 좁았다. 현재 버전은 다음 방향으로 고쳤다.

- Draft 1: `target cell choice`
- Draft 2: `statement choice`
- 두 draft 모두 non-text visual cue가 핵심
- Level 1 reasoning depth를 2-3 step 수준으로 낮춤

## 다음 구현 추천 순서

1. `channel_policy_transfer_l1_icon_anchor_pick_v1`
2. `inventory_exception_disambiguation_l1_pattern_vs_icon_statement_v1`
3. 이후 Level 2에서 cue 수와 answer indirection을 늘린 버전 추가

## 문서 연결

- [docs/family_design_brief.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/family_design_brief.md)
- [docs/pilot_family_episode_grammar.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/pilot_family_episode_grammar.md)
- [docs/primitive_glossary.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/primitive_glossary.md)
- [docs/episode_rulebook.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/episode_rulebook.md)
- [docs/visual_cue_inventory.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/visual_cue_inventory.md)
- [docs/operator_taxonomy.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/operator_taxonomy.md)
- [docs/answer_form_policy.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/answer_form_policy.md)
- [docs/level_design_policy.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/level_design_policy.md)
- [docs/episode_validation_checklist.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/episode_validation_checklist.md)
- [docs/generator_episode_schema.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/generator_episode_schema.md)
- [docs/pilot_implementation_strategy.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/pilot_implementation_strategy.md)
- [docs/document_status.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/document_status.md)
- [PLANS.md](/mnt/c/Users/imssh/Documents/TableMagnifier/PLANS.md)
