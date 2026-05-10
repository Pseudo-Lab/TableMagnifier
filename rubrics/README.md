# Rubrics

이 폴더는 `table-env-bench` family와 episode data를 구현하기 전에 먼저 합의해야 하는 평가 설계도를 둔다.

목표는 한국어 Visual TableQA를 정적 질의응답 데이터셋으로 늘리는 것이 아니라, 한국어 시각 테이블 환경에서 에이전트가 탐색, 규칙 유도, 문서 참조, 계산, 근거 제출을 수행하는 interactive benchmark를 만드는 것이다.

## 작성 순서

새 family나 data template은 다음 순서로 만든다.

1. Rubric 작성
   - 어떤 능력을 평가할지 정의한다.
   - 어떤 sheet/page/surface가 필요한지 정한다.
   - query-only, text-only, document-skip 같은 shortcut을 먼저 적는다.
   - 정답, 근거, 행동 효율, robustness를 어떻게 채점할지 정한다.
2. Family 설계
   - family id, level 범위, template id, latent rule, visual cue, answer form을 확정한다.
   - 각 level에서 늘어나는 complexity 축을 1-2개로 제한한다.
   - required navigation/evidence metadata를 rubric과 맞춘다.
3. Episode 생성
   - deterministic generator로 logical table, visual surface, question program, answer/evidence를 만든다.
   - 원본 CSV, hidden program, oracle metadata가 default observation에 노출되지 않게 한다.
   - 유일해와 distractor 품질을 확인한다.
4. Validation
   - render/readability, workbench traversal, red-team shortcut, regression test를 통과시킨다.
   - 실패한 visual issue는 수동 확인으로 끝내지 않고 gate나 test를 보강한다.

## 공통 평가 축

`FinalScore`는 단일 숫자 정답률만 보지 않는다. v0 rubric은 아래 항목을 기본 축으로 삼는다.

| 항목 | 권장 비중 | 평가 의도 |
| --- | ---: | --- |
| AnswerAccuracy | 0.60 | 최종 답이 맞는가 |
| EvidenceAccuracy | 0.15 | 참조한 셀, 헤더, 문서, 규칙 근거가 맞는가 |
| EfficiencyScore | 0.10 | 행동 수, 시간, 토큰 비용이 합리적인가 |
| RobustnessScore | 0.10 | 같은 논리 문제의 visual variant를 안정적으로 푸는가 |
| CalibrationScore | 0.05 | 불확실하거나 틀릴 때 과신하지 않는가 |

## 공통 실패 조건

아래 조건은 benchmark-ready episode로 보지 않는다.

- 표/문서가 아니라 숨겨진 structured text나 metadata만으로 풀린다.
- query page만 보고 정답을 고를 수 있다.
- 시각 단서 없이 업무 vocabulary나 사전지식만으로 풀린다.
- 사람이 봐도 규칙 후보가 여러 개라 유일해가 없다.
- text overlap, clipping, invalid layout이 있다.
- support sheet/page가 실제 추론에는 필요 없고 클릭 부담만 늘린다.
- distractor가 단순한 랜덤 오답이라 shortcut failure를 진단하지 못한다.

## 현재 Rubric

- [K-VisTable-ARC v0](k_vis_table_arc_v0.md): 현재 canonical family인 `k_vis_table_arc`의 v0 설계와 평가 항목.
