# Assumptions

- 다음 build pass에서도 렌더링 백엔드는 SVG를 유지한다. 차트, 범례, note overlay도 같은 결정론적 SVG 파이프라인에서 처리한다.
- core benchmark는 계속 offline-first여야 하며, OCR 서비스나 외부 네트워크 호출에 의존하지 않는다.
- 현재 `TableEnv`의 step loop, replay, scorer, FastAPI session API는 재사용하고, workbook abstraction은 그 위에 얹는다.
- benchmark의 장기 정체성은 `Visual TableQA-rooted reasoning`이다. 즉, canonical task는 visually rendered table 또는 worksheet fragment를 핵심 evidence로 유지한다.
- colors, shapes, markers를 쓰더라도 가능하면 cell state, row tag, header cue, filter chip, legend item, note annotation처럼 table semantics 안에 배치한다.
- chart, note, appendix, legend는 보조 evidence로 사용할 수 있지만, canonical task에서 table이 중심을 잃으면 안 된다.
- 초기 workbook refactor는 "기존 table episode를 single-sheet workbook으로 감싸는 방식"으로 시작하는 것이 가장 안전하다.
- benchmark action은 `click_region(x, y)`를 사용하고, 의미적으로는 cell picking이 아니라 region grounding이다.
- note/callout/appendix evidence는 가능하면 page 안에 visible text block으로도 배치해 human mode에서 직접 읽을 수 있게 둔다.
- sheet tab 이름과 page 번호는 시각적으로 보이는 정보이므로 agent observation에 포함해도 leakage로 보지 않는다.
- exact numeric answer는 가능하면 표, 범례, note, appendix에서 얻을 수 있어야 하며, 차트 pixel OCR만으로 풀어야 하는 문제는 피한다.
- 사용자 노출 콘텐츠와 UI는 한국어 기본값을 유지한다. 내부 family id와 action id는 영어를 유지할 수 있다.
- 한국어 answer normalizer는 계속 확장 가능하게 유지하지만, build pass 초반에는 현재 지원 범위인 공백/쉼표/일부 단위 접미어 처리만 보장한다.
- 세션 저장소는 당분간 in-memory여도 괜찮다. 다만 human baseline 수집이 시작되면 replay와 run metadata의 영속 저장이 필요하다.
