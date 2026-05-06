# Pilot Implementation Strategy

상태: historical design archive

이 문서는 초기 pilot 구현 당시의 순서를 기록한 문서다. 현재 active runtime과 public benchmark는 이미 `canonical_real_tableqa`와 real-data frozen pack 기준으로 운영되므로, 실제 구현과 release 판단은 [benchmark_guide.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/benchmark_guide.md), [real_data_authoring_policy.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/real_data_authoring_policy.md), [human_readability_checklist.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/human_readability_checklist.md)를 우선 본다.

이 문서는 새 pilot family를 실제 코드로 구현하는 `현실적인 순서`를 정리한다.

현재 코드베이스를 기준으로 보면, 완전한 새 렌더링 시스템을 먼저 만드는 것보다 `작은 확장 -> pilot 1개 구현 -> 검증 -> pilot 2개 구현` 순서가 안전하다.

## 1. 지금 코드에서 바로 재사용할 것

바로 재사용 가능한 축:

- `EpisodeSpec` / `WorkbookSpec` / `SheetSpec` / `PageSpec`
- table/chart/text_block rendering backbone
- region hit testing contract
- replay / scoring / preview export
- Streamlit / server / React UI shell

즉, pilot 구현의 핵심은 environment가 아니라 `data model + renderer + generator helper` 쪽이다.

## 2. 구현 순서

### Step 1. cell metadata 확장

대상 파일:

- [models.py](/mnt/c/Users/imssh/Documents/TableMagnifier/src/table_env_bench/data/models.py)

권장 변경:

- `TableCellSpec`에 `metadata: dict[str, Any]` 추가

이유:

- icon anchor
- pattern
- semantic hint

같은 cue를 renderer가 읽을 수 있어야 pilot family가 성립한다.

### Step 2. renderer에 minimal cue 지원 추가

대상 파일:

- [renderer.py](/mnt/c/Users/imssh/Documents/TableMagnifier/src/table_env_bench/render/renderer.py)

권장 범위:

- top-right / bottom-left triangle icon
- diagonal stripe pattern
- subtle candidate frame

주의:

- legacy family 렌더링이 깨지지 않게 default behavior는 그대로 둔다
- cue는 table 안의 overlay로 그린다

### Step 3. choice surface 임시 구현

선택지:

1. 가장 빠른 방법
   - `TextBlockElementSpec` + `RegionSpec` 조합으로 statement choice와 cell choice panel을 흉내냄
2. 더 좋은 방법
   - `ChoicePanelElementSpec`를 새로 추가

추천:

- pilot 1개를 빨리 돌리려면 1번
- pilot 2개 이상과 React/Streamlit 상호작용까지 생각하면 2번

### Step 4. generator helper 분리

대상 파일:

- [generators.py](/mnt/c/Users/imssh/Documents/TableMagnifier/src/table_env_bench/data/generators.py)

새 helper 추천:

- `make_pilot_table(...)`
- `make_icon_cell(...)`
- `make_pattern_cell(...)`
- `make_choice_panel(...)`
- `make_choice_regions(...)`

이유:

- legacy family generator와 pilot family generator를 같은 파일에 둬도 helper 수준에서는 분리 가능
- 이후 `src/table_env_bench/data/pilot_generators.py`로 옮기기 쉬워짐

### Step 5. pilot family registry 추가

초기엔 아래 둘만 추가한다.

- `channel_policy_transfer`
- `inventory_exception_disambiguation`

권장:

- Level 1만 먼저 구현
- seed 0-2 정도에서 deterministic preview 확인

### Step 6. validation loop

반드시 같이 할 것:

- preview export
- human UI에서 실제로 cue가 보이는지 확인
- answer choice region click이 되는지 확인
- legacy families regression test

## 3. 추천 구현 단위

pilot 구현은 아래처럼 잘게 나누는 것이 좋다.

### Unit A. visual cue infrastructure

- cell metadata
- renderer overlay
- tests

### Unit B. choice infrastructure

- choice panel rendering
- choice regions
- server/UI compatibility

### Unit C. family 1 implementation

- `channel_policy_transfer_l1_icon_anchor_pick_v1`

### Unit D. family 2 implementation

- `inventory_exception_disambiguation_l1_pattern_vs_icon_statement_v1`

## 4. 파일별 예상 수정

- [models.py](/mnt/c/Users/imssh/Documents/TableMagnifier/src/table_env_bench/data/models.py)
  - cell metadata, maybe new choice element
- [renderer.py](/mnt/c/Users/imssh/Documents/TableMagnifier/src/table_env_bench/render/renderer.py)
  - icon/pattern/choice rendering
- [generators.py](/mnt/c/Users/imssh/Documents/TableMagnifier/src/table_env_bench/data/generators.py)
  - pilot helpers and family registry
- tests
  - deterministic render
  - generator contract
  - choice region resolution

## 5. risk 관리

가장 큰 risk는 세 가지다.

### 5.1 renderer 과확장

- cue 지원을 한 번에 너무 많이 넣으면 legacy family까지 흔들릴 수 있다

대응:

- icon 1종, pattern 1종부터

### 5.2 answer choice contract 미정

- choice panel을 너무 늦게 정하면 UI/server와 다시 맞춰야 한다

대응:

- pilot 1 구현 전에 최소 contract를 정한다

### 5.3 draft와 코드 간 괴리

- 문서 초안은 좋은데 실제 dataclass에 안 들어갈 수 있다

대응:

- [generator_episode_schema.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/generator_episode_schema.md)를 구현의 중간 계약으로 사용한다

## 6. 추천 바로 다음 작업

가장 자연스러운 실제 구현 순서는 이렇다.

1. `TableCellSpec.metadata` 추가
2. renderer에 triangle anchor + stripe pattern 추가
3. 임시 choice panel helper 추가
4. `channel_policy_transfer_l1_icon_anchor_pick_v1` 구현
5. preview / tests
6. `inventory_exception_disambiguation_l1_pattern_vs_icon_statement_v1` 구현

## 7. 문서 연결

- [docs/generator_episode_schema.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/generator_episode_schema.md)
- [docs/pilot_episode_drafts.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/pilot_episode_drafts.md)
- [docs/episode_validation_checklist.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/episode_validation_checklist.md)
