# Document Status

이 문서는 `docs/` 안의 문서가 현재 어떤 역할을 가지는지 정리한다.

목적은 다음과 같다.

- active source-of-truth 문서를 빠르게 찾게 한다
- 중복 문서나 하위 호환용 문서를 `deprecated`로 분리한다
- 앞으로 문서를 추가할 때 어디에 연결해야 하는지 기준을 준다

## 1. Core active docs

아래 문서는 현재 canonical 방향을 설명하는 핵심 문서다.

- [PLANS.md](../PLANS.md)
- [primitive_glossary.md](./primitive_glossary.md)
- [episode_rulebook.md](./episode_rulebook.md)
- [visual_cue_inventory.md](./visual_cue_inventory.md)
- [operator_taxonomy.md](./operator_taxonomy.md)
- [answer_form_policy.md](./answer_form_policy.md)
- [episode_validation_checklist.md](./episode_validation_checklist.md)
- [real_data_authoring_policy.md](./real_data_authoring_policy.md)
- [domain_vocab_policy.md](./domain_vocab_policy.md)
- [human_readability_checklist.md](./human_readability_checklist.md)

## 2. Active runtime / interface docs

아래 문서는 현재 구현과 사용법을 설명한다.

- [benchmark_guide.md](./benchmark_guide.md)
- [workbook_benchmark_spec.md](./workbook_benchmark_spec.md)
- [action_schema.md](./action_schema.md)
- [ui_modes.md](./ui_modes.md)
- [assumptions.md](./assumptions.md)
- [eval_protocol.md](./eval_protocol.md)
- [skills/tableqa-family-author/SKILL.md](./skills/tableqa-family-author/SKILL.md)

## 3. Active overview docs

아래 문서는 요약/인덱스 역할을 한다.

- [first_steps.md](./first_steps.md)
- [task_families.md](./task_families.md)

주의:

- overview 문서는 source-of-truth가 아니다
- 세부 규칙은 family/rule/policy 문서를 우선한다

## 4. Historical / deprecated docs

### [benchmark_spec.md](./benchmark_spec.md)

상태:

- deprecated

이유:

- 현재 내용이 매우 얇은 compatibility pointer 역할에 가깝다
- 실질적인 환경/렌더러 source-of-truth는 [workbook_benchmark_spec.md](./workbook_benchmark_spec.md)다
- content direction은 family/rule/policy 문서 세트가 더 정확하게 설명한다

대신 볼 문서:

- [workbook_benchmark_spec.md](./workbook_benchmark_spec.md)
- [task_families.md](./task_families.md)
- [episode_rulebook.md](./episode_rulebook.md)

### 과거 pilot 설계 메모

상태:

- `PLANS.md` 내부의 과거 계획/마일스톤 기록으로만 유지

이유:

- 현재 active benchmark는 `korean_visual_table_agent_reasoning` track의 `k_vis_table_arc` generator family와 `canonical_dev` generated suite catalog를 기준으로 운영한다.
- 별도 pilot 문서 파일은 현재 repo에 남아 있지 않으며, runtime / generated suite / release gate의 source-of-truth가 아니다.

대신 볼 문서:

- [benchmark_guide.md](./benchmark_guide.md)
- [task_families.md](./task_families.md)
- [real_data_authoring_policy.md](./real_data_authoring_policy.md)

## 5. 문서 추가 규칙

새 문서를 추가할 때는 아래를 지킨다.

- family 설계 문서인지, runtime spec인지, overview인지 먼저 분류한다
- `document_status.md`에 상태를 추가한다
- source-of-truth가 여러 개 생기지 않게 한다
- 얇은 redirect 문서를 또 만들기보다 기존 문서에 섹션을 추가하는 쪽을 우선 고려한다
