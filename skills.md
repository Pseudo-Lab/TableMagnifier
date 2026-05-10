# Skills

이 저장소에서 benchmark family와 episode data를 추가할 때는 rubric-first 흐름을 따른다.

주요 authoring skill:

- [TableQA Family Author](docs/skills/tableqa-family-author/SKILL.md)

작업 순서:

1. `rubrics/`에서 평가 설계도를 먼저 작성하거나 갱신한다.
2. rubric의 capability, evidence path, shortcut probe, scoring axis를 기준으로 family/template을 하나씩 구현한다.
3. 구현 metadata의 `required_sheet_ids`, `required_page_refs`, `required_navigation`, `required_evidence`가 rubric과 일치하는지 테스트한다.
4. render/readability와 workbench traversal 검증을 통과시킨다.

현재 기준 rubric:

- [K-VisTable-ARC v0](rubrics/k_vis_table_arc_v0.md)
