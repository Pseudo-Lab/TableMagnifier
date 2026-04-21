# table-env-bench

`table-env-bench`는 workbook-style 인터페이스에서 시트와 페이지를 탐색하며 푸는 한국어 Visual TableQA 벤치마크입니다. 에이전트는 숨겨진 구조화 workbook 데이터를 직접 받지 않고, 현재 보이는 viewport와 질문, 남은 예산, 현재 sheet/page 정보만 보고 행동합니다.

이 저장소는 PseudoLab `TableMagnifier` 프로젝트에서 파생된 benchmark POC입니다. 상위 프로젝트가 한국어 TableQA용 데이터 구축과 검증 전반을 다룬다면, 이 저장소는 그중에서도 `interactive Visual TableQA benchmark`와 `agent evaluation`에 초점을 맞춘 실험용 구현입니다.

현재 canonical 방향은 `canonical_real_tableqa` 하나입니다. 사람에게도 바로 읽히는 실제 업무형 합성 표를 바탕으로, 표의 구조와 시각 단서를 읽고 규칙을 유도하거나 범위를 좁힌 뒤 정답을 선택하는 문제를 다룹니다.

상위 프로젝트와의 관계는 다음처럼 보는 편이 가장 정확합니다.

- `TableMagnifier`: 한국어 TableQA 데이터 구축, 합성, 검증, 도구화까지 포함하는 더 큰 프로젝트
- `table-env-bench`: workbook UI 위에서 agent와 사람이 실제로 탐색하며 푸는 Visual TableQA reasoning benchmark POC
- 현재 이 저장소의 관심사: 문제 설계, 렌더링, environment, replay, evaluation, public benchmark pack 운영

## 프로젝트 배경

이 POC는 “한국어 표를 얼마나 잘 읽는가”를 단일 정답 추출 문제가 아니라, `화면을 탐색하며 근거를 모으는 문제`로 다뤄보려는 목적에서 출발했습니다.

핵심 질문은 다음과 같습니다.

- agent가 visually rendered table을 실제로 읽는가
- 예시, 반례, 메모, 소계, grouped row 같은 workbook evidence를 사용할 수 있는가
- 단순 lookup이 아니라 transfer, disambiguation, scope resolution을 할 수 있는가
- 사람에게도 읽히는 문제를 agent benchmark로 안정적으로 운영할 수 있는가

즉, 이 저장소는 단순 데이터셋이 아니라 `interactive benchmark environment`와 `frozen evaluation pack`을 함께 제공하는 연구용 POC입니다.

## 프로젝트 목표

현재 이 저장소의 목표는 다음과 같습니다.

- 한국어 Visual TableQA를 workbook-style interactive benchmark로 정의하기
- 표, 헤더, 소계, 노트, 선택지 같은 시각 근거를 중심으로 reasoning 문제를 설계하기
- 사람과 agent가 같은 화면을 보되, agent는 제한된 action space 안에서 문제를 풀게 만들기
- frozen public pack, replay, readability audit, baseline evaluation까지 한 경로로 묶기
- 이후 hidden holdout, human baseline, model failure analysis로 확장 가능한 기반을 만들기

현재 public benchmark pack은 두 개입니다.

- `public_dev_real_v1`
- `public_smoke_real_v1`

현재 active family는 세 가지입니다.

- `channel_policy_transfer`
- `inventory_exception_disambiguation`
- `report_scope_reconciliation`

문서별 현재 상태는 [docs/document_status.md](docs/document_status.md)에서 확인할 수 있습니다. 처음 읽는 경우에는 [docs/first_steps.md](docs/first_steps.md), [docs/benchmark_guide.md](docs/benchmark_guide.md), [docs/task_families.md](docs/task_families.md) 순으로 보는 편이 빠릅니다.

## 현재 구현

현재 구현은 다음을 포함합니다.

- Gym 유사 환경 API: `reset(seed)` / `step(action)`
- workbook abstraction: `workbook -> sheet -> page -> region`
- 결정론적 SVG renderer
- table region, note marker, answer choice region hit testing
- frozen benchmark instance pack loader
- correctness / efficiency / generalization 집계 / replay export
- random / heuristic baseline
- tool-call 기반 LLM baseline runner
- FastAPI session API
- React web UI
- Playwright surface readability / workbench traversal gate

## 장기 방향

앞으로의 canonical benchmark는 다음 원칙을 따른다.

- Visual TableQA를 바탕으로 한다
- 표와 worksheet fragment가 항상 핵심 evidence surface다
- chart, note, legend는 표를 보조하는 근거다
- 정답은 lookup보다 scope resolution, disambiguation, transfer 같은 reasoning을 통해 도달해야 한다
- pure abstract puzzle처럼 표 의미가 사라지는 방향은 피한다
- readability failure는 UI polish가 아니라 benchmark failure로 취급한다

## 빠른 시작

WSL에서 의존성을 설치합니다.

```bash
cd /path/to/table-env-bench
uv sync
```

## 실행 방법

테스트:

```bash
cd /path/to/table-env-bench
uv run pytest
```

단일 데모 실행:

```bash
cd /path/to/table-env-bench
uv run python -m table_env_bench.scripts.run_demo --family channel_policy_transfer --level 1 --agent heuristic
```

고정 benchmark instance 실행:

```bash
cd /path/to/table-env-bench
uv run python -m table_env_bench.scripts.run_demo --instance-id public_smoke_real_v1__channel_policy_transfer_icon_scope_cell_l1_s0 --agent heuristic
```

baseline 평가:

```bash
cd /path/to/table-env-bench
uv run python -m table_env_bench.scripts.eval_baselines
```

LLM 평가:

```bash
cd /path/to/table-env-bench
OPENAI_API_KEY=... uv run python -m table_env_bench.scripts.eval_llm --suite public_dev_real_v1 --model gpt-5-nano
```

preview gallery export:

```bash
cd /path/to/table-env-bench
uv run python -m table_env_bench.scripts.export_preview_gallery --out artifacts/previews_real --pack public_dev_real_v1
```

strict public-pack readability audit:

```bash
cd /path/to/table-env-bench
uv run python -m table_env_bench.scripts.audit_readability --pack public_smoke_real_v1
uv run python -m table_env_bench.scripts.audit_readability --pack public_dev_real_v1
```

FastAPI 서버:

```bash
cd /path/to/table-env-bench
uv run python -m table_env_bench.scripts.run_server --reload
```

React 웹 UI:

```bash
cd /path/to/table-env-bench/frontend
npm install
npm run dev
```

## 벤치마크 개념

한 episode는 workbook 하나와 질문 하나로 구성됩니다.

- workbook: 여러 sheet를 가진 문서
- sheet: 탭 단위
- page: 한 sheet 안의 view 또는 pagination 단위
- region: table / chart / legend / note block 같은 groundable 영역

핵심은 정답 하나를 읽어내는 것이 아니라, 현재 보이는 시각 정보 위에서 어느 표, 어느 header scope, 어느 row group, 어느 note가 relevant한지 판단하는 것입니다.

## 액션 공간

benchmark action schema는 다음으로 제한됩니다.

- `select_sheet(name_or_index)`
- `next_page`
- `prev_page`
- `zoom_in`
- `zoom_out`
- `pan_up`
- `pan_down`
- `pan_left`
- `pan_right`
- `click_region(x, y)`
- `submit_answer(text)`

`click_region(x, y)`는 hidden cell id가 아니라 현재 렌더링된 scene의 region hit test로 처리됩니다.

## 모드

- agent mode
  - headless API와 최소 observation만 사용
- human mode
  - 질문, sheet tabs, page navigation, answer 입력이 보이는 로컬 UI
- dev mode
  - debug overlay, click 좌표 입력, last_event, replay를 확인할 수 있는 inspector UI

## 현재 canonical family 방향

- `channel_policy_transfer`
  - 예시 표와 보조 메모를 읽고 현재 표의 집행 대상을 고른다
- `inventory_exception_disambiguation`
  - 예외 확인 표와 메모를 반영해 잘못된 기준을 제거한다
- `report_scope_reconciliation`
  - merged header, grouped row, subtotal block이 실제 집계 범위를 결정한다

## 채점과 replay

episode 결과에는 다음이 포함됩니다.

- correctness
- efficiency
- overall
- raw_accuracy
- generalization_score
- action_count
- unique_sheets_visited
- unique_pages_visited
- replay trace

기본 correctness는 normalized exact match입니다. 한국어 답안 normalizer는 쉼표, 공백, `원` / `만원` / `개` / `건` 같은 접미어를 허용합니다.

기본 efficiency scorer는 action count 기반입니다. scorer 인터페이스는 분리되어 있어 나중에 다른 scoring policy로 교체할 수 있습니다.

replay JSON에는 각 step의 다음 정보가 저장됩니다.

- action payload
- before / after navigation state
- click 좌표와 resolved region
- reward
- terminated / truncated

## 새 family 추가 방법

1. [docs/family_design_brief.md](docs/family_design_brief.md)에서 canonical family 기준을 확인합니다.
2. [docs/episode_rulebook.md](docs/episode_rulebook.md), [docs/visual_cue_inventory.md](docs/visual_cue_inventory.md), [docs/operator_taxonomy.md](docs/operator_taxonomy.md)를 참고해 evidence topology를 설계합니다.
3. `src/table_env_bench/data/families/` 아래에 family generator를 추가합니다.
4. [src/table_env_bench/data/models.py](src/table_env_bench/data/models.py)의 workbook/sheet/page/element/region dataclass를 사용합니다.
5. authoring pipeline과 readability gate를 통과시킵니다.
6. 필요하면 frozen public pack으로 내리고 [docs/task_families.md](docs/task_families.md)를 갱신합니다.
7. pytest와 Playwright gate가 모두 통과하는지 확인합니다.

## 주요 경로

- [src/table_env_bench/env/environment.py](src/table_env_bench/env/environment.py)
- [src/table_env_bench/env/actions.py](src/table_env_bench/env/actions.py)
- [src/table_env_bench/render/renderer.py](src/table_env_bench/render/renderer.py)
- [src/table_env_bench/data/models.py](src/table_env_bench/data/models.py)
- [src/table_env_bench/data/families](src/table_env_bench/data/families)
- [src/table_env_bench/data/instances.py](src/table_env_bench/data/instances.py)
- [src/table_env_bench/eval/scoring.py](src/table_env_bench/eval/scoring.py)
- [src/table_env_bench/server/app.py](src/table_env_bench/server/app.py)
- [frontend/src/App.tsx](frontend/src/App.tsx)
