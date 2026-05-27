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
- `marker_position_rule_transfer`에서는 삼각형의 모양만 보고 anchor 위치를 무시해도 풀리는가?

하나라도 "예"가 많으면 설계를 다시 본다.

## 4. operator check

- primary operator가 무엇인지 한 줄로 설명 가능한가?
- support operator가 정말 필요한가?
- aggregate 하나로 설명되는 문제로 축소되지 않는가?

## 5. answer-form check

- answer form이 operator와 자연스럽게 맞는가?
- answer form이 지나치게 free-form이라 채점이 불안정하지 않은가?
- distractor가 실제 failure mode를 반영하는가?
- 정답 선택지 ID 제출을 허용하는 value choice에서는 표시값이 서로 중복되지 않는가?

## 6. level-fit check

- Level 1이면 2-3 reasoning steps 안에 설명 가능한가?
- Level 2이면 3-4 steps 수준인가?
- Level 3이면 4-5 steps와 answer indirection 또는 stronger disambiguation이 있는가?
- 같은 family의 adjacent level과 차이가 분명한가?

## 7. distractor quality check

- 오답 choice마다 어떤 failure mode를 반영하는지 설명 가능한가?
- random distractor가 아니라 plausible wrong rule인가?
- 정답이 시각적으로 너무 튀지 않는가?
- 선택지에는 option ID와 제출값만 노출되고, distractor 생성 이유나 내부 라벨이 보이지 않는가?

## 8. leakage check

- hidden cell id, debug label, oracle metadata가 human/agent view로 새지 않는가?
- answer canonical이 시각적으로 암시되지 않는가?
- `marker_position_rule_transfer`의 query/note 문구가 decisive anchor label을 직접 정답으로 말하지 않는가?
- 같은 family/level의 seed들이 하나의 answer choice label만 반복하지 않는가?
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

## 12. navigation contract check

sheet/page/viewport 이동이 reasoning의 일부라면 아래를 확인한다.

- `required_navigation.required_sheet_ids`와 `required_page_refs`가 decisive surface를 모두 포함하는가?
- pan/zoom이 필요한 episode는 `required_navigation.required_viewport_states`를 가지는가?
- viewport state는 `sheet_id`, `page_id`, `min_zoom_index`, `required_action_types`, `match`, `target_rects`를 명시하는가?
- `target_center_in_viewbox`와 `viewbox_intersects_target` 중 어떤 match mode를 쓰는지 명확한가?
- `forbidden_shortcuts`가 `initial_viewport_only`, `no_pan_zoom`, `sheet_skip` 같은 generic navigation shortcut을 표현하는가?
- replay metrics와 static validation metadata가 같은 required viewport state id를 보고하는가?

## 13. pass 기준

아래 조건을 모두 만족하면 일단 합격으로 본다.

- identity check 통과
- visual grounding check 통과
- text-only solvability check 통과
- level-fit check 통과
- distractor quality check 통과
- leakage check 통과
- deterministic generation check 통과
- visual readability / zero-overlap check 통과
- navigation contract check 통과

## 13A. marker-position probe 기준

`marker_position_rule_transfer` episode는 아래 shortcut probe를 우선 확인한다.

- query-only probe는 Level 2/3 평균 correctness가 0.25 미만이어야 한다.
- text-scrape probe는 모든 level에서 평균 correctness가 0.50 미만이어야 한다.
- marker-presence-only probe는 모든 level에서 평균 correctness가 0.50 미만이어야 한다.
- legend-skip probe는 모든 level에서 평균 correctness가 0.25 미만이어야 한다.
- exception-skip probe는 Level 2/3 평균 correctness가 0.25 미만이어야 한다.
- note-skip probe는 Level 3 평균 correctness가 0.25 미만이어야 한다.
- base answer label은 checked seed에서 최소 2개 이상 나타나야 한다.

## 13B. viewport-navigation probe 기준

`excel_viewport_sheet_navigation` episode는 아래 shortcut probe를 우선 확인한다.

- initial-viewport-only probe는 target column을 보지 못해야 한다.
- no-pan-zoom probe는 required viewport state를 방문하지 못해야 한다.
- sheet-skip probe는 examples/operators surface를 생략하므로 required evidence를 충족하지 못해야 한다.
- replay와 static navigation validation은 `query-right-target` 같은 required viewport state id를 동일하게 기록해야 한다.

## 14. 권장 워크플로

1. episode draft 작성
2. 이 체크리스트로 문서 점검
3. preview export 확인
4. full-seed readability audit 확인
5. human mode에서 1회 플레이
6. 필요하면 level 재조정
