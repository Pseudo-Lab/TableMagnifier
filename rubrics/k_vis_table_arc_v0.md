# K-VisTable-ARC v0 Rubric

`k_vis_table_arc`는 한국어 시각 테이블 workbook 환경에서 에이전트가 제한된 관찰과 행동으로 필요한 sheet/page를 탐색하고, 표 구조와 보조 문서를 근거로 규칙을 유도한 뒤 계산 결과를 제출하는지를 평가한다.

## 데이터 단위

평가 단위는 `{table, question, answer}`가 아니라 episode다.

- workbook title, sheet tabs, page sequence를 갖는다.
- rendered viewport가 기본 evidence surface다.
- agent는 sheet 이동, page 이동, click, final answer 제출 같은 제한된 action을 수행한다.
- episode metadata에는 required navigation, required evidence, shortcut probes, hidden program, seed를 기록한다.
- hidden program과 oracle evidence는 평가/검증용이며 default observation에 노출하지 않는다.

## 현재 v0 Template

| Template | 평가하고 싶은 능력 | 주요 surface | 대표 shortcut |
| --- | --- | --- | --- |
| `symbol_rule_induction` | 완성 행에서 특수 기호 규칙을 유도하고 query 행에 전이 | examples sheet, query sheet, L3 exception page | 기호를 고정 의미로 외우기, 예외 page skip |
| `merged_header_scope` | 병합 헤더와 계층 scope를 상속해 올바른 범위 비교 | merged table, unit note, query sheet | 인접 열 선택, `%`와 `%p` 혼동 |
| `abbrev_doc_reference` | 합성 약어와 단위를 별도 glossary에서 확인 | main table, glossary sheet, query sheet | 실제 세계 약어 지식 사용, glossary skip |
| `wide_table_navigation` | 50+ 열 환경에서 유사 열명과 행 조건을 탐색 | directory sheet, wide table, query sheet | 유사 열 선택, 천 원/원 단위 변환 skip |

## Level 의도

| Level | 의도 | 권장 reasoning steps |
| --- | --- | ---: |
| L1 | 작은 표, 단일 cue, 기본 계산 | 2-3 |
| L2 | cue 조합 또는 support sheet 의존성 추가 | 3-4 |
| L3 | 예외/보조 page가 wrong rule을 제거 | 4-5 |

난이도를 올릴 때는 perceptual load, scope nesting, operator complexity, answer indirection, navigation burden 중 1-2개만 올린다. 모든 축을 동시에 키우면 실패 원인을 해석하기 어렵다.

## 평가 항목

### 1. AnswerAccuracy

- 숫자 금액은 원 단위 exact match를 기본으로 한다.
- `1,845,000`, `1845000원`처럼 표기만 다른 값은 normalizer로 허용할 수 있다.
- `%p`, `%`, 천 원, 만 원, 억 원 같은 단위 변환은 문제 문구와 support surface에 명시되어야 한다.

### 2. EvidenceAccuracy

정답이 맞아도 아래 근거를 거치지 않으면 불완전한 solve로 본다.

- 필요한 sheet/page 방문 여부
- target cell 또는 relevant row/column/header 확인 여부
- glossary, note, exception page 참조 여부
- 유도한 rule 또는 scope 해석이 gold evidence와 맞는지

현재 metadata는 최소한 `required_sheet_ids`, `required_page_refs`, `required_navigation`, `required_evidence`를 포함해야 한다.

### 3. EfficiencyScore

정답을 맞히는 것뿐 아니라 탐색 효율도 본다.

- `Human-normalized Efficiency = min(1, median_human_steps / agent_steps)`를 기본 후보로 둔다.
- 같은 page를 반복 방문하거나 모든 answer choice를 무작정 클릭하는 행동은 감점 대상이다.
- wide table template은 정확한 column narrowing을 했는지 action trace로 확인한다.

### 4. RobustnessScore

같은 logical rule을 visual variant로 바꿔도 풀 수 있어야 한다.

예정 variant:

- symbol 모양, 색, 위치 변경
- merged/unmerged/multi-line/rotated header 변경
- glossary 위치와 약어 체계 변경
- wide table column 수와 viewport 위치 변경

### 5. CalibrationScore

에이전트가 evidence가 부족한 상태에서 과신하지 않는지 본다.

- support page를 보지 않았는데 높은 확신으로 답하면 감점한다.
- answer는 맞았지만 evidence가 부족한 경우 calibration credit을 낮춘다.
- impossible/ambiguous split을 만들 경우 abstain 또는 uncertainty 표현을 별도 평가할 수 있다.

## Template별 Gold Evidence 기준

### `symbol_rule_induction`

필수 evidence:

- examples page의 완성 행 2개 이상
- query row의 marked values
- L3에서는 exception page

평가 의도:

- 기호 의미를 자연어 설명 없이 표 내부 일관성으로 유도한다.
- 같은 기호라도 OOD split에서는 모양/색/위치가 바뀔 수 있다.

### `merged_header_scope`

필수 evidence:

- 상위 merged header
- 하위 channel/region header
- 비교 대상 기간의 두 data cells
- `%p` 계산 note

평가 의도:

- 셀 값 lookup이 아니라 header path 상속을 검증한다.
- 인접 기간이나 인접 channel을 잘못 고르는 distractor를 둔다.

### `abbrev_doc_reference`

필수 evidence:

- main table의 target row/cells
- glossary의 합성 약어 정의
- unit note 또는 calculation caution

평가 의도:

- 모델의 사전 약어 지식이 아니라 episode 내부 문서 참조 능력을 본다.
- 약어 의미는 seed/template별로 바뀔 수 있어야 한다.

### `wide_table_navigation`

필수 evidence:

- directory 또는 column guide
- target row condition
- 유사 column 중 정확한 target columns
- unit conversion cue

평가 의도:

- 한 화면에 보이지 않는 테이블 탐색, 위치 기억, 비슷한 열명 구분을 본다.
- action log로 운 좋게 맞힌 답과 실제 탐색 solve를 구분한다.

## Data Acceptance Checklist

episode를 추가할 때 아래를 모두 만족해야 한다.

- 사람 풀이 기준으로 유일해가 있다.
- query-only solve가 불가능하다.
- visible surface에 필요한 근거가 모두 있다.
- default observation에 hidden grid text, hidden program, gold evidence가 직접 노출되지 않는다.
- distractor는 실제 shortcut failure를 반영한다.
- `uv run pytest tests/test_pilot_families.py`를 통과한다.
- 최소 smoke readability audit을 통과한다.
