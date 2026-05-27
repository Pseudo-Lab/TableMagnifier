# Skills

이 저장소에서 benchmark family와 episode data를 추가할 때는 rule-doc-first 흐름을 따른다.

주요 authoring skill:

- [TableQA Family Author](docs/skills/tableqa-family-author/SKILL.md)

작업 순서:

1. `docs/episode_rulebook.md`, `docs/visual_cue_inventory.md`, `docs/operator_taxonomy.md`, `docs/answer_form_policy.md`, `docs/episode_validation_checklist.md`에서 capability, evidence path, shortcut probe, answer form을 먼저 정리한다.
2. rule docs와 Template Spec Card를 기준으로 family/template을 하나씩 구현한다.
3. 구현 metadata의 `required_sheet_ids`, `required_page_refs`, `required_navigation`, `required_evidence`가 문서화된 evidence path와 일치하는지 테스트한다.
4. static render/readability, red-team shortcut, regression 검증을 통과시킨다.

현재 기준 family:

- `k_vis_table_arc`
