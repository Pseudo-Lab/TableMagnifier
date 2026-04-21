# Pilot Family Episode Grammar

상태: historical design archive

이 문서는 초기 pilot 설계 문법을 보존한다. 현재 active benchmark는 `canonical_real_tableqa`와 real-data public pack 기준으로 운영되므로, 실제 family 추가와 validation은 [family_design_brief.md](family_design_brief.md), [episode_rulebook.md](episode_rulebook.md), [real_data_authoring_policy.md](real_data_authoring_policy.md)를 우선 본다.

## 목적

이 문서는 첫 두 개 pilot canonical family를 실제 episode spec 수준으로 설계할 때 따라야 하는 grammar를 정의한다.

대상 family:

- `channel_policy_transfer`
- `inventory_exception_disambiguation`

이 문서는 renderer 구현 세부보다 "어떤 episode가 valid한가"를 정하는 데 초점을 둔다.

## 공통 원칙

초기 pilot family 두 개 모두 아래 조건을 만족해야 한다.

- 정답은 compact answer format으로 채점 가능해야 한다
- workbook 구조가 reasoning topology를 반영해야 한다
- visually rendered table 또는 worksheet fragment가 핵심 evidence여야 한다
- chart, note, legend는 table evidence를 보조해야 한다
- seed가 바뀌어도 family identity가 유지되어야 한다
- hidden oracle 없이 사람이 화면만 보고 풀 수 있어야 한다

## 공통 episode spec 뼈대

권장 구조:

```json
{
  "episode_id": "channel_policy_transfer_l1_s0",
  "family": "channel_policy_transfer",
  "level": 1,
  "seed": 0,
  "question": "예시 표와 같은 규칙을 적용했을 때 맞는 결과는 무엇인가?",
  "answer": {"canonical": "B"},
  "workbook": {
    "sheets": [
      {"sheet_id": "examples", "pages": [...]},
      {"sheet_id": "query", "pages": [...]}
    ]
  }
}
```

실제 구현에서는 현재 데이터 모델에 맞게 번역하되, 의미 구조는 이 문서를 우선한다.

구체적인 sample episode 초안은 [docs/pilot_episode_drafts.md](pilot_episode_drafts.md)를 함께 본다.

## Family 1. `channel_policy_transfer`

### 핵심 질문

example table들에서 관찰한 동일한 규칙을 query table에 적용하면 어떤 결과가 되는가?

### canonical workbook topology

최소형:

- Sheet `examples`
  - Page 1: example 1, example 2
- Sheet `query`
  - Page 1: query table + answer choice panel

확장형:

- Sheet `examples`
  - Page 1: example 1, example 2
  - Page 2: example 3
- Sheet `query`
  - Page 1: query table + answer choice panel

### 필수 primitive 조합

- `example_table_panel` x 2 이상
- `query_table_panel` x 1
- `answer_choice_panel` x 1

선택 primitive:

- `merged_header_block`
- `row_group_band`
- `marker_chip`
- `filter_chip`
- `selection_frame`
- `note_card`

### latent rule class

초기 pilot에서는 아래 rule class만 허용한다.

- merged header scope 선택
- marker-conditioned row selection
- row group 기반 subtotal 갱신
- filter state에 따른 row inclusion
- aligned column 사이의 target slot 선택

초기 pilot에서 제외:

- free-floating abstract token puzzle
- 긴 텍스트 지시 규칙
- 3개 이상 rule의 동시 합성

### example grammar

각 example는 다음 의미를 가져야 한다.

- `input_table`
- `output_table`
- 두 table 사이에 동일한 latent rule이 존재

좋은 example 세트 조건:

- example 1과 2만 봐도 규칙 후보가 1-2개 정도로 좁혀져야 한다
- 추가 example이 있다면 규칙을 안정화하는 역할을 해야 한다
- 서로 다른 example은 같은 rule의 다른 instantiation이어야 한다
- 출력은 전체 표 재생성이 아니라, highlighted result cell, selected row subset, summary slot 변화처럼 compact해야 한다

### query grammar

query는 다음을 포함한다.

- 새 입력 table 또는 worksheet fragment
- 동일 rule을 적용해야 하는 명시적 또는 암시적 목표
- compact answer format

초기 pilot에서는 answer choice 방식을 권장한다.

### answer choice grammar

choice는 4개를 기본값으로 한다.

- `A`
- `B`
- `C`
- `D`

choice 설계 원칙:

- 1개는 정답
- 1개는 가장 흔한 잘못된 scope rule
- 1개는 partial rule만 맞는 오답
- 1개는 다른 row group 또는 다른 subtotal을 고른 distractor

choice 표면 예:

- mini table preview
- target cell highlight
- value / row label / column label

### level progression

#### Level 1

- 단일 header scope 또는 단일 group rule
- surface format 거의 동일
- distractor 약함

#### Level 2

- marker 또는 grouped-row 조건 포함
- distractor가 더 plausible하게 보임
- query에서 table 레이아웃이 약간 달라질 수 있음

#### Level 3

- 추가 example을 다른 page/sheet에서 확인해야 rule이 안정화됨
- merged header depth 또는 note scope가 늘어남
- 잘못된 규칙도 꽤 그럴듯하게 보이도록 설계

### invalid episode 조건

다음 중 하나면 invalid로 본다.

- 예시 하나만 보고도 정답이 너무 자명함
- 예시들 사이에 실제로 일관된 table rule이 없음
- choice들이 규칙적 오답이 아니라 랜덤 preview처럼 보임
- query가 example과 사실상 동일한 clone임
- 표 구조가 아니라 색 하나만 보면 풀리는 문제

### generation knobs

- header depth
- column count
- group count
- marker density
- subtotal placement
- distractor policy
- representation variant

### validation checklist

- example 2-3개에 일관된 latent rule이 있는가?
- query가 같은 rule을 요구하는가?
- 정답 choice가 유일한가?
- 가장 그럴듯한 오답이 실제 failure mode를 반영하는가?
- table structure를 읽지 않으면 풀 수 없는가?

## Family 2. `inventory_exception_disambiguation`

### 핵심 질문

처음 example table에서 가능한 여러 규칙 중, 예외 사례까지 반영했을 때 실제 규칙은 무엇인가?

### canonical workbook topology

최소형:

- Sheet `examples`
  - Page 1: ambiguous example 1, example 2
- Sheet `exception`
  - Page 1: exception card
- Sheet `query`
  - Page 1: query table + answer choice panel

확장형:

- Sheet `examples`
  - Page 1: ambiguous example pair
- Sheet `exception`
  - Page 1: exception 1
  - Page 2: note card 또는 second exception
- Sheet `query`
  - Page 1: query + answer choice

### 필수 primitive 조합

- `example_table_panel` x 2 이상
- `exception_card` x 1 이상
- `query_table_panel` x 1
- `answer_choice_panel` x 1

선택 primitive:

- `legend_panel`
- `note_card`
- `merged_header_block`
- `row_group_band`
- `filter_chip`

### latent rule structure

이 family는 다음 구조를 반드시 가져야 한다.

- 초반 example set은 underdetermined
- plausible wrong rule이 최소 1개 이상 존재
- 예외 사례가 그 wrong rule을 배제
- query는 예외 사례를 무시하면 틀리도록 설계

### ambiguity grammar

좋은 ambiguity는 아래 형태 중 하나여야 한다.

- whole-column rule처럼 보이지만 실제로는 특정 merged header scope
- 모든 highlighted row를 쓰는 것처럼 보이지만 실제로는 marker row만 사용
- section total처럼 보이지만 실제로는 filtered row만 포함
- chart cue가 전체 table을 가리키는 것처럼 보이지만 실제로는 특정 row group만 해당

### exception-surface grammar

예외 사례 surface는 아래 역할을 해야 한다.

- 잘못된 규칙 하나 이상을 명시적으로 무너뜨림
- 하지만 정답 규칙을 텍스트로 직접 말하지 않음
- 예외가 전체에 적용되는지, 특정 scope에만 적용되는지도 보여줌

예외 사례 surface는 noise가 아니어야 한다.  
"추가 example"이 아니라 "가설 제거 장치"여야 한다.

### query grammar

query는 아래를 만족해야 한다.

- ambiguous examples만으로는 정답을 확정할 수 없어야 함
- 예외 사례를 반영하면 정답이 유일해야 함
- 답은 여전히 compact answer로 제출 가능해야 함

### answer choice grammar

choice 설계 원칙:

- 1개는 예외 사례를 반영한 정답
- 1개는 ambiguous examples만 보고 세우기 쉬운 오답 규칙
- 1개는 scope를 한 단계 넓게/좁게 잡은 오답
- 1개는 명백히 다른 distractor

### level progression

#### Level 1

- ambiguous wrong rule 1개
- 예외 사례 1개로 제거 가능

#### Level 2

- merged header 또는 note scope가 ambiguity에 포함
- query table의 구조가 example과 약간 다름

#### Level 3

- 예외 사례와 query가 서로 다른 surface format을 일부 사용
- note + table 또는 chart inset + table을 함께 봐야 rule이 확정됨

### invalid episode 조건

다음 중 하나면 invalid로 본다.

- ambiguous examples만으로도 사실상 정답이 확정됨
- 예외 사례가 wrong rule을 실제로 배제하지 못함
- query가 예외 사례를 무시해도 우연히 정답이 됨
- 표 구조를 거의 보지 않고 텍스트만 읽으면 풀림

### generation knobs

- ambiguity type
- exception strength
- note usage
- header depth
- group structure
- answer choice policy

### validation checklist

- plausible wrong rule이 실제로 존재하는가?
- 예외 사례가 그 wrong rule을 무너뜨리는가?
- 예외 사례를 반영하면 정답이 유일한가?
- merged header, row group, note, filter 중 최소 하나가 실제로 의미를 가지는가?
- 사람이 화면만 보고 풀 수 있는가?
