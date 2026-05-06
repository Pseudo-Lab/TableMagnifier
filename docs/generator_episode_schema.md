# Generator-Friendly Episode Schema

이 문서는 새 canonical episode를 실제 generator 코드로 옮길 때 사용할 `generator-friendly schema` 초안을 정의한다.

목표는 두 가지다.

- 현재 코드베이스의 dataclass와 크게 충돌하지 않는 최소 스키마를 먼저 제시한다
- canonical family를 구현하려면 어디를 확장해야 하는지도 분리해서 적는다

현재 기준 코드:

- [models.py](/mnt/c/Users/imssh/Documents/TableMagnifier/src/table_env_bench/data/models.py)
- [generators.py](/mnt/c/Users/imssh/Documents/TableMagnifier/src/table_env_bench/data/generators.py)
- [renderer.py](/mnt/c/Users/imssh/Documents/TableMagnifier/src/table_env_bench/render/renderer.py)

## 1. 현재 코드 기준 제약

현재 구현은 아래 구조를 이미 지원한다.

- `EpisodeSpec -> WorkbookSpec -> SheetSpec -> PageSpec`
- page 안에 `table`, `chart`, `legend`, `text_block`
- table 안에 `TableCellSpec`
  - `row`, `col`, `text`, `row_span`, `col_span`, `style`, `align`

즉, 현재는 다음이 쉽다.

- merged header
- grouped-looking table layout
- text label
- body/header/total/highlight 같은 style 기반 강조
- chart, legend, note block 배치

반대로 현재 바로는 약한 부분:

- cell-level icon anchor position
- conditional-format pattern
- cell-level metadata 기반 custom drawing
- answer choice preview surface
- statement choice용 explicit choice element

따라서 schema도 두 단계로 나눈다.

- `Schema A`: 현재 모델에 최대한 얹을 수 있는 최소형
- `Schema B`: canonical family 구현을 위해 확장해야 하는 목표형

## 2. Schema A: current-model compatible

### 2.1 episode-level metadata

현재 `EpisodeSpec.metadata`를 활용해 아래를 넣을 수 있다.

```json
{
  "episode_intent": {
    "primary_operator": "select_scope",
    "support_operator": null,
    "primary_visual_cue": "merged_header_span",
    "answer_form": "target_cell_choice"
  }
}
```

용도:

- generator와 test가 episode의 의도를 확인
- renderer는 반드시 모두 사용하지 않아도 됨

### 2.2 page-level metadata

현재 `PageSpec.metadata`에는 아래 정도를 두는 것이 자연스럽다.

```json
{
  "page_role": "examples",
  "example_index": 1,
  "draft_id": "channel_policy_transfer_l1_icon_anchor_pick_v1"
}
```

### 2.3 table-level metadata

현재 `TableElementSpec.metadata`를 활용해 table-level cue를 넣는다.

```json
{
  "table_variant": "pilot_example_table",
  "active_band": "검토",
  "choice_group": "query_choices",
  "render_hints": {
    "excel_chrome": true,
    "freeze_columns": 1
  }
}
```

이 단계에서는 `active_band` 같은 힌트가 generator/test용 의미를 가지며, 실제 시각 cue는 merged header 셀과 text/icon 대체 텍스트로 표현한다.

### 2.4 region metadata

현재 `RegionSpec.metadata`를 써서 선택 대상이나 answer choice를 groundable region으로 붙일 수 있다.

```json
{
  "region_type": "answer_choice",
  "choice_id": "B",
  "is_correct": false
}
```

주의:

- `is_correct`는 human/agent view에 새면 안 된다
- generator/test 단계에서만 유지하거나 runtime payload에서 제거해야 한다

## 3. Schema B: pilot-target extension

canonical family를 제대로 구현하려면 아래 확장이 필요하다.

### 3.1 `TableCellSpec.metadata`

가장 먼저 필요한 확장이다.

추천 형태:

```json
{
  "icon": {
    "kind": "triangle",
    "anchor": "top_right"
  },
  "pattern": {
    "kind": "diagonal_stripe",
    "tone": "blue_soft"
  },
  "semantic_role": "candidate"
}
```

추가 이유:

- text-only 대체 없이 icon anchor를 렌더링할 수 있어야 함
- conditional formatting pattern을 실제 visual cue로 그릴 수 있어야 함

### 3.2 choice surface spec

현재는 choice를 별도 element로 다루는 모델이 없다. canonical family에는 최소 choice panel이 필요하다.

추천 새 element:

- `ChoicePanelElementSpec`

추천 필드:

```json
{
  "element_id": "query-choices",
  "type": "choice_panel",
  "choice_type": "cell_choice",
  "choices": [
    {"choice_id": "A", "label": "A", "preview_kind": "cell_target"},
    {"choice_id": "B", "label": "B", "preview_kind": "cell_target"}
  ]
}
```

### 3.3 explicit example pair metadata

`example_table_panel`을 흉내내기 위해 현재는 page metadata나 title에 의존해야 한다. 더 자연스럽게 하려면 table metadata에 아래 정도가 필요하다.

```json
{
  "panel_role": "example_input",
  "paired_with": "example-1-output",
  "example_group": "example-1"
}
```

## 4. 추천 intermediate schema

지금 당장 구현을 시작한다면 full refactor보다 아래 intermediate schema가 현실적이다.

### 4.1 page 단위

- example input table
- example output text block 또는 highlight region
- query table
- answer choice는 `text_block` + custom regions로 임시 구현

### 4.2 table 단위

- merged header는 `row_span`, `col_span`으로 구현
- icon/pattern은 우선 `style` 확장과 renderer 분기 최소 추가로 구현

### 4.3 region 단위

- answer choice clickable region
- query target candidate region

## 5. Draft 1 mapping

[pilot_episode_drafts.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/pilot_episode_drafts.md)의 `channel_policy_transfer_l1_icon_anchor_pick_v1`을 현재 코드에 매핑하면 아래와 같다.

- workbook
  - `examples` sheet
  - `query` sheet
- examples page
  - table 2개
  - output 강조는 region label + highlight cell style
- query page
  - table 1개
  - choice panel은 임시로 작은 table 4개 또는 text blocks 4개

핵심 확장:

- cell metadata로 `triangle@top_right` vs `triangle@bottom_left`

## 6. Draft 2 mapping

`inventory_exception_disambiguation_l1_pattern_vs_icon_statement_v1`은 아래처럼 매핑 가능하다.

- examples sheet
  - ambiguous example table 2개
- exception sheet
  - exception table 1개
- query sheet
  - query table 1개
  - statement choice panel 1개

핵심 확장:

- cell pattern rendering
- statement choice element 또는 equivalent text block layout

## 7. 추천 최소 코드 변경

pilot 구현 전 최소 변경 우선순위:

1. `TableCellSpec`에 `metadata: dict[str, Any]` 추가
2. renderer `_render_table()`가 cell metadata의 `icon`과 `pattern`을 읽어 간단한 overlay를 그림
3. answer choice를 표현할 임시 `text_block`-based helper 또는 새 `choice_panel` spec 추가
4. generator helper에 `make_choice_regions()` 같은 유틸 추가

## 8. validation 포인트

- new metadata가 default render를 깨지 않는가?
- regression family table이 그대로 렌더되는가?
- preview export에서도 icon/pattern이 동일하게 보이는가?
- answer choice region이 click-groundable 한가?

## 9. 문서 연결

- [docs/pilot_episode_drafts.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/pilot_episode_drafts.md)
- [docs/episode_rulebook.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/episode_rulebook.md)
- [docs/visual_cue_inventory.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/visual_cue_inventory.md)
- [docs/answer_form_policy.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/answer_form_policy.md)
