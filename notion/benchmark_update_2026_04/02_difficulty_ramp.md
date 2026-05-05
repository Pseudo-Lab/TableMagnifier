# Canonical Difficulty Ramp 정리

## 핵심 방향

이번 난이도 상향의 목적은 "더 많은 클릭"이 아니라 "더 많은 reasoning pressure"를 만드는 것이었다.

난이도를 올릴 때 다음 기준을 고정했다.

- 여러 sheet/page가 실제로 필요해야 한다
- decisive evidence가 2개 이상인 episode를 늘린다
- wrong rule을 버리지 않으면 못 푸는 counterexample pressure를 강화한다
- text scrape만으로는 안 풀리도록 visual cue 의존성을 유지한다
- level이 올라갈수록 scope, order, exception 처리 부담을 올린다

## 메타데이터 확장

이번에 canonical/eval_hard manifest에 더 강하게 채운 항목은 다음과 같다.

- `required_sheet_ids`
- `required_page_refs`
- `required_actions`
- `required_evidence`
- `required_visual_cues`
- `shortcut_probes`
- `expected_reasoning_steps`

이 정보는 catalog, benchmark suite record, episode metadata까지 전파된다.

## family별 강화 포인트

### `channel_policy_transfer`

- Level 2부터 example 보강 페이지를 필수 evidence로 취급
- Level 3에서는 appendix note가 실제 rule 확정에 필요
- 막으려는 shortcut:
  - 첫 example만 읽고 바로 전이
  - band scope 무시
  - icon만 단순 매칭

![channel_policy_transfer](assets/channel_policy_transfer_l3_query.png)

### `inventory_exception_disambiguation`

- counterexample sheet를 optional 참고 자료가 아니라 wrong rule 제거 장치로 명시
- Level 2 이상에서는 추가 counterexample page나 note가 없으면 규칙이 충분히 고정되지 않게 유지
- 막으려는 shortcut:
  - single-page submit
  - counterexample 무시
  - text-only guess

![inventory_exception_disambiguation](assets/inventory_exception_disambiguation_l3_counterexample.png)

### `report_scope_reconciliation`

- merged header, indentation, subtotal boundary를 결합 cue로 다룸
- Level 2 이상에서는 notes sheet가 범위 확정 근거가 되도록 강화
- 막으려는 shortcut:
  - hierarchy 무시
  - subtotal row를 데이터 row로 오인

![report_scope_reconciliation](assets/report_scope_reconciliation_l3_overview.png)

### `legend_operator_composition`

- legend mapping과 worked example을 분리
- operator order를 따로 읽지 않으면 query 해석이 흔들리게 설계
- `legend_statement`는 note-card 성격의 operator order 해석이 핵심
- 막으려는 shortcut:
  - operator order 무시
  - query table만 보고 포함/제외를 추정

![legend_operator_composition](assets/legend_operator_composition_l3_legend.png)

## `eval_hard`에서의 의미

`eval_hard`는 canonical보다 한 단계 더 강하게 다음을 요구한다.

- decisive evidence를 여러 surface에서 읽기
- premature submit이 명확히 불이익을 받기
- counterfactual pair를 안정적으로 구분하기
- restricted baseline이 낮은 evidence coverage를 보이기

즉, `eval_hard`는 단순 정확도보다 "제대로 읽었는가"를 더 강하게 드러내는 트랙이다.
