# Level Design Policy

이 문서는 active canonical family들의 Level 1/2/3 기준을 정의한다.

## 공통 원칙

- Level은 표면 clutter가 아니라 reasoning depth로 구분한다
- 한 단계 올릴 때는 1-2개의 complexity axis만 올린다
- 낮은 Level부터 note, cross-sheet, answer indirection을 모두 요구하지 않는다

## Family 1. `report_scope_reconciliation`

### Level 1

- 권장: 2-3 step
- cue: merged header, repeated team label
- navigation: `개요 -> 질의`

### Level 2

- 권장: 3-4 step
- cue: Level 1 cue + `메모` + subtotal/total
- navigation: `개요 -> 메모 -> 질의`

### Level 3

- 권장: 4-5 step
- cue: Level 2 cue + stronger disambiguation pressure
- navigation: multi-surface evidence를 더 안정적으로 결합

## Family 2. `channel_policy_transfer`

### Level 1

- 권장: 2-3 step
- cue: active band + icon anchor
- navigation: `예시 -> 질의`

### Level 2

- 권장: 3-4 step
- cue: Level 1 cue + row group band
- navigation: `예시 p1 -> 예시 p2 -> 질의`

### Level 3

- 권장: 4-5 step
- cue: Level 2 cue + appendix note
- navigation: `예시 p1 -> 예시 p2 -> 부록 -> 질의`

## Family 3. `inventory_exception_disambiguation`

### Level 1

- 권장: 3-4 step
- cue: diagonal stripe + triangle marker
- navigation: `예시 -> 반례 -> 질의`

### Level 2

- 권장: 4-5 step
- cue: Level 1 cue + row group band + exception note
- navigation: `예시 -> 반례 표 -> 반례 note -> 질의`

### Level 3

- 권장: 4-5 step
- cue: Level 2 cue + query surface format change
- navigation: `예시 -> 반례 표 -> 반례 note -> 질의`

## Complexity Axes

### 1. Perceptual Load

- row 수
- repeated label 수
- summary block 수

### 2. Scope Nesting

- merged header depth
- row group depth
- subtotal / total boundary

### 3. Operator Complexity

- `scope_resolution`
- `classify`
- `verify_statement`
- `transfer`

### 4. Answer Indirection

- direct cell choice
- row label choice
- statement choice

### 5. Navigation Burden

- single support sheet 필요 여부
- note open 필요 여부
- 보강 예시 page 필요 여부

## Level별 권장 조합

### Level 1

- primary cue 1개
- support cue 0개
- note open은 기본적으로 없음

### Level 2

- primary cue 1개
- support cue 1개
- 보강 예시 또는 support page를 함께 사용

### Level 3

- support cue 1-2개
- distractor를 더 그럴듯하게 만든다
- wrong scope와 wrong cue 해석이 모두 살아 남지 않게 한다

## Misfit 신호

아래 중 하나면 레벨이 잘못 붙었을 가능성이 크다.

- Level 1인데 note open이 필수다
- Level 1인데 subtotal/appendix 없이는 못 푼다
- Level 2인데 support page 없이도 너무 쉽게 정답이 고정된다
- Level 3인데 Level 2보다 실제 reasoning depth가 거의 늘지 않는다
