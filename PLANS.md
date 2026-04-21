# PLANS

## 1. 왜 지금 방향을 다시 잡는가

현재 저장소는 환경, 렌더러, UI, replay, preview export, 테스트까지 기본 골격은 이미 잘 갖춰져 있다.  
문제는 "무엇을 재는 벤치마크인가"에 대한 정체성이다.

지금 코드에 들어 있는 family들은 주로 다음 성격에 가깝다.

- 보고서/워크북 안에서 숫자를 찾아 조합하는 업무형 탐색 문제
- appendix, note, detail table을 오가며 정답을 확정하는 구조
- 시각 구조 추론보다는 문맥, 단위, 정합성 확인에 가까운 문제

우리가 앞으로 지향하는 방향은 이것과도 다르고, 그렇다고 순수 추상 퍼즐과도 다르다.

- 목표: `Visual TableQA`를 바탕으로 한 상호작용형 reasoning benchmark
- 감각: 워크북/시트/페이지를 탐색하면서, 표와 차트와 노트에 나타난 시각 구조를 해석하고 규칙을 전이하는 문제
- 제약: 표와 worksheet fragment가 항상 핵심 evidence surface여야 하며, chart/note/legend는 이를 보조해야 한다

즉, 앞으로의 `table-env-bench`는 "업무형 workbook investigation benchmark"도 아니고, "표와 무관한 abstract puzzle benchmark"도 아니다.  
정체성은 "`워크북 형태의 인터랙티브 Visual TableQA benchmark`이며, 그 위에서 구조적 reasoning을 더 강하게 재는 것"이다.

## 2. 북극성

이 프로젝트가 궁극적으로 재고 싶은 능력은 다음과 같다.

- 시각적으로 렌더링된 표, worksheet fragment, 차트, 노트를 읽고 relevant evidence를 찾는 능력
- header, merged header, row group, marker, filter 상태, subtotal 구조를 해석하는 능력
- 여러 시트/페이지에 흩어진 단서를 조합하는 능력
- 성급한 일반화를 버리고 반례나 note를 통해 규칙을 수정하는 능력
- 표면 표현이 달라도 같은 tabular rule을 인식하는 능력
- 순서가 있는 worksheet transformation을 단계적으로 적용하는 능력

핵심은 "표에 무엇이 적혀 있는가"만이 아니라, "이 표 구조에서 어떤 규칙이 작동하는가"다.

## 3. 하지 않을 것

다음 항목은 새 canonical benchmark 방향에서 벗어나는 것으로 본다.

- 단일 숫자를 찾아 더하거나 빼는 lookup형 문제를 계속 늘리는 것
- 업무 도메인 용어 이해가 성능을 좌우하는 문제
- 순수 abstract shape puzzle처럼 표/worksheet 의미가 거의 없는 문제
- appendix 숫자 1개를 찾으면 곧바로 정답이 되는 구조
- hidden text dump, cell id, oracle metadata 같은 비시각적 shortcut
- debug affordance가 human mode 경험을 압도하는 UI

## 4. legacy 처리 원칙

현재 존재하는 family들은 당장 삭제하지 않는다.

- `summary_appendix_override`
- `chart_to_detail_lookup`
- `scale_shift_cross_sheet`

이 family들은 다음 용도로 유지한다.

- 환경/렌더러/탐색 동작에 대한 회귀 테스트
- preview/export 흐름 확인
- UI와 replay contract가 깨지지 않았는지 보는 smoke test

하지만 앞으로 이 family들을 benchmark의 중심이라고 설명하지 않는다.  
새로운 reasoning-first family가 들어오면, 기존 family는 문서와 코드에서 `legacy` 또는 `business` 성격으로 분리한다.

## 5. 새 benchmark의 기본 문제 구조

앞으로의 canonical episode는 아래 구조를 기본형으로 삼는다.

- `examples` 시트/페이지: 2-3개의 작은 table snippet 또는 worksheet fragment 예시
- `legend` 또는 `operators` 시트/페이지: marker, filter chip, header cue, chart/table mapping, note scope 같은 해석 규칙
- `query` 시트/페이지: 새 표 조각, target slot, 답 후보
- `counterexample` 또는 `appendix` 시트/페이지: 잘못된 가설을 배제하는 추가 표/노트/예외 사례

좋은 문제는 최소한 아래 세 단계를 포함해야 한다.

- induction: 예시로부터 규칙 후보를 세운다
- disambiguation: 다른 시트/페이지의 단서로 규칙을 확정한다
- transfer: 확정한 규칙을 query table에 적용한다

## 6. 새 family 설계 원칙

각 family는 다음 조건을 만족해야 한다.

- 최소 1개의 visually rendered table 또는 worksheet fragment가 주 evidence여야 한다
- 단순 lookup이 아니라 규칙 유도 단계가 있을 것
- 여러 sheet/page가 "필요해서" 존재할 것
- 첫 가설이 틀릴 가능성이 있는 구조를 포함할 것
- 텍스트 의미보다 header/group/scope/marker 같은 시각 구조가 핵심 단서일 것
- 답은 짧게 채점 가능하더라도 중간 reasoning은 짧지 않을 것
- seed가 달라도 같은 추상 family identity를 유지할 것
- 가능하면 최소 1개의 non-text visual cue가 정답 결정에 필수여야 한다

가급적 초기에 적극적으로 써야 하는 cue:

- merged-cell span 방향
- conditional formatting의 패턴 차이
- 아이콘의 셀 내부 위치
- indentation depth / hierarchy
- band / border 구조
- chart glyph와 table block의 정렬 관계

한 family가 계속 같은 연산만 반복하지 않도록, episode operator와 answer form도 다양화한다.

- operator 예:
  - scope 선택
  - 제외/포함
  - 대응 찾기
  - 순서 적용
  - 순위 / 정렬
  - 분류 / 진술 검증
- answer form 예:
  - target cell
  - row/column label
  - statement choice
  - mini-table choice
  - count
  - short text

## 7. 우선 도입할 canonical family

### 7.1 `channel_policy_transfer`

핵심:

- 몇 개의 table example을 보고 같은 rule을 새 query table에 적용한다.

보는 능력:

- 패턴 유도
- header/row scope 해석
- 규칙 전이

워크북 구성 예시:

- Sheet A: example 1, example 2
- Sheet B: example 3 또는 보조 example
- Sheet C: query + answer choice

좋은 mechanic 예:

- 특정 merged header 아래 값만 선택
- marker가 달린 row만 집계
- subtotal slot으로 어떤 값이 들어가는지 유도

### 7.2 `legend_operator_composition`

핵심:

- 색, marker, filter chip, row tag, legend item이 각각 table operation을 뜻하고, 이를 조합해야 한다.

보는 능력:

- symbol grounding
- table-region operator composition
- 순서 민감 reasoning

워크북 구성 예시:

- Sheet A: operator legend
- Sheet B: worked table example
- Sheet C: query pipeline

### 7.3 `inventory_exception_disambiguation`

핵심:

- 처음 example table만 보면 여러 규칙이 가능하지만, 다른 시트의 반례가 진짜 규칙을 확정한다.

보는 능력:

- hypothesis revision
- note/header scope 해석
- 과도한 일반화 억제

좋은 ambiguity 예:

- 전체 column rule처럼 보이지만 실제로는 특정 merged header scope만 해당
- 모든 highlighted row를 쓰는 것처럼 보이지만 실제로는 marker row만 집계

### 7.4 `cross_format_table_reasoning`

핵심:

- 같은 underlying tabular relation이 table, chart inset, note, legend 같은 다른 surface로 나타난다.

보는 능력:

- 표면 형식 불변 추상화
- chart/table alignment
- note/table mapping

### 7.5 `report_scope_reconciliation`

핵심:

- 개별 셀보다 merged header, grouped row, subtotal block, section band 같은 구조가 의미를 가진다.

보는 능력:

- 구조 추론
- scope resolution
- block 단위 reasoning

### 7.6 `order_sensitive_worksheet_pipeline`

핵심:

- 시트별로 worksheet operation 단계가 정의되며, 순서가 바뀌면 답이 달라진다.

보는 능력:

- multi-step composition
- 상태 업데이트
- 연산 순서 유지

## 8. 초기 답 형식 원칙

초기 버전에서는 채점과 디버깅을 쉽게 하기 위해 답 형식을 제한한다.

우선 허용:

- 선택지 `A/B/C/D`
- target cell 또는 target region
- row label / column label
- statement choice
- mini-table choice
- 최종 개수
- 짧은 numeric / symbolic output

초기에는 full-grid generation을 canonical output으로 삼지 않는다.  
먼저 interaction contract, renderer primitive, replay, 채점 안정성을 확보한다.

## 8A. level progression 원칙

초기 canonical family는 Level별 reasoning depth를 의도적으로 분리한다.

- Level 1
  - 2-3 reasoning steps
  - cue 1개
  - band/group 1개 또는 아주 얕은 scope
  - weak distractor
- Level 2
  - 3-4 reasoning steps
  - cue 1-2개
  - band/group 2개 또는 약한 counterexample
  - answer indirection 또는 representation shift가 약하게 추가될 수 있음
- Level 3
  - 4-5 reasoning steps
  - cue 2-3개
  - counterexample 또는 cross-sheet evidence 필수에 가깝게 고려
  - nested scope, stronger distractor, answer indirection 가능

Level을 올릴 때는 아래 축 중 1-2개만 올리는 것을 원칙으로 한다.

- perceptual load
- scope nesting
- operator complexity
- answer indirection
- navigation burden

Level 1에서 이미 4-5단계를 요구하는 설계는 피한다.

## 8B. episode rule 문서화 계획

episode rule은 generator code 안에만 숨어 있으면 안 된다. 구현 전에 아래 문서들을 순차적으로 준비한다.

### 문서 1. `episode_rulebook.md`

역할:

- episode를 구성하는 핵심 rule 단위를 정의
- rule의 입력, 적용 범위, 필요한 cue, 허용 answer form을 정리

포함 항목:

- rule id
- visual cue requirements
- operator type
- compatible family
- disallowed leakage
- common failure modes

### 문서 2. `visual_cue_inventory.md`

역할:

- text-only로는 풀 수 없게 만드는 시각 cue를 체계화

포함 항목:

- merged-cell span direction
- conditional formatting patterns
- icon anchor positions
- indentation / hierarchy
- band / border semantics
- chart/table alignment cues

### 문서 3. `operator_taxonomy.md`

역할:

- family가 반복적으로 subset aggregation에만 머무르지 않게 operator space를 정의

포함 항목:

- select
- filter
- match
- map
- order
- rank
- classify
- verify statement
- aggregate

### 문서 4. `answer_form_policy.md`

역할:

- family별로 어떤 output 형태를 써야 operator와 benchmark identity가 잘 맞는지 정리

포함 항목:

- target cell
- row/column label
- statement choice
- mini-table choice
- count
- short text / symbolic output

### 문서 5. `level_design_policy.md`

역할:

- Level 1/2/3에서 reasoning step 수와 complexity 축을 어떻게 올릴지 고정

포함 항목:

- target reasoning depth
- cue count
- band/group complexity
- counterexample pressure
- navigation burden

### 문서 6. `episode_validation_checklist.md`

역할:

- 새 episode가 benchmark-safe한지 확인

포함 항목:

- text-only solvability check
- leakage check
- distractor quality check
- deterministic generation check
- level-fit check

## 9. 필요한 primitive 백로그

새 family를 만들기 전에 renderer/data layer가 공통 primitive를 가져야 한다.

반드시 필요한 것:

- `example_table_panel`
- `query_table_panel`
- `answer_choice_panel`
- `legend_panel`
- `counterexample_card`
- `table_panel`
- `header_band`
- `merged_header_block`
- `row_group_band`
- `marker_chip`
- `filter_chip`
- `selection_frame`
- `chart_inset`
- `note_card`

가급적 있으면 좋은 것:

- `subtotal_row`
- `scope_badge`
- `group_label_strip`
- `operator_strip`
- `callout_pointer`

원칙:

- primitive는 family마다 새로 그리는 것이 아니라 재사용 가능해야 한다
- environment branch보다 generator helper와 renderer template로 해결해야 한다
- hit testing과 deterministic geometry를 깨지 않아야 한다

## 10. UI / 렌더러 방향

앱 셸은 지금의 premium console 방향을 유지해도 된다.  
하지만 page surface 안의 콘텐츠 언어는 "업무 리포트"와 "순수 추상 퍼즐" 사이에서, 명확히 `table-rooted reasoning surface` 쪽으로 가야 한다.

앞으로의 renderer 목표:

- 표와 worksheet fragment가 메인 evidence area일 것
- chart, legend, note는 보조 surface로 자연스럽게 붙을 것
- merged header, grouped row, subtotal, marker가 한눈에 읽힐 것
- 시각적 밀도는 높되 toy-like decoration은 줄일 것
- workbook shell은 유지하되 내부 surface는 더 구조적이고 해석 가능한 표면일 것

## 11. 구현 단계

### Phase 0. legacy 동결

목표:

- 기존 business family를 더 이상 확장하지 않고 동결한다

산출물:

- 문서에서 legacy 포지셔닝 명시
- smoke test용 family 목록 정리

완료 기준:

- 새 문서가 benchmark identity를 business lookup으로 설명하지 않음

### Phase 1. spec 정리

목표:

- 새 benchmark의 정체성과 family 설계 기준을 문서화한다

산출물:

- family design brief
- primitive glossary
- pilot family episode grammar
- pilot episode drafts
- answer format / difficulty policy 초안
- episode rule 문서 로드맵

완료 기준:

- 새 family proposal을 문서만 보고 작성할 수 있음

### Phase 1.5. episode rule docs 고정

목표:

- 실제 family 구현 전에 rule 단위 문서 체계를 먼저 고정한다

산출물:

- `episode_rulebook.md`
- `visual_cue_inventory.md`
- `operator_taxonomy.md`
- `answer_form_policy.md`
- `level_design_policy.md`
- `episode_validation_checklist.md`
- `generator_episode_schema.md`
- `pilot_implementation_strategy.md`

완료 기준:

- 새 episode 초안을 generator 코드 없이 문서 레벨에서 검토할 수 있음
- text-only solvability와 level misfit을 구현 전에 걸러낼 수 있음

### Phase 2. primitive 구현

목표:

- table-rooted reasoning family를 만들 수 있는 공통 renderer/data primitive를 확보한다

산출물:

- table panel 계열 primitive
- header/group/marker/filter primitive
- answer choice / counterexample / note / chart inset primitive

완료 기준:

- pilot family 2종을 family-specific hardcode 없이 조합 가능

### Phase 3. pilot family 구현

목표:

- `channel_policy_transfer`
- `inventory_exception_disambiguation`

위 두 family를 먼저 end-to-end로 구현한다.

완료 기준:

- seed별 deterministic episode 생성
- renderer preview 생성
- replay / scoring / human mode / agent mode 모두 동작

### Phase 4. baseline / evaluation 정리

목표:

- legacy heuristic과 새 pilot family의 관계를 정리한다

산출물:

- 새 pilot family용 단순 baseline 또는 no-op baseline
- evaluation docs 업데이트

완료 기준:

- benchmark report에서 legacy와 canonical family를 혼동하지 않음

## 12. done의 기준

다음이 충족되면 pivot이 제대로 반영된 것으로 본다.

- 문서 전반이 Visual TableQA를 benchmark의 기반으로 설명한다
- 새 canonical family가 table/worksheet fragment를 핵심 evidence로 사용한다
- chart/note/legend는 보조 근거로 남고, 표가 중심을 잃지 않는다
- human mode와 agent mode 모두 hidden shortcut 없이 유지된다
- preview와 replay가 새 family에도 그대로 작동한다
- legacy family는 계속 돌아가지만 benchmark identity의 중심은 아니다
