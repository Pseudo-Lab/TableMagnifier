# `public_dev_real_v1` 문제별 해설

> 실제 agent가 받는 preview surface PNG를 그대로 붙인 해설 문서입니다.  
> 기준 pack: `public_dev_real_v1`  
> smoke pack인 `public_smoke_real_v1`는 이 문서의 일부 문제를 부분집합으로 포함합니다.

## 1. 채널 집행 기준 L1 · 3월 대상 칸

`instance_id`: `public_dev_real_v1__channel_policy_transfer_icon_scope_cell_l1_s0`  
`정답`: `A`  
`질문`: 사례 시트의 기준을 따르면 현재 채널표에서 집행 대상으로 표시할 칸은 어디인가?

### 실제 이미지

**사례 시트**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__channel_policy_transfer_icon_scope_cell_l1_s0_examples_examples-p1.png)

**확인 시트**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__channel_policy_transfer_icon_scope_cell_l1_s0_query_query-p1.png)

### 해설

- 사례 시트의 핵심은 `band`와 `표식 위치`를 같이 읽는 것입니다.
- 메모에 적힌 대로 같은 `집행 band` 안에서 실제 반영 위치는 `조치` 셀입니다.
- 확인 시트 선택지 중 이 조건을 동시에 만족하는 것은 `제휴 / 집행-조치`뿐이라서 `A`가 정답입니다.

### 흔한 오답

- `B`: `조치`는 맞지만 `계획 band`라서 탈락입니다.
- `C`: `집행 band`는 맞지만 `상태` 칸이라 반영 위치가 아닙니다.
- `D`: band도 다르고 위치도 다릅니다.

---

## 2. 채널 집행 기준 L2 · 확장 사례

`instance_id`: `public_dev_real_v1__channel_policy_transfer_icon_scope_cell_l2_s0`  
`정답`: `A`  
`질문`: 두 사례를 함께 보면 현재 채널표에서 집행 대상으로 남는 칸은 어디인가?

### 실제 이미지

**사례 시트 1**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__channel_policy_transfer_icon_scope_cell_l2_s0_examples_examples-p1.png)

**보강 사례**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__channel_policy_transfer_icon_scope_cell_l2_s0_examples_examples-p2.png)

**확인 시트**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__channel_policy_transfer_icon_scope_cell_l2_s0_query_query-p1.png)

### 해설

- 첫 사례만 보면 `집행 band` 안의 후보가 보이지만, 두 번째 사례가 `묶음 경계`까지 고정합니다.
- 보강 사례 메모에 `묶음 머리글 아래 있는 행만 같은 후보군`이라고 적혀 있습니다.
- 확인 시트의 목표는 `집행 band · 분석 묶음`이므로, 후보는 `분석 묶음` 안의 `집행-조치` 셀만 남습니다.
- 이 조건을 만족하는 선택지는 `가람 / 집행-조치`인 `A`입니다.

### 흔한 오답

- `B`: 같은 `집행-조치`지만 다른 묶음입니다.
- `C`: 같은 행이어도 `계획` 칸이라 탈락입니다.
- `D`: 표식만 보고 묶음 경계를 놓치면 고르기 쉬운 오답입니다.

---

## 3. 채널 집행 기준 L3 · 메모 반영

`instance_id`: `public_dev_real_v1__channel_policy_transfer_icon_scope_cell_l3_s0`  
`정답`: `A`  
`질문`: 기준 사례와 보조 메모를 함께 반영하면 현재 채널표에서 집행 대상으로 표시할 칸은 어디인가?

### 실제 이미지

**사례 시트 1**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__channel_policy_transfer_icon_scope_cell_l3_s0_examples_examples-p1.png)

**보강 사례**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__channel_policy_transfer_icon_scope_cell_l3_s0_examples_examples-p2.png)

**기준 메모**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__channel_policy_transfer_icon_scope_cell_l3_s0_appendix_appendix-p1__note_anchor-note.png)

**확인 시트**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__channel_policy_transfer_icon_scope_cell_l3_s0_query_query-p1.png)

### 해설

- 사례 두 장으로 `집행 band · 운영 묶음`까지는 고정할 수 있습니다.
- 하지만 L3에서는 메모가 추가로 `top_right 방향 삼각형만 실제 후보`라고 못 박습니다.
- 따라서 같은 묶음 안에 있더라도 `bottom_left` 방향 후보는 제외해야 합니다.
- 확인 시트에서 이 조건을 만족하는 선택지는 `다온 / 집행-조치`인 `A`입니다.

### 흔한 오답

- `B`나 `D`: 묶음은 맞지만 삼각형 방향을 무시하면 걸리는 오답입니다.
- `C`: 행은 비슷해 보여도 `계획-조치`라서 탈락입니다.

---

## 4. 채널 집행 기준 L2 · 4월 변형

`instance_id`: `public_dev_real_v1__channel_policy_transfer_icon_scope_cell_l2_s1`  
`정답`: `B`  
`질문`: 4월 표로 바뀐 현재 채널표에서 집행 대상으로 남는 칸은 어디인가?

### 실제 이미지

**사례 시트 1**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__channel_policy_transfer_icon_scope_cell_l2_s1_examples_examples-p1.png)

**보강 사례**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__channel_policy_transfer_icon_scope_cell_l2_s1_examples_examples-p2.png)

**확인 시트**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__channel_policy_transfer_icon_scope_cell_l2_s1_query_query-p1.png)

### 해설

- 이 문제는 규칙은 같고 표 내용만 4월 변형으로 바뀐 경우입니다.
- 목표 조건은 `계획 band · 운영 묶음`입니다.
- 따라서 `운영 묶음` 아래에서 `계획-조치` 칸만 후보가 됩니다.
- 네 선택지 중 정확히 일치하는 것은 `라온 / 계획-조치`인 `B`입니다.

### 흔한 오답

- `A`: 같은 `계획-조치`라도 다른 묶음입니다.
- `D`: 행은 맞아 보여도 `집행-조치`라서 탈락입니다.

---

## 5. 재고 예외 판정 L1 · 적용 기준

`instance_id`: `public_dev_real_v1__inventory_exception_disambiguation_pattern_vs_icon_statement_l1_s0`  
`정답`: `B`  
`질문`: 사례와 예외 시트를 함께 보면 현재 재고표에 대해 맞는 설명은 어느 것인가?

### 실제 이미지

**예시 시트**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__inventory_exception_disambiguation_pattern_vs_icon_statement_l1_s0_examples_examples-p1.png)

**반례 시트**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__inventory_exception_disambiguation_pattern_vs_icon_statement_l1_s0_exception_exception-p1.png)

**선택 시트**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__inventory_exception_disambiguation_pattern_vs_icon_statement_l1_s0_query_query-p1.png)

### 해설

- 예시 시트만 보면 `사선 표시`와 `삼각 표식`이 자주 같이 보여서 둘 다 기준처럼 보입니다.
- 반례 시트가 결정적입니다. 여기서 두 표식이 갈라지므로 하나는 버려야 합니다.
- query 메모가 `사선 표시가 아니라 삼각 표식 행이 실제 기준`이라고 정리해 줍니다.
- 따라서 정답 설명은 `삼각 표식 행`인 `B`입니다.

### 흔한 오답

- `A`: 예시만 보고 `사선 표시`를 기준으로 고르면 빠지는 오답입니다.
- `D`: 표식이 하나라도 있으면 다 고른다는 과잉 일반화입니다.

---

## 6. 재고 예외 판정 L2 · 범위 메모

`instance_id`: `public_dev_real_v1__inventory_exception_disambiguation_pattern_vs_icon_statement_l2_s0`  
`정답`: `B`  
`질문`: 예외 시트와 범위 메모를 함께 보면 현재 재고표에 대해 맞는 설명은 어느 것인가?

### 실제 이미지

**예시 시트**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__inventory_exception_disambiguation_pattern_vs_icon_statement_l2_s0_examples_examples-p1.png)

**예외 확인 표**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__inventory_exception_disambiguation_pattern_vs_icon_statement_l2_s0_exception_exception-p1.png)

**적용 범위 메모**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__inventory_exception_disambiguation_pattern_vs_icon_statement_l2_s0_exception_exception-p2__note_scope-note.png)

**선택 시트**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__inventory_exception_disambiguation_pattern_vs_icon_statement_l2_s0_query_query-p1.png)

### 해설

- L2부터는 두 단계를 모두 거쳐야 합니다.
- 먼저 반례가 `사선 표시`를 버리고 `삼각 표식`을 실제 기준으로 고정합니다.
- 다음으로 메모가 `분석 묶음 아래 행만 선택 대상`이라고 범위를 줄입니다.
- 그래서 정답은 `삼각 표식 기준`과 `분석 묶음 범위`를 동시에 만족하는 설명인 `B`입니다.

### 흔한 오답

- `A`: 여전히 `사선 표시`를 붙잡는 경우입니다.
- `C`나 `D`: 삼각 표식은 맞더라도 묶음 범위를 넓게 잡은 경우가 많습니다.

---

## 7. 재고 예외 판정 L3 · 후보 표 선택

`instance_id`: `public_dev_real_v1__inventory_exception_disambiguation_pattern_vs_icon_statement_l3_s0`  
`정답`: `C`  
`질문`: 사례, 예외, 보조 단서를 함께 반영했을 때 현재 재고표와 맞는 후보 표는 어느 것인가?

### 실제 이미지

**예시 시트**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__inventory_exception_disambiguation_pattern_vs_icon_statement_l3_s0_examples_examples-p1.png)

**예외 확인 표**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__inventory_exception_disambiguation_pattern_vs_icon_statement_l3_s0_exception_exception-p1.png)

**적용 범위 메모**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__inventory_exception_disambiguation_pattern_vs_icon_statement_l3_s0_exception_exception-p2__note_scope-note.png)

**선택 시트**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__inventory_exception_disambiguation_pattern_vs_icon_statement_l3_s0_query_query-p1.png)

### 해설

- 이 문제는 문장 선택이 아니라 `후보 표 자체`를 고르는 형태입니다.
- 예외 확인 표가 `삼각 표식 기준`을 고정하고, 메모가 `운영 묶음 아래 삼각 표식 행만 실제 선택 대상`이라고 범위를 고정합니다.
- query 시트에는 결과 열이 직접 없기 때문에, 네 개의 후보 표 중 이 패턴을 정확히 재현한 것을 골라야 합니다.
- 그 조건을 만족하는 후보가 `C`입니다.

### 흔한 오답

- `A`: 사선 표시 기준을 버리지 못했을 때 고르기 쉽습니다.
- `B`나 `D`: 삼각 표식은 반영했지만 적용 묶음을 너무 넓게 해석한 경우가 많습니다.

---

## 8. 재고 예외 판정 L2 · 창고 변형

`instance_id`: `public_dev_real_v1__inventory_exception_disambiguation_pattern_vs_icon_statement_l2_s1`  
`정답`: `B`  
`질문`: 창고 배치가 달라진 현재 재고표에서 맞는 설명은 어느 것인가?

### 실제 이미지

**예시 시트**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__inventory_exception_disambiguation_pattern_vs_icon_statement_l2_s1_examples_examples-p1.png)

**예외 확인 표**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__inventory_exception_disambiguation_pattern_vs_icon_statement_l2_s1_exception_exception-p1.png)

**적용 범위 메모**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__inventory_exception_disambiguation_pattern_vs_icon_statement_l2_s1_exception_exception-p2__note_scope-note.png)

**선택 시트**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__inventory_exception_disambiguation_pattern_vs_icon_statement_l2_s1_query_query-p1.png)

### 해설

- 규칙은 L2와 같지만 query 쪽 창고 배치가 바뀐 변형입니다.
- 핵심은 여전히 `삼각 표식 기준`과 `운영 묶음 범위`를 동시에 반영하는 것입니다.
- 배치가 바뀌어도 묶음과 표식만 정확히 읽으면 정답은 변하지 않고 `B`입니다.

### 흔한 오답

- 표 배치가 달라졌다는 이유로 예시 시트의 행 위치를 그대로 복사하면 틀립니다.
- 메모를 읽지 않고 `운영 묶음` 바깥 행까지 포함하면 오답이 됩니다.

---

## 9. 보고 범위 판정 L1 · 집계 칸

`instance_id`: `public_dev_real_v1__report_scope_reconciliation_merged_scope_cell_l1_s0`  
`정답`: `B`  
`질문`: 중첩 헤더와 반복된 팀 라벨을 함께 읽으면 찾는 집계 칸은 어디인가?

### 실제 이미지

**보고표 시트**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__report_scope_reconciliation_merged_scope_cell_l1_s0_overview_overview-p1.png)

**선택 시트**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__report_scope_reconciliation_merged_scope_cell_l1_s0_query_query-p1.png)

### 해설

- 목표는 `북부 / 2팀 / 상반기-매출`입니다.
- 이 문제는 지역, 팀, 반기, 항목을 한 번에 맞춰야 합니다.
- `같은 팀 이름`이 지역마다 반복되고, `상반기` 아래에 `매출`과 `마진`이 함께 있으므로 범위를 하나라도 놓치면 틀립니다.
- 네 선택지 중 이 네 조건을 모두 만족하는 것은 `B`뿐입니다.

### 흔한 오답

- `A`: 팀은 맞지만 지역이 다릅니다.
- `C`: 범위는 비슷하지만 `매출` 대신 `마진` 열입니다.
- `D`: 소계 행을 개별 팀 행처럼 읽은 경우입니다.

---

## 10. 보고 범위 판정 L2 · 소계 설명

`instance_id`: `public_dev_real_v1__report_scope_reconciliation_grouped_statement_l2_s0`  
`정답`: `B`  
`질문`: 소계 구간과 보조 메모를 함께 읽으면 맞는 설명은 어느 것인가?

### 실제 이미지

**보고표 시트**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__report_scope_reconciliation_grouped_statement_l2_s0_overview_overview-p1.png)

**기준 메모**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__report_scope_reconciliation_grouped_statement_l2_s0_notes_notes-p1.png)

**선택 시트**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__report_scope_reconciliation_grouped_statement_l2_s0_query_query-p1.png)

### 해설

- 메모가 `각 지역 소계는 같은 지역 3개 팀의 매출만 요약`한다고 분명히 적고 있습니다.
- 따라서 `중부 소계`는 `중부 1팀 + 중부 2팀 + 중부 3팀의 매출`만 포함해야 합니다.
- 다른 지역 팀이나 `마진` 열, `전체 합계`는 이 범위에 들어오지 않습니다.
- 이 설명과 정확히 일치하는 선택지가 `B`입니다.

### 흔한 오답

- `A`: 지역 경계를 무시하고 전체 지역 합으로 읽은 경우입니다.
- `C`: 소계를 바로 위 한 행의 복사처럼 해석한 경우입니다.
- `D`: `전체 합계`와 `지역 소계`를 섞은 경우입니다.

---

## 11. 보고 범위 판정 L3 · 소계 묶음

`instance_id`: `public_dev_real_v1__report_scope_reconciliation_subtotal_row_label_l3_s0`  
`정답`: `A`  
`질문`: 소계 행이 실제로 묶는 팀 조합은 어느 것인가?

### 실제 이미지

**보고표 시트**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__report_scope_reconciliation_subtotal_row_label_l3_s0_overview_overview-p1.png)

**기준 메모**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__report_scope_reconciliation_subtotal_row_label_l3_s0_notes_notes-p1.png)

**선택 시트**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__report_scope_reconciliation_subtotal_row_label_l3_s0_query_query-p1.png)

### 해설

- query에서 묻는 것은 `소계 북부`가 묶는 팀 조합입니다.
- 메모에 `지역 소계는 같은 지역 3개 팀만 묶고, 합계 전체는 세 지역 팀 전체를 묶는다`고 적혀 있습니다.
- 따라서 `소계 북부`는 `북부 1팀 + 2팀 + 3팀`이고, 다른 지역 조합이나 전체 합계는 아닙니다.
- 정답은 `A`입니다.

### 흔한 오답

- `B`나 `C`: 다른 지역 소계를 선택한 경우입니다.
- `D`: `전체 합계`가 묶는 범위를 `지역 소계`로 오해한 경우입니다.

---

## 12. 보고 범위 판정 L1 · 그룹 설명

`instance_id`: `public_dev_real_v1__report_scope_reconciliation_grouped_statement_l1_s0`  
`정답`: `B`  
`질문`: 현재 보고표를 읽었을 때 맞는 그룹 설명은 어느 것인가?

### 실제 이미지

**보고표 시트**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__report_scope_reconciliation_grouped_statement_l1_s0_overview_overview-p1.png)

**선택 시트**

![](../artifacts/notion_explanations/previews_public_dev_real_v1/public_dev_real_v1__report_scope_reconciliation_grouped_statement_l1_s0_query_query-p1.png)

### 해설

- L1 버전은 메모가 없어도 표 자체만 읽어서 소계 경계를 잡을 수 있어야 합니다.
- `중부 소계`는 `중부 지역` 아래 연속된 세 팀을 묶는 행입니다.
- 따라서 설명은 `중부 1팀 + 중부 2팀 + 중부 3팀의 매출만 합친 값`이어야 하고, 이것이 `B`입니다.

### 흔한 오답

- `A`: 지역을 무시하고 전부 더한 경우입니다.
- `C`: 소계를 바로 위 한 행과 혼동한 경우입니다.
- `D`: `전체 합계`와 같은 범위라고 착각한 경우입니다.

---

## 사용 메모

- 이 문서는 실제 preview export 결과를 그대로 참조합니다.
- preview 원본 디렉터리: [artifacts/notion_explanations/previews_public_dev_real_v1](/mnt/c/Users/imssh/Documents/poc_1/artifacts/notion_explanations/previews_public_dev_real_v1)
- 생성 기준 명령:

```bash
uv run python -m table_env_bench.scripts.export_preview_gallery \
  --out artifacts/notion_explanations/previews_public_dev_real_v1 \
  --pack public_dev_real_v1
```
