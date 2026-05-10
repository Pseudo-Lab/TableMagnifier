# table-env-bench 벤치마크 가이드

`table-env-bench`는 한국어 시각 테이블 환경에서 에이전트가 탐색, 규칙 유도, 문서 참조, 계산을 수행하는 interactive benchmark다.

현재 canonical track은 `korean_visual_table_agent_reasoning`이며, 기본 family는 `k_vis_table_arc` 하나다. 기존 정적 한국어 TableQA와 차별점은 한국어 표면 자체가 아니라 visual layout, 제한된 viewport, action feedback, hidden rule discovery, evidence-aware evaluation에 있다.

## 현재 노출 경로

현재 repo는 frozen `public_*` instance pack을 포함하지 않는다.
workbench와 API의 기본 노출 경로는 generator family catalog이며, hidden holdout은 별도 instance pack으로 같은 loader 경로를 통해 읽는다.

## 현재 Family

- `k_vis_table_arc`
  - 특수 기호 규칙 유도
  - merged cell/header scope 이해
  - 합성 약어 문서 참조
  - 50+ column wide table 탐색 계산

이전 family는 canonical registry와 UI/API 노출 경로에서 제거했다.

## 무엇을 측정하나

- rendered table/document viewport에서 relevant evidence를 찾는 능력
- 표 구조, 병합 헤더, 기호 위치, 약어 문서, 단위 문구를 함께 읽는 능력
- 여러 시트와 페이지에 흩어진 evidence를 합쳐 hidden rule을 유도하는 능력
- 넓은 표에서 scroll/pan/zoom 중 위치를 기억하고 정확한 셀을 찾는 능력
- 정답률뿐 아니라 action efficiency와 evidence coverage를 함께 만족하는 능력

권장 headline metric:

```text
FinalScore =
  0.60 * AnswerAccuracy
+ 0.15 * EvidenceAccuracy
+ 0.10 * EfficiencyScore
+ 0.10 * RobustnessScore
+ 0.05 * CalibrationScore
```

## Integrity Rules

- 모든 canonical surface는 zero-overlap이어야 한다.
- `invalidLayout == false`, `layoutErrors == []`가 기본 기준이다.
- 에이전트에게 원본 CSV, 구조화 HTML, hidden logical table을 default observation으로 제공하지 않는다.
- 합성 약어와 기호 규칙은 episode-local이어야 하며 사전지식으로 풀리지 않아야 한다.
- 기호 규칙 유형은 uniqueness checker를 통과해야 한다.

## 빠르게 실행해 보기

```bash
uv run pytest
uv run python -m table_env_bench.scripts.audit_readability --smoke --seed-samples 0
uv run python -m table_env_bench.scripts.eval_baselines --suite canonical_dev
```
