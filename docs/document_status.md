# Document Status

이 문서는 `docs/` 안의 문서가 현재 어떤 역할을 가지는지 정리한다.

목적은 다음과 같다.

- active source-of-truth 문서를 빠르게 찾게 한다
- 중복 문서나 하위 호환용 문서를 `deprecated`로 분리한다
- 앞으로 문서를 추가할 때 어디에 연결해야 하는지 기준을 준다

## 1. Core active docs

아래 문서는 현재 canonical 방향을 설명하는 핵심 문서다.

- [PLANS.md](/mnt/c/Users/imssh/Documents/TableMagnifier/PLANS.md)
- [family_design_brief.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/family_design_brief.md)
- [primitive_glossary.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/primitive_glossary.md)
- [generator_episode_schema.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/generator_episode_schema.md)
- [episode_rulebook.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/episode_rulebook.md)
- [canonical_quality_audit.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/canonical_quality_audit.md)
- [visual_cue_inventory.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/visual_cue_inventory.md)
- [operator_taxonomy.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/operator_taxonomy.md)
- [answer_form_policy.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/answer_form_policy.md)
- [level_design_policy.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/level_design_policy.md)
- [episode_validation_checklist.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/episode_validation_checklist.md)
- [real_data_authoring_policy.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/real_data_authoring_policy.md)
- [domain_vocab_policy.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/domain_vocab_policy.md)
- [human_readability_checklist.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/human_readability_checklist.md)

## 2. Active runtime / interface docs

아래 문서는 현재 구현과 사용법을 설명한다.

- [benchmark_guide.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/benchmark_guide.md)
- [workbook_benchmark_spec.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/workbook_benchmark_spec.md)
- [action_schema.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/action_schema.md)
- [ui_modes.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/ui_modes.md)
- [assumptions.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/assumptions.md)
- [eval_protocol.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/eval_protocol.md)
- [skills/tableqa-family-author/SKILL.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/skills/tableqa-family-author/SKILL.md)

## 3. Active overview docs

아래 문서는 요약/인덱스 역할을 한다.

- [first_steps.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/first_steps.md)
- [task_families.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/task_families.md)

주의:

- overview 문서는 source-of-truth가 아니다
- 세부 규칙은 family/rule/policy 문서를 우선한다

## 4. Historical / deprecated docs

### [benchmark_spec.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/benchmark_spec.md)

상태:

- deprecated

이유:

- 현재 내용이 매우 얇은 compatibility pointer 역할에 가깝다
- 실질적인 환경/렌더러 source-of-truth는 [workbook_benchmark_spec.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/workbook_benchmark_spec.md)다
- content direction은 family/rule/policy 문서 세트가 더 정확하게 설명한다

대신 볼 문서:

- [workbook_benchmark_spec.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/workbook_benchmark_spec.md)
- [family_design_brief.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/family_design_brief.md)
- [episode_rulebook.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/episode_rulebook.md)

### pilot 문서 세트

- [pilot_family_episode_grammar.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/pilot_family_episode_grammar.md)
- [pilot_episode_drafts.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/pilot_episode_drafts.md)
- [pilot_implementation_strategy.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/pilot_implementation_strategy.md)

상태:

- historical design archive

이유:

- 현재 active benchmark는 `canonical_real_tableqa`와 generated benchmark suite catalog를 기준으로 운영한다
- pilot 문서 세트는 초창기 설계 reasoning을 보존하지만, 현재 runtime / generated suite / release gate의 source-of-truth는 아니다

대신 볼 문서:

- [benchmark_guide.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/benchmark_guide.md)
- [task_families.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/task_families.md)
- [real_data_authoring_policy.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/real_data_authoring_policy.md)

## 5. 문서 추가 규칙

새 문서를 추가할 때는 아래를 지킨다.

- family 설계 문서인지, runtime spec인지, overview인지 먼저 분류한다
- `document_status.md`에 상태를 추가한다
- source-of-truth가 여러 개 생기지 않게 한다
- 얇은 redirect 문서를 또 만들기보다 기존 문서에 섹션을 추가하는 쪽을 우선 고려한다
