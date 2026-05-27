# Human Readability Checklist

canonical surface를 freeze하기 전에 아래 항목을 모두 통과해야 한다.

## Viewport

- 글자 겹침이 없다.
- 제목과 표 본문이 닿지 않는다.
- note/callout이 박스를 넘지 않는다.
- answer card와 choice table이 서로 겹치지 않는다.

## Copy

- workbook title만 읽어도 무슨 표인지 감이 온다.
- question이 한 번에 이해된다.
- `query`, `target cell`, `legacy`, `pilot`, `review`, `counterexample` 같은 내부 용어가 없다.
- row/column label이 같은 화면 안에서 일관된다.

## Reasoning

- 여러 시트/페이지를 보는 이유가 실제로 있다.
- 표의 시각 구조를 읽지 않으면 풀 수 없다.
- distractor가 겉보기만 비슷한 수준이 아니라, 잘못된 범위 해석을 유도한다.

## Freeze

- `invalidLayout == false`
- `layoutErrors == []`
- strict readability audit 통과
- static preview artifact 검증 통과
