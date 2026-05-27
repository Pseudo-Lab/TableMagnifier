# Visual Cue Inventory

이 문서는 `table-env-bench`의 canonical episode에서 사용할 `non-text visual cue`를 체계적으로 정리한다.

목적은 다음과 같다.

- episode가 text-only lookup으로 무너지지 않게 한다
- family마다 어떤 시각 cue를 핵심 evidence로 삼는지 명확히 한다
- generator와 renderer가 어떤 cue를 먼저 지원해야 하는지 우선순위를 준다

핵심 원칙은 단순하다.

- cue는 장식이 아니라 reasoning에 필수여야 한다
- cue는 가능하면 table/worksheet semantics 안에 있어야 한다
- cue 하나만으로 정답을 직접 노출하지 말고, scope나 rule을 좁히는 역할을 하게 한다

## 1. cue 사용 원칙

좋은 visual cue는 아래 조건을 만족한다.

- 텍스트를 읽는 것만으로는 대체되지 않는다
- 현재 표의 scope, grouping, mapping, ordering 중 하나를 바꾼다
- renderer에서 seed가 같으면 안정적으로 재현된다
- 사람이 화면을 보고 자연스럽게 해석할 수 있다

피해야 할 cue 사용 방식:

- purely decorative 색칠
- 정답 셀만 노골적으로 둘러싸는 개발용 highlight
- 표와 무관한 추상 아이콘 퍼즐
- cue가 너무 미약해서 렌더링 해상도에 따라 사라지는 경우

## 2. Cue 카테고리

### 2.1 merged-cell span direction

정의:

- header 또는 side band가 어느 방향으로 span되는지가 scope를 결정하는 cue

좋은 사용 예:

- 같은 라벨이라도 왼쪽 block 전체를 span하는지, 위쪽 2개 column만 span하는지가 다름
- query에서 어느 subtotal block을 읽어야 하는지 merged header가 결정

잘 맞는 operator:

- scope 선택
- 대응 찾기
- statement verification

주의:

- 라벨 텍스트만 같고 span 정보가 없으면 풀리지 않게 설계해야 한다

### 2.2 conditional formatting pattern

정의:

- 단순 색상뿐 아니라 줄무늬, 점 패턴, 해치, data bar, 음영 강도 차이로 scope를 나타내는 cue

좋은 사용 예:

- 동일한 파란색 계열이라도 stripe 패턴 row만 포함
- fill 강도는 decorative이고 해치 패턴만 실제 의미를 가짐

잘 맞는 operator:

- filter
- classify
- exception-based disambiguation

주의:

- 색상 하나만 의미를 갖게 하면 text-only 설명으로 축약되기 쉬움
- 패턴 대비는 충분히 커야 한다

### 2.3 icon anchor position

정의:

- 동일 아이콘이라도 셀 중앙, 좌측, 우상단, baseline 옆에 붙는 위치 차이가 의미를 갖는 cue

좋은 사용 예:

- 우상단 삼각 아이콘은 "예외 포함"
- 셀 중앙 원형 아이콘은 "선택 대상"
- 같은 모양이지만 위치가 다르면 다른 operator를 뜻함

잘 맞는 operator:

- select
- map
- verify statement

주의:

- 아이콘 종류보다 위치 차이가 핵심이면, 라벨 텍스트 없이도 구분 가능해야 한다
- 현재 v1 renderer에서 canonical하게 쓰는 triangle anchor는 `top_left`, `top_right`, `bottom_left`, `bottom_right` 네 모서리로 제한한다

### 2.4 border / band semantics

정의:

- 두꺼운 구분선, 밴드 배경, section separator가 grouping 또는 stage boundary를 나타내는 cue

좋은 사용 예:

- 세로 band가 다른 block을 나누고, 각 block 안에서만 같은 rule이 적용됨
- subtotal 위의 두꺼운 rule이 aggregation boundary를 뜻함

잘 맞는 operator:

- group parsing
- order-sensitive pipeline
- aggregate

주의:

- border는 너무 많으면 clutter가 된다
- decorative line과 semantic line이 구분되어야 한다

### 2.5 indentation depth / hierarchy

정의:

- row label의 들여쓰기 깊이 또는 tree-like alignment가 hierarchy를 표현하는 cue

좋은 사용 예:

- 들여쓰기 0은 section
- 들여쓰기 1은 child row
- 들여쓰기 2는 leaf row
- 정답은 leaf row가 아니라 parent subtotal block

잘 맞는 operator:

- hierarchy parsing
- scope resolution
- rank within group

주의:

- 텍스트 라벨 앞 공백처럼 모호한 방식보다 명확한 geometry 차이를 주는 편이 좋다

### 2.6 row / cell marker morphology

정의:

- 점, 삼각형, 깃발, 체크, 링 같은 marker의 모양 차이가 의미를 갖는 cue

좋은 사용 예:

- filled circle은 include
- hollow circle은 compare-only
- triangle은 exception candidate

잘 맞는 operator:

- filter
- classify
- exception handling

주의:

- marker 모양만 바꾸지 말고 위치, count, 주변 band와 함께 쓰면 더 강해진다

### 2.7 chart-to-table alignment

정의:

- 차트의 bar/line/point/legend glyph가 table block이나 row group과 대응되는 cue

좋은 사용 예:

- chart에서 강조된 점선 series가 table의 특정 grouped row와 연결
- chart의 annotation 화살표가 table block 한 개를 가리킴

잘 맞는 operator:

- match
- map
- cross-format reasoning

주의:

- chart만 보고 pixel OCR 하게 만들면 안 된다
- chart는 보조 surface여야 한다

### 2.8 note anchor / callout attachment

정의:

- note card가 어느 cell, band, block에 붙어 있는지가 의미를 갖는 cue

좋은 사용 예:

- 같은 note text라도 붙는 위치가 다르면 scope가 달라짐
- footnote marker가 subtotal row에 붙었는지 header band에 붙었는지가 다름

잘 맞는 operator:

- disambiguation
- exception handling
- statement verification

주의:

- note text만 읽어서 푸는 문제가 되지 않게, attachment geometry가 필수여야 한다

### 2.9 viewport window / pan-to-target position

정의:

- 넓은 worksheet에서 현재 viewbox가 어느 열/행 범위를 보여주는지가 evidence가 되는 cue

좋은 사용 예:

- 초기 viewport에는 점검 열만 보이고, 오른쪽 target column은 zoom/pan 후에만 보임
- 사례 시트에서 확인한 column offset을 질의 시트의 같은 행에 적용
- `required_viewport_states`가 target rect와 match mode를 명시해 replay/static validation이 같은 상태를 검증

잘 맞는 operator:

- match column offset
- rule transfer
- select target cell

주의:

- 단순히 표를 크게 만들어 찾기 어렵게 하는 것은 좋은 cue가 아니다
- target column을 보려면 실제 reasoning상 pan/zoom이 필요해야 한다
- `viewbox_intersects_target`와 `target_center_in_viewbox` 중 어떤 조건을 쓰는지 manifest에 명시해야 한다

## 3. cue 조합 가이드

Level별로 cue는 아래 정도가 적당하다.

- Level 1
  - cue 1개
  - 가장 선명한 primary cue만 사용
- Level 2
  - cue 1-2개
  - primary cue + weak supporting cue
- Level 3
  - cue 2-3개
- cue 간 충돌이나 예외 사례 surface까지 포함 가능

권장 조합 예:

- merged header + marker morphology
- conditional pattern + exception note anchor
- indentation hierarchy + subtotal rule
- chart alignment + header scope

피해야 할 조합 예:

- cue 4개를 동시에 올리고 answer form까지 복잡하게 만드는 것
- 비슷한 cue를 여러 개 중복해서 사실상 같은 정보만 주는 것

## 4. family별 추천 cue

  - merged-cell span direction
  - marker morphology
  - indentation hierarchy
  - conditional formatting pattern
  - icon anchor position
  - note anchor
- `legend_operator_composition`
  - marker morphology
  - icon anchor position
  - band semantics
- `cross_format_table_reasoning`
  - chart-to-table alignment
  - note anchor
  - merged header scope
  - indentation hierarchy
  - merged-cell span direction
  - border / band semantics
- `marker_position_rule_transfer`
  - icon anchor position
- `excel_viewport_sheet_navigation`
  - viewport window / pan-to-target position
  - border / band semantics
  - indentation hierarchy when row labels need scope disambiguation
  - legend item
  - note anchor
- `order_sensitive_worksheet_pipeline`
  - band semantics
  - operator strip icon order
  - row/cell marker morphology

## 5. validation 질문

새 episode를 만들 때 아래 질문을 확인한다.

- cue를 제거하면 문제의 핵심이 무너지는가?
- 텍스트만 OCR하거나 라벨만 읽어서는 풀 수 없는가?
- cue가 표/worksheet semantics 안에 자연스럽게 놓여 있는가?
- cue가 정답을 직접 칠해 주는 수준으로 노골적이지 않은가?
- 동일 cue가 level이 올라갈 때도 재사용 가능한가?
