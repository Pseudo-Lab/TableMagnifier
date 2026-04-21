# Episode Validation Checklist

이 문서는 새 canonical episode 초안이나 generator output이 benchmark-safe한지 확인하는 체크리스트다.

목표는 다음과 같다.

- 구현 전에 text-only solvability와 level misfit을 걸러낸다
- distractor 품질과 leakage 문제를 조기에 잡는다
- deterministic benchmark로서 필요한 조건을 유지한다

## 1. identity check

- visually rendered table 또는 worksheet fragment가 핵심 evidence인가?
- chart, note, legend는 보조 surface인가?
- pure abstract puzzle처럼 표 의미가 사라지지 않았는가?

## 2. visual grounding check

- non-text visual cue가 실제로 정답 결정에 필요한가?
- cue를 제거하면 문제의 핵심 reasoning이 무너지는가?
- cue가 장식이 아니라 scope / grouping / mapping / order를 바꾸는가?

## 3. text-only solvability check

- row/column label만 읽어도 정답이 보이지 않는가?
- note text만 읽어서 정답을 확정할 수 없는가?
- 숫자만 OCR 해서 제출하는 문제가 아닌가?

실무적으로는 아래 질문을 쓴다.

- merged header 정보를 무시하면 still solvable 한가?
- marker 위치/패턴을 무시하면 still solvable 한가?
- chart/note attachment geometry를 무시하면 still solvable 한가?

하나라도 "예"가 많으면 설계를 다시 본다.

## 4. operator check

- primary operator가 무엇인지 한 줄로 설명 가능한가?
- support operator가 정말 필요한가?
- aggregate 하나로 설명되는 문제로 축소되지 않는가?

## 5. answer-form check

- answer form이 operator와 자연스럽게 맞는가?
- answer form이 지나치게 free-form이라 채점이 불안정하지 않은가?
- distractor가 실제 failure mode를 반영하는가?

## 6. level-fit check

- Level 1이면 2-3 reasoning steps 안에 설명 가능한가?
- Level 2이면 3-4 steps 수준인가?
- Level 3이면 4-5 steps와 answer indirection 또는 stronger disambiguation이 있는가?
- 같은 family의 adjacent level과 차이가 분명한가?

## 7. distractor quality check

- 오답 choice마다 어떤 failure mode를 반영하는지 설명 가능한가?
- random distractor가 아니라 plausible wrong rule인가?
- 정답이 시각적으로 너무 튀지 않는가?

## 8. leakage check

- hidden cell id, debug label, oracle metadata가 human/agent view로 새지 않는가?
- answer canonical이 시각적으로 암시되지 않는가?
- generator-only metadata가 render payload에 남지 않는가?

## 9. deterministic generation check

- seed가 같으면 같은 layout / numbers / cue placement가 나오나?
- seed가 달라도 family identity가 유지되나?
- preview export와 runtime render가 같은 geometry를 쓰나?

## 10. human-play check

- 사람이 UI에서 실제로 볼 때 cue가 읽히는가?
- 줌 없이도 Level 1 cue가 인지 가능한가?
- 지나친 clutter 없이 relevant evidence를 찾을 수 있는가?

## 11. visual readability / zero-overlap check

- text block, callout, note, overlay note의 title/subtitle/body text가 자기 박스 안에 완전히 들어가는가?
- table title/subtitle가 table body 또는 다른 상단 element와 겹치지 않는가?
- table cell text가 padded cell bounds 안에 들어가는가?
- renderer debug payload 기준 `invalidLayout == false`, `layoutErrors == []` 인가?

이 항목은 UX polish가 아니라 benchmark integrity requirement다. 글자가 겹치거나 잘리면 episode는 invalid surface로 본다.

## 12. pass 기준

아래 조건을 모두 만족하면 일단 합격으로 본다.

- identity check 통과
- visual grounding check 통과
- text-only solvability check 통과
- level-fit check 통과
- distractor quality check 통과
- leakage check 통과
- deterministic generation check 통과
- visual readability / zero-overlap check 통과

## 13. 권장 워크플로

1. episode draft 작성
2. 이 체크리스트로 문서 점검
3. preview export 확인
4. full-seed readability audit 확인
5. human mode에서 1회 플레이
6. 필요하면 level 재조정
