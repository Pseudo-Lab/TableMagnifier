# Real Data Authoring Policy

canonical family와 frozen pack은 `사람이 읽어도 바로 이해되는 실제 업무형 합성 표`를 기준으로 만든다.

## 기본 원칙

- workbook title, sheet title, question은 업무 문맥이 드러나야 한다.
- 예시/보조 메모/예외 시트는 실제로 해석을 좁히는 역할을 해야 한다.
- 정답 구조는 deterministic하게 유지하되, 표의 겉모습은 실제 보고서나 운영표처럼 읽혀야 한다.
- 내부 개발 용어를 human-visible copy에 남기지 않는다.

## 금지 어휘

아래 표현은 canonical human-visible copy에 넣지 않는다.

- `query`
- `target cell`
- `hybrid`
- `appendix cue`
- `legacy`
- `pilot`
- `counterexample`
- `review`

## Copy Budget

- sheet/page title은 짧고 명확하게 쓴다.
- note title은 12자 안팎으로 유지한다.
- question은 한 문장으로 끝내고, 두 개 이상의 조건절을 겹치지 않는다.
- row/column label은 한눈에 구분되는 실무 명사로 제한한다.

## Freeze Rule

- frozen instance는 `question`, `workbook title`, `instance label` 정도만 polish한다.
- family topology, answer contract, required evidence, layout 구조는 source episode와 맞아야 한다.
