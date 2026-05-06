# Answer Form Policy

이 문서는 canonical episode에서 사용할 `정답 형식`을 정리한다.

목표는 다음과 같다.

- answer form이 특정 operator에 과도하게 치우치지 않게 한다
- free-form numeric answer만 반복되어 benchmark가 단조로워지는 것을 막는다
- 평가와 replay는 단단하게 유지하면서도 reasoning 다양성을 확보한다

## 1. 기본 원칙

- answer form은 문제의 핵심 reasoning을 드러내야 한다
- answer form이 너무 자유로우면 채점과 해석이 불안정해진다
- answer form이 너무 단순하면 결국 OCR lookup benchmark로 수렴한다

좋은 answer form:

- operator와 자연스럽게 연결된다
- distractor를 meaningful하게 설계할 수 있다
- 사람이 UI에서 제출하기도 무리가 없다

## 2. 우선 허용하는 answer form

### 2.1 target cell choice

설명:

- 어느 cell이 정답인지 고르게 한다

잘 맞는 operator:

- `select_scope`
- `match_mapping`

장점:

- table-rooted 느낌이 강하다
- Level 1에 적합하다

### 2.2 row / column label answer

설명:

- 어느 row나 column이 정답인지 label로 답하게 한다

잘 맞는 operator:

- `rank_compare`
- `select_scope`

장점:

- 숫자 계산 없이도 강한 reasoning을 볼 수 있다

### 2.3 statement choice

설명:

- A/B/C/D 중 올바른 진술을 선택하게 한다

잘 맞는 operator:

- `verify_statement`

장점:

- aggregate 중심을 벗어나기 좋다
- note와 exception reasoning에 잘 맞는다

주의:

- 진술 문장만 읽고 풀리지 않도록, table cue가 필수여야 한다

### 2.4 mini-table choice

설명:

- 작은 표 preview들 중에서 올바른 결과를 고르게 한다

잘 맞는 operator:

- `order_sequence`
- `classify_state`

장점:

- output이 table-like form이라 benchmark identity를 잘 유지한다

### 2.5 count

설명:

- 몇 개가 조건을 만족하는지 답하게 한다

잘 맞는 operator:

- `filter_members`
- `classify_state`

주의:

- count-only problem이 계속 반복되면 operator 다양성이 줄어든다

### 2.6 short numeric / symbolic output

설명:

- 짧은 값이나 심볼을 답하게 한다

잘 맞는 operator:

- `aggregate`
- `order_sequence`

주의:

- free-form numeric answer는 꼭 필요할 때만 쓴다
- 가능하면 choice나 target-cell answer와 섞어서 사용한다

## 3. level별 권장 answer form

- Level 1
  - target cell choice
  - row / column label
  - simple statement choice
- Level 2
  - mini-table choice
  - count
  - scoped statement choice
- Level 3
  - answer indirection이 있는 mini-table choice
  - exception-based statement choice
  - short symbolic output

## 4. 피해야 할 패턴

- 모든 family가 결국 숫자 하나를 입력하게 하는 것
- statement choice인데 문장만 읽어도 정답이 보이는 것
- mini-table choice인데 시각적으로 너무 비슷해서 랜덤 guessing처럼 느껴지는 것
- target cell choice인데 사실상 강조된 셀 하나만 너무 튀게 보이는 것

## 5. family별 추천

  - target cell choice
  - mini-table choice
  - statement choice
  - target cell choice
- `legend_operator_composition`
  - mini-table choice
  - target stage output
- `cross_format_table_reasoning`
  - row label
  - statement choice
  - target cell choice
  - row / column label
- `order_sensitive_worksheet_pipeline`
  - mini-table choice
  - short symbolic output

## 6. validation 질문

- answer form이 operator와 잘 맞는가?
- answer form이 OCR shortcut으로 무너지지 않는가?
- distractor가 실제 failure mode를 반영하는가?
- human mode에서 입력하기 과하게 번거롭지 않은가?
