# Family Design Brief

## 목적

이 문서는 `table-env-bench`의 새 canonical family를 어떤 기준으로 설계해야 하는지 정의하는 실무용 brief이다.

이 문서의 전제는 다음과 같다.

- benchmark의 핵심 정체성은 `Visual TableQA-rooted interactive reasoning`이다
- workbook UI는 현실 업무 문서 재현만을 위한 껍데기가 아니라, table-centered evidence를 여러 시트/페이지에 분산시키는 공간이다
- 현재 canonical track은 `canonical_real_tableqa`이고, 사람에게 바로 읽히는 실제 업무형 합성 표를 기본 surface로 사용한다

이 문서는 특히 다음 작업을 바로 시작할 수 있게 만드는 것을 목표로 한다.

- 새 family proposal 작성
- generator helper 설계
- renderer primitive 우선순위 결정
- canonical family 구현 착수

관련 문서:

- [PLANS.md](/mnt/c/Users/imssh/Documents/TableMagnifier/PLANS.md)
- [docs/primitive_glossary.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/primitive_glossary.md)
- [docs/episode_rulebook.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/episode_rulebook.md)
- [docs/visual_cue_inventory.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/visual_cue_inventory.md)
- [docs/operator_taxonomy.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/operator_taxonomy.md)
- [docs/answer_form_policy.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/answer_form_policy.md)
- [docs/level_design_policy.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/level_design_policy.md)
- [docs/episode_validation_checklist.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/episode_validation_checklist.md)
- [docs/generator_episode_schema.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/generator_episode_schema.md)
- [docs/real_data_authoring_policy.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/real_data_authoring_policy.md)

## 이 benchmark가 재고 싶은 것

좋은 family는 아래 능력을 직접 겨냥해야 한다.

- 시각적으로 렌더링된 표와 worksheet fragment에서 relevant evidence를 찾는 능력
- header, merged header, row group, subtotal, marker, filter를 해석하는 능력
- 여러 sheet/page에 흩어진 단서를 조합하는 능력
- 틀린 가설을 예외 사례나 note로 수정하는 능력
- 표면 형식이 달라도 같은 tabular rule을 알아보는 능력
- 연산 순서와 그룹 구조를 유지하며 reasoning하는 능력

좋은 family는 아래 능력에 너무 의존하면 안 된다.

- 특정 업무 도메인 용어 이해
- 한국어 문장 의미만으로 문제 풀기
- 숫자 하나를 찾아 단순 산술하기
- 숨겨진 메타데이터 shortcut
- 표와 무관한 free-floating abstract token puzzle

## canonical family의 최소 조건

canonical family로 받아들이려면 아래 조건을 만족해야 한다.

1. 최소 1개의 visually rendered table 또는 worksheet fragment가 핵심 evidence여야 한다.
2. 최소 1개의 `induction` 단계가 있어야 한다.
3. 최소 1개의 `transfer` 단계가 있어야 한다.
4. 최소 1개의 `disambiguation` 또는 `exception handling` 단계가 있어야 한다.
5. workbook의 다중 sheet/page 구조가 억지 클릭 유도가 아니라 실제 reasoning 구조를 반영해야 한다.
6. 문제의 핵심은 텍스트 해독이 아니라 시각 구조, scope, grouping, mapping 파악이어야 한다.

## workbook episode 기본 구조

새 canonical episode는 아래 토폴로지 중 하나를 기본으로 삼는다.

### 구조 A: Example Table -> Query Table

- `examples` sheet/page: 2-3개의 input/output table example
- `query` sheet/page: 새 table fragment
- `answers` area: 짧은 답 또는 선택지

적합한 family:

- `channel_policy_transfer`

### 구조 B: Example Table -> Legend / Note -> Query Table

- `examples` sheet/page: 규칙이 작동하는 table example
- `legend` / `operators` / `notes` sheet/page: marker, filter chip, header cue, chart/table mapping 규칙
- `query` sheet/page: 적용 대상 table

적합한 family:

- `legend_operator_composition`
- `order_sensitive_worksheet_pipeline`

### 구조 C: Example Table -> Exception Surface -> Query Table

- `examples` sheet/page: 여러 가설이 가능해 보이는 example table
- `exception` sheet/page: 잘못된 가설을 배제하는 table / note / support surface
- `query` sheet/page: 최종 적용 문제

적합한 family:

- `inventory_exception_disambiguation`

### 구조 D: Table -> Chart / Note / Legend -> Query

- `main table` sheet/page: 핵심 evidence table
- `chart inset` / `note` / `legend` sheet/page: 같은 rule을 다른 surface로 드러내는 보조 근거
- `query` sheet/page: 최종 판단

적합한 family:

- `cross_format_table_reasoning`
- `report_scope_reconciliation`

## family one-pager에 반드시 들어가야 할 항목

앞으로 어떤 family를 제안하든 아래 항목을 채워야 한다.

- `family_id`
- 한 줄 설명
- 주로 재고 싶은 능력
- latent mechanic
- workbook evidence topology
- required table/worksheet surface
- supporting surface
- 필요한 renderer primitive
- answer format
- level progression
- distractor / failure mode
- deterministic generation knobs
- benchmark-safe validation checklist

## difficulty를 올리는 방식

난이도는 "복잡하게 보이게 만들기"가 아니라 아래 축으로 올린다.

### 1. header / scope ambiguity

- 어떤 merged header나 grouped row에 rule이 적용되는지 바로 확신할 수 없게 만든다

### 2. representation shift

- 같은 rule을 table, chart inset, note, legend 같은 다른 시각 형식으로 보여준다

### 3. composition depth

- rule이 한 번에 끝나지 않고 두 단계 이상 합성되도록 한다

### 4. exception pressure

- 첫 가설이 그럴듯하지만 틀리도록 만들고, 다른 시트의 evidence가 이를 수정하게 한다

### 5. navigation burden

- relevant evidence가 다른 sheet/page에 있어 실제 탐색이 필요하도록 한다

다음 방식으로 난이도를 올리는 것은 피한다.

- 랜덤 clutter만 늘리기
- 텍스트 설명만 길게 쓰기
- table semantics 없이 색/shape만 늘리기
- 답 후보를 과하게 비슷하게 만들기

## answer format 원칙

초기 canonical family는 다음 답 형식을 우선 사용한다.

- `A/B/C/D` 선택
- target cell 또는 target region
- row label / column label
- 최종 개수
- 짧은 numeric / symbolic output

초기 단계에서는 full-grid generation을 canonical output으로 요구하지 않는다.  
먼저 interaction contract, renderer primitive, replay, 채점 안정성을 확보한다.

## renderer primitive 우선순위

새 family 구현 전에 아래 primitive를 우선 지원해야 한다.

### must-have

- `example_table_panel`
- `query_table_panel`
- `answer_choice_panel`
- `legend_panel`
- `exception_card`
- `table_panel`
- `header_band`
- `merged_header_block`
- `row_group_band`
- `marker_chip`
- `filter_chip`
- `selection_frame`
- `note_card`

### should-have

- `chart_inset`
- `operator_strip`
- `scope_badge`
- `group_label_strip`
- `subtotal_row`

### rule

- primitive는 family-specific hack이 아니라 재사용 가능한 helper로 제공한다
- generator layer에서 조합하고 renderer는 primitive spec만 책임진다
- deterministic geometry와 hit testing은 유지한다

## Canonical Family Example 1: `channel_policy_transfer`

### 한 줄 설명

몇 개의 table example에서 공통 rule을 유도하고, 새 query table에 같은 rule을 적용하는 family.

### 주로 재고 싶은 능력

- analogical transfer
- visual rule induction
- table scope interpretation

### latent mechanic

- 입력 table과 출력 table의 차이를 보고 rule을 유도한다
- rule은 header, row group, marker, subtotal slot 같은 table 구조에 걸려 있어야 한다
- query table에는 같은 rule을 적용해야 한다
- 답은 전체 표 재생성이 아니라 compact answer로 제출한다

### workbook topology

- Sheet A: example 1, example 2
- Sheet B: example 3 또는 보조 example
- Sheet C: query + answer choices

### 좋은 episode의 조건

- example 2개만 봐도 규칙 후보가 1-2개 정도로 좁혀져야 한다
- 3번째 example이 rule을 안정화한다
- query는 표면적으로는 달라 보여도 같은 table rule이 적용된다

### 좋은 rule 예

- 특정 merged header 아래 값만 선택
- marker가 있는 row만 subtotal에 반영
- 특정 row group에서만 summary cell을 갱신
- filter chip에 해당하는 row만 남겼을 때 target value를 선택

### level progression

- Level 1: 단일 scope rule, 단일 group, surface format 동일
- Level 2: marker 또는 grouped-row 조건 포함
- Level 3: 다른 page의 추가 example을 봐야만 rule이 확정됨

### 흔한 실패 모드

- 눈에 띄는 색 하나만 보고 성급히 일반화
- 전체 column rule로 오해하지만 실제로는 merged header scope만 해당
- query에서 row group 구조가 조금 달라지면 rule을 놓침

### generation knobs

- header depth
- group count
- marker density
- subtotal placement
- distractor policy
- representation variant

### 초기 정답 형식 추천

- 정답 후보 `A/B/C/D`
- 또는 target cell / target value

## Pilot Family 2: `inventory_exception_disambiguation`

### 한 줄 설명

처음 example table만 보면 여러 규칙이 가능해 보이지만, 다른 시트의 예외 사례가 잘못된 가설을 제거하는 family.

### 주로 재고 싶은 능력

- hypothesis revision
- exception-surface use
- ambiguity resolution

### latent mechanic

- 초반 example set은 underdetermined다
- plausible wrong rule이 최소 1개 이상 존재한다
- 예외 사례가 그 wrong rule을 배제한다
- query는 예외 사례를 무시하면 틀리도록 설계한다

### workbook topology

- Sheet A: ambiguous example pair
- Sheet B: exception table 또는 note card
- Sheet C: query + answer choice

### 좋은 ambiguity 예

- 전체 column rule처럼 보이지만 실제로는 특정 merged header scope만 해당
- highlighted row 전부를 쓰는 것처럼 보이지만 실제로는 marker row만 집계
- subtotal이 전체 section 합처럼 보이지만 실제로는 filtered row만 포함

### level progression

- Level 1: 예외 사례 1개로 ambiguous rule 1개 제거
- Level 2: note 또는 legend가 scope를 추가로 좁힘
- Level 3: 예외 사례와 query가 서로 다른 surface format을 사용

### 흔한 실패 모드

- 첫 example에서 세운 rule을 끝까지 고수
- note나 예외 사례를 decorative element로 취급
- header scope를 무시하고 직관적으로 가장 큰 block만 선택

### generation knobs

- ambiguity type
- exception strength
- note usage
- header depth
- group shape
- answer choice policy

## Next-wave family 요약

- `legend_operator_composition`
  - marker, filter chip, legend item의 의미를 조합
- `cross_format_table_reasoning`
  - table, chart inset, note가 같은 rule을 다른 surface로 드러냄
- `report_scope_reconciliation`
  - merged header와 grouped row hierarchy가 의미를 결정
- `order_sensitive_worksheet_pipeline`
  - worksheet operation의 적용 순서가 정답을 바꿈

## family proposal acceptance checklist

새 family proposal은 아래 질문에 모두 "예"라고 답할 수 있어야 한다.

- visually rendered table 또는 worksheet fragment가 중심인가?
- chart/note/legend는 table evidence를 보조하는가?
- induction과 transfer가 모두 있는가?
- disambiguation 또는 exception-surface 단계가 있는가?
- multi-sheet/page 구조가 실제 reasoning 필요를 반영하는가?
- hidden shortcut 없이도 사람이 풀 수 있는가?
- pure abstract puzzle처럼 table semantics가 사라지지 않았는가?
