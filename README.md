# table-env-bench

`table-env-bench`는 workbook-style 인터페이스에서 시트와 페이지를 탐색하며 푸는 한국어 Visual TableQA 벤치마크입니다. 에이전트는 숨겨진 구조화 workbook 데이터를 직접 받지 않고, 현재 viewport, 질문, 남은 예산, sheet/page 상태만 보고 행동합니다.

현재 canonical 방향은 `canonical_real_tableqa`입니다. 사람이 읽을 수 있는 실제 업무형 합성 표를 바탕으로, 표 구조와 시각 단서를 읽고 규칙을 유도하거나 범위를 좁힌 뒤 정답을 선택하는 문제를 다룹니다.

## 현재 운영 모델

이 저장소는 더 이상 repo 안에 frozen `public_*` instance pack을 포함하지 않습니다. 기본 실행과 UI 노출은 generated benchmark suite catalog를 사용합니다.

- `/api/catalog`: 개발용 family/level 브라우저
- `/api/benchmark-suites`: generated benchmark suite/template/seed-slot launch catalog
- `/api/instances`: 별도 instance pack이 있을 때만 노출되며, 현재 repo 기본값은 `[]`

현재 generated suite는 다음 순서로 노출됩니다.

- `canonical_dev`
- `eval_hard_dev`
- `eval_hard_holdout`

Workbench는 instance pack이 없으면 generated benchmark selector를 보여주고, 선택한 record의 `family`, `level`, `seed`, `template_id`로 정확히 세션을 시작합니다. Generated benchmark에는 free-form seed 입력이 없고, catalog에 선언된 seed slot만 선택합니다.

## 현재 Family

우선 노출 family:

- `marker_position_rule_transfer`
  - 예시/범례/반례에서 셀 모서리 표식 위치 규칙을 유도하고 query table에 전이합니다.

Active/dev family:

- `excel_viewport_sheet_navigation`
  - pan/zoom/sheet navigation과 viewport traversal 안정성을 검증합니다.

Deprecated comparison families:

- `channel_policy_transfer`
- `inventory_exception_disambiguation`
- `report_scope_reconciliation`

Deprecated family는 삭제하지 않고 regression, baseline 비교, hard suite 일부 구성을 위해 유지합니다.

## 빠른 시작

WSL에서 실행하는 것을 기준으로 합니다.

```bash
cd /mnt/c/Users/imssh/Documents/TableMagnifier
uv sync
```

Python test:

```bash
uv run pytest
```

Frontend 의존성:

```bash
cd frontend
npm install
```

## UI 실행

터미널 1:

```bash
cd /mnt/c/Users/imssh/Documents/TableMagnifier
uv run python -m table_env_bench.scripts.run_server --host 127.0.0.1 --port 8000
```

터미널 2:

```bash
cd /mnt/c/Users/imssh/Documents/TableMagnifier/frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

브라우저에서 `http://127.0.0.1:5173/`를 엽니다.

개발용 family deep link는 계속 지원합니다.

```text
http://127.0.0.1:5173/?family=excel_viewport_sheet_navigation&level=1&seed=0
```

유효한 `?family=...` dev URL은 generated default보다 우선합니다. 유효하지 않은 `?family` URL이나 URL 파라미터가 없는 경우에는 `/api/benchmark-suites`의 첫 generated record로 시작합니다.

## 실행 예시

Generated family demo:

```bash
cd /mnt/c/Users/imssh/Documents/TableMagnifier
uv run python -m table_env_bench.scripts.run_demo --family marker_position_rule_transfer --level 1 --template-id corner_anchor_statement --seed 0 --agent heuristic
```

Baseline 평가:

```bash
uv run python -m table_env_bench.scripts.eval_baselines --suite canonical_dev
```

LLM 평가:

```bash
OPENAI_API_KEY=... uv run python -m table_env_bench.scripts.eval_llm --suite canonical_dev --model gpt-5-nano
```

Preview gallery:

```bash
uv run python -m table_env_bench.scripts.export_preview_gallery --out artifacts/previews_active
```

Readability audit:

```bash
uv run python -m table_env_bench.scripts.audit_readability
```

빠른 smoke audit:

```bash
uv run python -m table_env_bench.scripts.audit_readability --smoke --seed-samples 0
```

Frontend gates:

```bash
cd frontend
npm run build
npm run lint
npx playwright test playwright/dev-family-visibility.spec.ts --project=chromium-fullhd
npx playwright test playwright/workbench-navigation-readability.spec.ts --project=chromium-fullhd
```

## 벤치마크 개념

한 episode는 workbook 하나와 질문 하나로 구성됩니다.

- workbook: 여러 sheet를 가진 문서
- sheet: 탭 단위
- page: 한 sheet 안의 view 또는 pagination 단위
- region: table, note marker, answer choice 같은 hit-test 가능한 영역

핵심은 정답 하나를 읽어내는 것이 아니라, 현재 보이는 시각 정보 위에서 어느 표, 어느 header scope, 어느 row group, 어느 note, 어느 표식이 relevant한지 판단하는 것입니다.

## 액션 공간

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

## 새 Family 추가 방법

새 canonical family는 adapter 방식으로 등록합니다.

1. `src/table_env_bench/data/families/<family_id>.py`에 generator module을 만듭니다.
2. module은 최소한 아래 surface를 제공합니다.
   - `FAMILY`
   - `FAMILY_LABEL`
   - `list_manifests(level)`
   - `build_episode(level, seed, *, template_id=None)`
3. `src/table_env_bench/data/families/__init__.py`의 `CANONICAL_FAMILY_ADAPTERS`에 `FamilyAdapter` 하나를 추가합니다.
4. `CANONICAL_FAMILY_LABELS`, `CANONICAL_MANIFEST_LISTERS`, `CANONICAL_BUILDERS`는 adapter 목록에서 파생되므로 직접 수정하지 않습니다.
5. authoring pipeline, readability audit, pytest, frontend Playwright gate를 통과시킵니다.

관련 문서:

- [docs/first_steps.md](docs/first_steps.md)
- [docs/benchmark_guide.md](docs/benchmark_guide.md)
- [docs/task_families.md](docs/task_families.md)
- [docs/family_design_brief.md](docs/family_design_brief.md)
- [docs/episode_rulebook.md](docs/episode_rulebook.md)
- [docs/visual_cue_inventory.md](docs/visual_cue_inventory.md)
- [docs/operator_taxonomy.md](docs/operator_taxonomy.md)

## Codex Skill 설치와 사용

이 repo에는 TableQA family authoring을 돕는 Codex skill이 준비되어 있습니다.

Repo에 포함된 skill source:

```text
docs/skills/tableqa-family-author/SKILL.md
```

Codex가 해당 skill을 인식하지 못하는 환경에서는 repo의 skill directory를 `~/.codex/skills` 아래로 복사해서 추가합니다.

```bash
mkdir -p ~/.codex/skills/tableqa-family-author
cp -R /mnt/c/Users/imssh/Documents/TableMagnifier/docs/skills/tableqa-family-author/. ~/.codex/skills/tableqa-family-author/
```

이미 `/home/ssh/.codex/skills/tableqa-family-author/SKILL.md`가 있다면 전역 skill이 설치된 상태입니다.

Codex에서 새 문제 family를 만들 때는 프롬프트 첫머리에 skill을 명시합니다.

```text
$tableqa-family-author marker_position_rule_transfer와 다른 새 Visual TableQA family를 adapter 방식으로 추가해줘
```

이 skill은 다음 순서를 강제합니다.

- rule docs와 validation checklist 확인
- family adapter surface 설계
- episode generator 구현
- manifest/seed/template contract 검증
- readability와 Playwright gate 확인

## 주요 경로

- [src/table_env_bench/env/environment.py](src/table_env_bench/env/environment.py)
- [src/table_env_bench/render/renderer.py](src/table_env_bench/render/renderer.py)
- [src/table_env_bench/data/families](src/table_env_bench/data/families)
- [src/table_env_bench/data/families/adapters.py](src/table_env_bench/data/families/adapters.py)
- [src/table_env_bench/data/canonical_catalog.py](src/table_env_bench/data/canonical_catalog.py)
- [src/table_env_bench/data/instances.py](src/table_env_bench/data/instances.py)
- [src/table_env_bench/server/app.py](src/table_env_bench/server/app.py)
- [frontend/src/App.tsx](frontend/src/App.tsx)
- [frontend/public/workbook-canvas-renderer.js](frontend/public/workbook-canvas-renderer.js)
