# ABC Generator Scaffold for Visual TableQA Families

이 문서는 특정 template 하나를 고정 구현하기 위한 명세가 아니라, **새로운 Visual TableQA template을 빠르게 정의하고 코딩 에이전트가 바로 generator를 구현할 수 있게 하는 공통 생성 프레임워크**다.

`abc-template.md`가 “template 명세 작성 양식”이라면, 이 문서는 “그 명세를 실제 생성기 구조로 옮기는 방식”을 정의한다.

목표는 다음과 같다.

1. 새로운 template을 만들 때 빈칸만 채우면 된다.
2. 코딩 에이전트가 template별 구현 파일을 일관된 방식으로 만들 수 있다.
3. 너무 구체적인 예제 복제가 아니라, seed 기반으로 다양한 instance를 생성한다.
4. hidden program, distractor, evidence path, validation, render safety가 모두 자동화된다.
5. 모든 template이 같은 family 계약과 renderer 계약을 따른다.

---

## 0. 핵심 아이디어

각 template은 다음 세 층으로 나눈다.

```text
Template Idea
  ↓
Template Spec Card
  ↓
Template Generator Module
  ↓
Generated Workbook Instance
```

### 0.1 Template Idea

사람이 한두 문장으로 쓰는 문제 의도다.

예:

```text
표 안의 raw value를 별도 문서의 단위 규칙과 상태 예외에 따라 변환해 최종 금액을 계산한다.
```

### 0.2 Template Spec Card

코딩 에이전트가 generator를 만들 수 있을 정도로 구조화한 카드다.

예:

```yaml
template_id: cross_sheet_unit_note
primary_operator: unit_conversion
support_operators:
  - document_lookup
  - conditional_adjustment
required_evidence:
  - main_table
  - unit_note
  - status_rule
hidden_program_shape: lookup -> convert unit -> apply adjustment -> round
shortcut_traps:
  - unit_skip
  - document_skip
  - wrong_status
  - exception_skip
```

### 0.3 Template Generator Module

실제 코드 구조다. 모든 template은 같은 interface를 구현한다.

```text
manifest
sampleParams(seed_slot, level)
buildWorkbook(params)
solve(params)
buildChoices(answer, params)
buildMetadata(params, answer, choices)
validate(instance)
```

### 0.4 Generated Workbook Instance

렌더러가 사용하는 최종 데이터다.

```text
workbook
query
choices
gold
metadata_extra
validation
```

---

## 1. 권장 디렉터리 구조

코딩 에이전트는 가능하면 다음 구조를 따른다. 기존 repo 구조가 다르면 이름만 맞춰서 조정한다.

```text
src/
  generators/
    core/
      rng.ts
      types.ts
      workbook.ts
      table.ts
      documents.ts
      choices.ts
      distractors.ts
      validation.ts
      evidence.ts
      render-safety.ts
      audit.ts

    families/
      k_vis_table_arc/
        family-manifest.ts
        family-types.ts
        family-validation.ts
        shared-visuals.ts
        shared-distractors.ts

        templates/
          abbrev_doc_reference.ts
          symbol_rule_induction.ts
          cross_sheet_unit_note.ts
          merged_header_delta.ts
          document_filter_rank.ts
          __template_stub.ts

        index.ts

  frontend/
    components/
      sample-viewer.tsx
      evidence-table.tsx
      answer-choice-grid.tsx
```

### 1.1 Core와 template의 역할 분리

Core는 template에 종속되지 않는다.

| 파일 | 역할 |
| --- | --- |
| `rng.ts` | deterministic random helper |
| `types.ts` | 공통 generator type |
| `workbook.ts` | sheet/page/element 생성 helper |
| `table.ts` | table geometry, row, cell 생성 helper |
| `documents.ts` | note/glossary/document block helper |
| `choices.ts` | answer choice formatting/shuffling |
| `distractors.ts` | distractor uniqueness/checking |
| `validation.ts` | structural/evidence/answer validation |
| `evidence.ts` | gold evidence path builder |
| `render-safety.ts` | forbidden visible metadata 검사 |
| `audit.ts` | 전체 sample/template audit |

Template 파일은 reasoning과 content generation만 담당한다.

---

## 2. 공통 Generator Interface

모든 template은 아래 개념의 interface를 구현해야 한다. TypeScript repo라면 실제 type으로 만든다.

```ts
export type TemplateGenerator<Params = unknown> = {
  manifest: TemplateManifest;

  sampleParams(input: {
    seed_slot: number;
    level: number;
    family_id: string;
  }): Params;

  buildWorkbook(params: Params): Workbook;

  solve(params: Params): GoldAnswer;

  buildChoices(input: {
    params: Params;
    answer: GoldAnswer;
    rng: RandomLike;
  }): AnswerChoice[];

  buildMetadata(input: {
    params: Params;
    answer: GoldAnswer;
    choices: AnswerChoice[];
    workbook: Workbook;
  }): MetadataExtra;

  validate(input: {
    params: Params;
    workbook: Workbook;
    answer: GoldAnswer;
    choices: AnswerChoice[];
    metadata: MetadataExtra;
  }): ValidationResult;
};
```

### 2.1 Instance 생성 흐름

```ts
export function generateInstance(template, input) {
  const params = template.sampleParams(input);
  const workbook = template.buildWorkbook(params);
  const answer = template.solve(params);
  const choices = template.buildChoices({ params, answer, rng });
  const metadata = template.buildMetadata({ params, answer, choices, workbook });
  const validation = template.validate({ params, workbook, answer, choices, metadata });

  return {
    family_id: input.family_id,
    template_id: template.manifest.template_id,
    level: input.level,
    seed_slot: input.seed_slot,
    workbook,
    query: params.query,
    choices,
    gold: answer,
    metadata_extra: metadata,
    validation
  };
}
```

---

## 3. Template Spec Card: 빠른 작성 양식

새 template을 추가할 때 먼저 이 카드만 채운다. 이 카드는 full spec보다 짧고, coding agent가 첫 구현을 시작하기에 충분해야 한다.

```yaml
template_id: ""
template_label: ""
family_id: "k_vis_table_arc"

intent: |
  이 template이 평가하는 능력을 2~4문장으로 설명한다.
  실제 세계 지식이 아니라 workbook 내부 evidence를 사용해야 함을 명시한다.

answer_form: "number | choice_id | text | cell_value | row_label"

primary_operator: ""
support_operators:
  - ""
  - ""

capability_axes:
  - table_lookup
  - document_reference
  - calculation

required_evidence:
  main:
    role: ""
    decisive: true
  document:
    role: ""
    decisive: true
  query:
    role: ""
    decisive: true
  exception:
    role: ""
    decisive_levels: [3]

sheets:
  - sheet_id: main
    tab_label: ""
    role: main
  - sheet_id: query
    tab_label: "질의"
    role: query

level_progression:
  1: ""
  2: ""
  3: ""

hidden_program_shape: |
  Human-readable calculation or reasoning shape.

pseudo_code: |
  answer = ...

seed_variables:
  decisive:
    - name: ""
      range: ""
      visible_in: ""
      used_in_answer: true
  visible_unused:
    - name: ""
      range: ""
      visible_in: ""
      used_in_answer: false
  distractor:
    - name: ""
      purpose: ""

shortcut_traps:
  - trap_id: document_skip
    description: ""
  - trap_id: unit_skip
    description: ""

variation_axes:
  - axis: entity_labels
    allowed_variation: ""
    invariant: ""
  - axis: table_size
    allowed_variation: ""
    invariant: ""
  - axis: document_wording
    allowed_variation: ""
    invariant: ""

choice_distractors:
  - trap: ""
    derivation: ""
  - trap: ""
    derivation: ""

validation_rules:
  - ""
  - ""

forbidden_visible_metadata:
  - candidate
  - distractor
  - rationale
  - debug
  - generation
  - 검산 후보
  - 표 단서 적용 후보
  - 문서 단서 적용 후보
  - 단위 확인 후보
```

---

## 4. Full Generator Authoring Form

Template Spec Card를 작성한 뒤, coding agent는 아래 항목을 채워 실제 generator를 만든다.

## 4.1 Manifest

```ts
export const manifest = {
  family_id: "k_vis_table_arc",
  template_id: "",
  template_label: "",
  answer_form: "number",
  primary_operator: "",
  support_operators: [],
  capability_axes: [],
  cue_tags: [],
  required_sheet_ids: [],
  required_page_refs_by_level: {
    1: [],
    2: [],
    3: []
  },
  level_count: 3,
  supports_multiple_choice: true
};
```

## 4.2 Params Type

```ts
export type TemplateParams = {
  seed_slot: number;
  level: 1 | 2 | 3;

  query: {
    text: string;
    answer_format: string;
  };

  target: {
    id: string;
    label: string;
  };

  decisive: Record<string, number | string | boolean>;
  visible_unused: Record<string, number | string | boolean>;
  distractor_context: Record<string, unknown>;

  visual: {
    row_order: string[];
    column_order: string[];
    emphasis: Record<string, string>;
  };
};
```

## 4.3 sampleParams

`sampleParams`는 seed와 level을 받아 모든 변수를 deterministic하게 만든다.

```ts
export function sampleParams({ seed_slot, level }) {
  const rng = makeRng(seed_slot + TEMPLATE_OFFSET + level);

  const target = sampleTarget(rng);
  const decisive = sampleDecisiveVars(rng, level);
  const visible_unused = sampleVisibleUnusedVars(rng, level);
  const distractor_context = sampleDistractorContext(rng, target, decisive, level);
  const visual = sampleVisualVars(rng, level);
  const query = buildQuestion({ target, decisive, level, rng });

  return {
    seed_slot,
    level,
    target,
    decisive,
    visible_unused,
    distractor_context,
    visual,
    query
  };
}
```

## 4.4 buildWorkbook

`buildWorkbook`는 화면에 보이는 workbook만 만든다. 정답이나 distractor derivation을 visible text로 넣으면 안 된다.

```ts
export function buildWorkbook(params) {
  return workbook({
    sheets: [
      buildMainSheet(params),
      buildReferenceSheet(params),
      buildQuerySheet(params)
    ]
  });
}
```

### Workbook 생성 원칙

- decisive value는 반드시 visible evidence에 있어야 한다.
- visible-but-unused value는 산식에는 쓰지 않지만 화면에는 자연스럽게 있어야 한다.
- target과 distractor entity가 모두 있어야 한다.
- document/reference가 필요한 template에서는 해당 문서가 반드시 존재해야 한다.
- Level 3 exception이 decisive하면 exception page/note가 반드시 visible해야 한다.

## 4.5 solve

`solve`는 오직 params만 사용해 answer를 계산한다.

```ts
export function solve(params) {
  const { decisive, level } = params;

  // hidden program here
  const answer = computeAnswer(decisive, level);

  return {
    value: answer,
    display_value: formatAnswer(answer),
    answer_form: manifest.answer_form
  };
}
```

## 4.6 buildChoices

`buildChoices`는 정답과 distractor를 만든다.

```ts
export function buildChoices({ params, answer, rng }) {
  const distractors = [
    deriveDistractor(params, "unit_skip"),
    deriveDistractor(params, "wrong_row"),
    deriveDistractor(params, "ignore_exception")
  ];

  return buildMultipleChoiceSet({
    answer,
    distractors,
    rng,
    optionIds: ["A", "B", "C", "D"]
  });
}
```

### Choice visible text rule

Visible answer choice에는 다음만 들어간다.

```text
A · 38원
B · 35원
C · 45원
D · 52원
```

다음은 절대 visible text로 넣지 않는다.

```text
unit_skip
wrong_row
검산 후보
표 단서 적용 후보
distractor
candidate
rationale
```

## 4.7 buildMetadata

`buildMetadata`는 분석과 검증을 위한 정보를 기록한다. 렌더링 UI에는 노출하지 않는다.

```ts
export function buildMetadata({ params, answer, choices, workbook }) {
  return {
    decisive_variables: params.decisive,
    visible_unused_variables: params.visible_unused,
    shortcut_traps: manifest.shortcut_traps,
    distractor_derivations: getDistractorDerivations(choices),
    gold_evidence_path: buildGoldEvidencePath(params, workbook),
    hidden_program: {
      text: "Human-readable hidden program",
      pseudo_code: "answer = ..."
    }
  };
}
```

## 4.8 validate

`validate`는 생성된 instance가 문제로서 유효한지 확인한다.

```ts
export function validate({ params, workbook, answer, choices, metadata }) {
  return combineValidationResults([
    validateStructure(workbook),
    validateEvidenceVisibility(workbook, metadata.gold_evidence_path),
    validateAnswer(params, answer),
    validateChoices(answer, choices),
    validateDistractors(answer, choices, metadata.distractor_derivations),
    validateShortcutTraps(params, answer, choices, metadata.shortcut_traps),
    validateRenderSafety(workbook, choices)
  ]);
}
```

---

## 5. Generator Recipe Bank

새 template을 만들 때 아래 recipe 중 하나를 선택하거나 조합한다. 이것이 “창의적이지만 구현 가능한” 문제 family의 핵심이다.

## 5.1 Recipe: `document_reference_calculation`

표의 값은 raw value이고, 문서/glossary/note가 의미와 단위를 결정한다.

```text
lookup target row
lookup document rule
convert unit
apply factor or adjustment
answer = rounded result
```

필수 요소:

- main table
- reference document or glossary
- target row
- unit/factor rule
- wrong-row distractor
- document-skip distractor

좋은 variation:

- 약어 이름 변경
- 단위 변경
- factor/cap 변경
- note 위치 변경
- target/distractor row shuffle

## 5.2 Recipe: `symbol_rule_induction`

완성 행에서 기호 규칙을 유도하고 질의 행에 적용한다.

```text
read completed rows
infer symbol transform
apply transform to query row
aggregate result
```

필수 요소:

- completed rows
- query row
- at least one symbol
- enough rows to disambiguate rule
- symbol-ignore distractor

좋은 variation:

- symbol set 변경
- multiply/add/cap/sign rule 변경
- completed row 수 변경
- aggregation 변경

## 5.3 Recipe: `cross_sheet_unit_note`

단위 규칙이 별도 sheet에 있으며, 표의 category/status에 따라 변환 방식이 달라진다.

```text
lookup target row
lookup category unit
convert raw amount
lookup status adjustment
apply adjustment
```

필수 요소:

- main table
- unit note sheet
- status rule sheet or note
- category/status fields

좋은 variation:

- unit multiplier 변경
- category label 변경
- status adjustment 방식 변경
- exception level 추가

## 5.4 Recipe: `merged_header_lookup_or_delta`

상위/하위 header를 조합해서 올바른 cell을 찾고 차이/비율을 계산한다.

```text
resolve grouped header
lookup v1
lookup v2
compute delta or ratio
```

필수 요소:

- grouped header table
- entity row
- period or group columns
- submetric columns

좋은 variation:

- period labels
- submetric labels
- delta direction
- ratio rounding
- header order

## 5.5 Recipe: `document_filter_rank`

문서의 filter rule을 표에 적용한 뒤 rank 또는 target entity를 찾는다.

```text
read eligibility rule
filter rows
sort rows
tie-break if needed
return requested field
```

필수 요소:

- main table with candidates
- document rule with eligibility
- sort key
- tie-break rule for Level 2+
- exclusion exception for Level 3

좋은 variation:

- filter condition 개수
- sort direction
- tie-break field
- requested output field
- rank index

## 5.6 Recipe: `conditional_exception_rule`

기본 규칙은 간단하지만 특정 상태/level/category에서 예외가 적용된다.

```text
compute base
if condition:
  apply exception
answer = result
```

필수 요소:

- status/category field
- exception note
- distractor that ignores exception

좋은 variation:

- cap/floor
- multiplier override
- exclusion
- sign flip
- rounding exception

## 5.7 Recipe: `aggregation_with_decoy_fields`

여러 셀을 합산/평균/최대/최소하되, 일부 visible field는 제외해야 한다.

```text
select eligible cells
exclude decoy fields
aggregate selected cells
apply unit or rounding
```

필수 요소:

- multiple numeric columns
- rule defining included/excluded fields
- visible-but-unused distractor field

좋은 variation:

- sum/mean/min/max
- included field count
- exclusion wording
- negative values
- missing value handling

---

## 6. Variation Axis Bank

각 template은 아래 중 최소 3개 이상을 사용해야 한다. 이 조건은 단순 예제 복제를 막는다.

| Axis | 예시 | Invariant |
| --- | --- | --- |
| entity labels | 서울A, 인천K, Node-17, 구역나 | target unique |
| row order | target top/middle/bottom | target still findable |
| column order | metric columns shuffled | header still readable |
| table size | 4~9 rows, 4~8 cols | decisive cells visible |
| units | 원, 천 원, 만 원, %, point | conversion rule visible |
| synthetic codes | TCA, R2N, K-Adj, QX7 | glossary decisive |
| symbols | ★, ▲, ●, ◆ | rule inferable |
| document wording | concise/verbose/paraphrase | same logical rule |
| page order | main first, glossary first | page refs valid |
| exception type | cap, floor, override, exclusion | exception decisive |
| rounding | round, floor, ceil, nearest 10 | rule visible |
| visual emphasis | accent target cells, neutral rows | no answer leakage |
| unused fields | visible decoy metric | not used in answer |
| distractor row | same prefix/city/category | wrong answer if used |
| answer magnitude | small/medium/large | choices unique |

---

## 7. Common Validation Library

모든 template은 최소한 아래 validation을 통과해야 한다.

## 7.1 Structural Validation

```text
- family_id exists
- template_id exists
- level exists and is supported
- seed_slot exists
- required sheets exist
- required pages exist
- required elements exist
- query text exists
- answer form exists
- answer choices exist if multiple choice is enabled
```

## 7.2 Evidence Validation

```text
- every gold evidence page_ref exists
- every gold evidence element_id exists
- every decisive variable appears in visible evidence
- required document/glossary/note exists
- query row exists when required
- completed rows exist when rule induction requires them
```

## 7.3 Answer Validation

```text
- solve(params) matches gold answer
- answer display value matches answer form
- rounding rule is applied consistently
- all choices have IDs
- correct answer appears exactly once
- distractors are not equal to answer
- distractors are unique
```

## 7.4 Shortcut Validation

```text
- each declared shortcut trap has a corresponding distractor or test
- wrong row produces a different value
- unit skip produces a different value
- document skip cannot determine decisive semantics
- exception skip produces a different value when exception is decisive
- visible-unused field usage produces a wrong value when applicable
```

## 7.5 Render Safety Validation

```text
- no forbidden visible metadata strings
- answer cards only show option ID and display value
- no candidate/distractor/rationale/debug labels in UI
- required evidence appears in normalized viewer
- evaluation mode can hide answer submission UI
- no giant fixed-height empty table container
```

Forbidden visible strings:

```text
candidate
distractor
rationale
debug
generation
source_hint
answer_type
candidate_type
distractor_type
rationale_type
검산 후보
표 단서 적용 후보
문서 단서 적용 후보
단위 확인 후보
정답 후보
생성 메타
```

---

## 8. Normalized Viewer Contract

Generator output은 frontend에서 raw template별로 직접 렌더링하지 않고, normalized view model로 변환되어야 한다.

```ts
type NormalizedSampleViewModel = {
  id?: string;
  dataset?: string;
  template?: string;
  taskType?: string;
  mode?: "review" | "evaluation";
  pageIndex?: number;
  pageCount?: number;

  header: {
    title: string;
    subtitle?: string;
    badges?: Array<{ label: string; value?: string }>;
  };

  question: {
    title: string;
    text: string;
  };

  submission: {
    title: string;
    formats: Array<{ id: string; label: string }>;
  };

  evidenceSections: NormalizedEvidenceSection[];

  choices?: Array<{
    id: string;
    displayValue: string;
  }>;

  validationIssues: ValidationIssue[];
};
```

Template generator는 다양한 workbook을 만들 수 있지만, viewer는 일관된 구조로 보여줘야 한다.

---

## 9. New Template Creation Workflow

새 template을 만들 때 coding agent는 아래 순서를 따른다.

```text
1. Read family spec and abc-generator scaffold.
2. Fill Template Spec Card.
3. Choose one or more generator recipes.
4. Define manifest.
5. Define Params type.
6. Implement sampleParams.
7. Implement buildWorkbook.
8. Implement solve.
9. Implement buildChoices.
10. Implement buildMetadata.
11. Implement validate.
12. Add template to family registry.
13. Add at least one test per level.
14. Add audit coverage.
15. Run lint/build/test/audit.
```

---

## 10. Coding Agent Prompt Template

새 template을 실제로 구현할 때 아래 prompt를 사용한다.

```text
You are implementing a new Visual TableQA template generator.

Read the family specification and abc-generator scaffold first.
Do not hardcode a single example. Implement a deterministic seed-based generator.

Use this Template Spec Card:

[PASTE TEMPLATE SPEC CARD HERE]

Requirements:
- Implement the template through the standard generator interface.
- Preserve the reasoning contract, but use variation axes to create diverse instances.
- Generate valid workbook sheets/pages/elements.
- Keep all decisive evidence visible.
- Keep hidden program, gold answer, distractor derivations, and shortcut labels out of rendered UI.
- Build answer choices with only option ID and display value visible.
- Add metadata_extra with decisive variables, visible-unused variables, shortcut traps, distractor derivations, gold evidence path, and hidden program.
- Add validation for structure, evidence, answer, shortcuts, and render safety.
- Add tests for all supported levels.
- Add this template to the family registry and audit script.

Before finishing, report:
1. Files changed.
2. Template manifest.
3. Variation axes implemented.
4. Shortcut traps implemented.
5. Validation rules added.
6. Test/audit result.
```

---

## 11. Template Stub

아래는 새 template 파일의 시작점이다.

```ts
import { makeRng } from "../../core/rng";
import { buildChoiceSet } from "../../core/choices";
import { validateInstance } from "../../core/validation";
import type { TemplateGenerator } from "../../core/types";

const TEMPLATE_OFFSET = 0; // assign unique offset

export const manifest = {
  family_id: "k_vis_table_arc",
  template_id: "replace_me",
  template_label: "Replace Me",
  answer_form: "number",
  primary_operator: "replace_me",
  support_operators: [],
  capability_axes: [],
  cue_tags: [],
  required_sheet_ids: [],
  required_page_refs_by_level: {
    1: [],
    2: [],
    3: []
  },
  level_count: 3,
  supports_multiple_choice: true
};

type Params = {
  seed_slot: number;
  level: 1 | 2 | 3;
  query: {
    text: string;
    answer_format: string;
  };
  target: {
    id: string;
    label: string;
  };
  decisive: Record<string, number | string | boolean>;
  visible_unused: Record<string, number | string | boolean>;
  distractor_context: Record<string, unknown>;
  visual: Record<string, unknown>;
};

function sampleParams({ seed_slot, level }): Params {
  const rng = makeRng(seed_slot + TEMPLATE_OFFSET + level);

  // 1. sample target
  // 2. sample decisive variables
  // 3. sample visible-unused variables
  // 4. sample distractor context
  // 5. sample visual/layout variation
  // 6. build question text

  return {
    seed_slot,
    level,
    query: {
      text: "",
      answer_format: "원 단위 숫자 또는 선택지 ID"
    },
    target: {
      id: "",
      label: ""
    },
    decisive: {},
    visible_unused: {},
    distractor_context: {},
    visual: {}
  };
}

function buildWorkbook(params: Params) {
  // Build visible workbook only.
  // Do not expose hidden program or distractor metadata here.
  return {
    sheets: []
  };
}

function solve(params: Params) {
  // Hidden program.
  const value = 0;

  return {
    value,
    display_value: `${value}원`,
    answer_form: manifest.answer_form
  };
}

function buildChoices({ params, answer, rng }) {
  const distractors = [
    // derive distractors from declared shortcut traps
  ];

  return buildChoiceSet({
    answer,
    distractors,
    rng,
    optionIds: ["A", "B", "C", "D"]
  });
}

function buildMetadata({ params, answer, choices, workbook }) {
  return {
    decisive_variables: params.decisive,
    visible_unused_variables: params.visible_unused,
    shortcut_traps: [],
    distractor_derivations: [],
    gold_evidence_path: [],
    hidden_program: {
      text: "",
      pseudo_code: ""
    }
  };
}

function validate({ params, workbook, answer, choices, metadata }) {
  return validateInstance({
    manifest,
    params,
    workbook,
    answer,
    choices,
    metadata
  });
}

export const generator: TemplateGenerator<Params> = {
  manifest,
  sampleParams,
  buildWorkbook,
  solve,
  buildChoices,
  buildMetadata,
  validate
};
```

---

## 12. Audit Script Contract

Family 전체 audit는 최소 다음을 출력해야 한다.

```text
Family: k_vis_table_arc
Templates discovered: N
Seeds checked per template/level: M

Template results:
- abbrev_doc_reference
  - level 1: pass 100 / warn 0 / fail 0
  - level 2: pass 100 / warn 0 / fail 0
  - level 3: pass 100 / warn 0 / fail 0

Global checks:
- forbidden visible metadata: pass
- choice uniqueness: pass
- gold evidence references: pass
- render safety: pass
- shortcut trap coverage: pass
```

Audit 실패 시 예:

```text
FAIL template=document_filter_rank level=3 seed=42
reason: declared shortcut trap tie_break_skip has no corresponding distractor
```

---

## 13. 최소 완료 기준

새 template은 다음을 만족해야 완료로 본다.

- Template Spec Card가 작성되어 있다.
- manifest가 family registry에 등록되어 있다.
- seed 기반으로 level 1~3 instance를 생성한다.
- workbook에 required evidence가 모두 visible하다.
- solve가 deterministic하고 validation과 일치한다.
- distractor가 shortcut traps를 대표한다.
- metadata_extra가 gold evidence path와 hidden program을 기록한다.
- rendered UI에 forbidden metadata가 노출되지 않는다.
- normalized viewer가 evidence/choices를 표시할 수 있다.
- audit script에서 pass 또는 명확한 validation issue를 낸다.

---

## 14. 중요한 구현 철학

이 scaffold는 template을 단순히 “예제 하나 복사하기”로 만들지 않기 위해 존재한다.

좋은 template generator는 다음을 만족한다.

```text
Same reasoning contract,
Many visual/text/numeric variations,
Deterministic hidden program,
Explicit evidence path,
Strong shortcut traps,
No metadata leakage,
Validation before rendering.
```

나쁜 generator는 다음과 같다.

```text
One hardcoded row,
One hardcoded question,
One fixed table,
No validation,
No distractor derivation,
No evidence path,
Visible debug labels,
Works only for the screenshot.
```

새로운 template을 추가할 때는 항상 전자가 되도록 구현한다.

