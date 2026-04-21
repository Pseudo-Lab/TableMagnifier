# Primitive Glossary

## 목적

이 문서는 새 canonical family를 구현할 때 공통으로 재사용할 visual primitive를 정의한다.

이 문서의 역할은 다음과 같다.

- generator helper가 어떤 입력을 받아야 하는지 정의
- renderer가 어떤 surface를 그려야 하는지 정의
- family-specific hack 대신 공통 부품으로 문제를 구성하도록 기준 제공

앞으로의 primitive는 `Visual TableQA`를 바탕으로 해야 한다.  
즉, 표와 worksheet fragment가 중심이고, chart/note/legend는 표를 보조하는 surface로 설계한다.

## 설계 원칙

### 1. primitive는 family보다 먼저 존재해야 한다

좋은 family는 새 primitive를 매번 발명하지 않고, 이미 있는 primitive의 조합으로 만들어질 수 있어야 한다.

### 2. primitive는 table-rooted visual role이 분명해야 한다

각 primitive는 "표에서 어떤 역할을 하는가"가 명확해야 한다.

- example table을 보여주는가
- query table을 보여주는가
- header hierarchy를 보여주는가
- row group이나 subtotal 구조를 보여주는가
- note, legend, chart inset으로 scope를 보조하는가

### 3. hidden shortcut을 만들면 안 된다

primitive spec 안에 hidden answer logic이나 디버그 전용 정보가 섞여 있으면 안 된다.

### 4. deterministic geometry를 가져야 한다

seed가 같으면 같은 primitive 배치가 안정적으로 생성되어야 한다.

### 5. interaction surface와 non-interaction surface를 구분해야 한다

모든 primitive가 클릭 가능한 것은 아니다.  
region hit testing이 필요한 primitive만 명시적으로 interactive region과 연결한다.

## 공통 spec 규칙

primitive spec은 아래 공통 필드를 공유하는 것을 권장한다.

```json
{
  "primitive_id": "query-table-1",
  "primitive_type": "query_table_panel",
  "rect": {"x": 120, "y": 180, "width": 520, "height": 280},
  "metadata": {}
}
```

공통 필드:

- `primitive_id`
- `primitive_type`
- `rect`
- `metadata`

`rect`는 page canvas 기준 절대 좌표를 사용한다.

## Primitive 분류

primitive는 크게 다섯 부류로 나눈다.

- panel primitives
- table structure primitives
- cell / marker primitives
- supporting evidence primitives
- answer / selection primitives

---

## 1. Panel Primitives

### 1.1 `table_panel`

역할:

- worksheet-like table surface의 기본 패널

필수 필드:

- `columns`
- `rows`
- `cell_matrix`

선택 필드:

- `title`
- `subtitle`
- `sheet_label`
- `table_variant`

주의:

- abstract grid처럼 보이기보다 table/worksheet로 읽혀야 한다
- column width, header band, row rhythm이 자연스러워야 한다

### 1.2 `example_table_panel`

역할:

- input -> output table example 한 쌍을 보여주는 기본 패널

필수 필드:

- `input_table`
- `output_table`

선택 필드:

- `title`
- `badge`
- `scope_hint`

권장 용도:

- `channel_policy_transfer`
- `inventory_exception_disambiguation`

### 1.3 `query_table_panel`

역할:

- 규칙을 적용해야 하는 새 query table을 보여주는 패널

필수 필드:

- `query_table`

선택 필드:

- `title`
- `focus_hint`
- `target_slot`

주의:

- query panel은 정답을 노골적으로 암시하면 안 된다

### 1.4 `legend_panel`

역할:

- marker, filter chip, row tag, header cue, line style 같은 visual cue의 의미를 보여주는 패널

필수 필드:

- `items`

각 item 권장 필드:

- `swatch`
- `label`
- `meaning`

주의:

- legend는 텍스트만 길게 나열하면 안 된다
- 시각 cue와 table semantics의 매핑이 핵심이어야 한다

### 1.5 `exception_card`

역할:

- 잘못된 가설을 제거하는 반례 또는 예외 사례를 보여주는 패널

필수 필드:

- `input_table`
- `output_table` 또는 `resolved_scope`

선택 필드:

- `title`
- `exception_label`
- `note_ref`

주의:

- 예외 사례 카드는 추가 clutter가 아니라 hypothesis 제거 장치여야 한다

### 1.6 `answer_choice_panel`

역할:

- `A/B/C/D` 선택지 또는 target cell 후보를 묶어 보여주는 패널

필수 필드:

- `choices`

choice 권장 필드:

- `choice_id`
- `label`
- `preview`
- `choice_type`

주의:

- choice는 random distractor가 아니라 실제 failure mode를 반영해야 한다

---

## 2. Table Structure Primitives

### 2.1 `header_band`

역할:

- 단일 depth column header 또는 row header 밴드

필수 필드:

- `axis`
- `labels`

권장 용도:

- 기본 table hierarchy 표현

### 2.2 `merged_header_block`

역할:

- 여러 column 또는 row 위에 걸친 merged header scope를 표현

필수 필드:

- `span_start`
- `span_end`
- `label`

중요성:

- canonical family에서 scope ambiguity를 만드는 핵심 primitive

### 2.3 `row_group_band`

역할:

- 특정 section 또는 grouped row cluster를 시각적으로 묶어 보여주는 밴드

필수 필드:

- `row_start`
- `row_end`
- `label`

주의:

- 색칠 자체보다 grouping 의미가 먼저 읽혀야 한다

### 2.4 `subtotal_row`

역할:

- section subtotal 또는 total row를 구분하는 구조적 행

필수 필드:

- `row_index`
- `style_variant`

주의:

- loud highlight block보다 typography, tone, spacing으로 강조한다

### 2.5 `selection_frame`

역할:

- 현재 focus target 또는 후보 scope를 둘러싸는 강조 프레임

필수 필드:

- `target_rect`

주의:

- dev overlay처럼 보이지 않게, human-readable한 강조여야 한다

---

## 3. Cell / Marker Primitives

### 3.1 `table_cell`

역할:

- table 안의 개별 셀 표현

표현 가능한 속성 예:

- `text`
- `numeric_style`
- `fill_tone`
- `alignment`
- `state`

원칙:

- cell 자체보다 cell이 속한 header/group/scope 관계가 중요할 수 있다

### 3.2 `marker_chip`

역할:

- 특정 row, column, cell에 붙는 작은 marker

예:

- 원형 점
- 짧은 태그
- 색 띠

용도:

- relevant scope 표시
- filter 대상 표시
- operator grounding

### 3.3 `filter_chip`

역할:

- 표 위쪽 또는 옆에 붙는 현재 filter / view 상태 표시

필수 필드:

- `label`
- `state`

주의:

- filter chip은 장식이 아니라 row inclusion rule의 일부일 수 있다

### 3.4 `cell_annotation`

역할:

- 특정 셀이나 block에 짧은 annotation을 붙여 scope나 exception을 나타냄

필수 필드:

- `target`
- `label`

주의:

- note card를 대체하는 긴 설명이 아니라, local cue 수준에 머물러야 한다

---

## 4. Supporting Evidence Primitives

### 4.1 `note_card`

역할:

- footnote, appendix note, exception text를 보여주는 보조 패널

필수 필드:

- `title`
- `body`

선택 필드:

- `scope_tag`
- `linked_target`

주의:

- note는 표를 대체하지 않는다
- table evidence의 scope를 바꾸거나 해석을 좁히는 용도로 쓴다

### 4.2 `chart_inset`

역할:

- table과 연결된 작은 차트 surface

필수 필드:

- `chart_type`
- `series`
- `axis_labels`

용도:

- relevant row/column group을 좁히기
- 같은 relation을 다른 surface로 보여주기

주의:

- chart만 보고 정답을 pixel OCR 하게 만들지 않는다

### 4.3 `operator_strip`

역할:

- filter, select, aggregate, map 같은 operation 단계를 순서대로 보여주는 strip

필수 필드:

- `operators`

권장 용도:

- `legend_operator_composition`
- `order_sensitive_worksheet_pipeline`

### 4.4 `group_label_strip`

역할:

- section, block, stage를 짧게 라벨링하는 구조적 strip

주의:

- 읽기 편한 hierarchy를 돕되, 정답을 직접 설명하지는 않는다

---

## 5. Answer / Selection Primitives

### 5.1 `target_cell_choice`

역할:

- 정답 후보를 "어느 cell이 맞는가" 형태로 보여주는 choice item

### 5.2 `value_choice`

역할:

- 정답 후보를 값 또는 짧은 symbolic output으로 보여주는 choice item

### 5.3 `mini_table_choice`

역할:

- 정답 후보를 작은 table preview 형태로 보여주는 choice item

권장 용도:

- `channel_policy_transfer`
- `inventory_exception_disambiguation`

---

## 6. 구현 우선순위

먼저 구현할 primitive:

- `table_panel`
- `example_table_panel`
- `query_table_panel`
- `header_band`
- `merged_header_block`
- `row_group_band`
- `marker_chip`
- `filter_chip`
- `note_card`
- `answer_choice_panel`
- `selection_frame`

그다음 구현할 primitive:

- `chart_inset`
- `operator_strip`
- `subtotal_row`
- `cell_annotation`
- `group_label_strip`

## 7. 체크리스트

새 primitive를 추가할 때는 아래 질문을 확인한다.

- table-rooted evidence를 더 잘 표현하는가?
- family-specific hack 없이 재사용 가능한가?
- hidden shortcut이나 debug leakage를 만들지 않는가?
- deterministic geometry와 hit testing을 유지하는가?
- human mode와 agent mode 모두에서 의미가 자연스러운가?
