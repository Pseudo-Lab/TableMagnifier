# table-env-bench

`table-env-bench`는 한국어 시각 테이블 환경에서 에이전트가 탐색, 규칙 유도, 문서 참조, 계산을 수행하는 offline-first benchmark입니다. 에이전트는 hidden workbook 구조나 raw table dump를 받지 않고 현재 viewport, sheet/page 상태, 질문, action budget만 보고 행동합니다.

현재 canonical track은 `korean_visual_table_agent_reasoning`이고, active family는 `k_vis_table_arc`입니다.

## 현재 저장소 범위

이 repo는 Python benchmark core와 문서, 테스트만 유지합니다. 별도 web UI, JS visual gate, 분리된 평가 설계 디렉터리는 제거했습니다.

- `src/table_env_bench/env/`: environment API, action parsing, replay logging
- `src/table_env_bench/render/`: layout, SVG renderer, PNG image renderer
- `src/table_env_bench/data/`: episode specs, canonical catalog, deterministic generators
- `src/table_env_bench/authoring/`: rulebook, visual QA, static readability, red-team, regression stages
- `src/table_env_bench/eval/`: correctness and efficiency scoring
- `src/table_env_bench/server/`: optional FastAPI session API
- `tests/`: deterministic regression coverage
- `docs/`: benchmark design, rule policy, validation policy
- `prompts/`, `schemas/`, `scripts/`: agent prompts, run schemas, helper scripts

## 빠른 시작

WSL에서 실행하는 것을 기준으로 합니다.

```bash
cd /mnt/c/Users/imssh/Documents/TableMagnifier
uv sync
uv run pytest
```

## 실행 예시

Generated family demo:

```bash
uv run python -m table_env_bench.scripts.run_demo --family k_vis_table_arc --level 1 --template-id symbol_rule_induction --seed 0 --agent heuristic
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

Optional API server:

```bash
uv run python -m table_env_bench.scripts.run_server --host 127.0.0.1 --port 8000
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

1. `docs/episode_rulebook.md`, `docs/visual_cue_inventory.md`, `docs/operator_taxonomy.md`, `docs/answer_form_policy.md`, `docs/episode_validation_checklist.md`에서 목표 capability와 evidence path를 먼저 정리합니다.
2. `src/table_env_bench/data/families/<family_id>.py`에 generator module을 만듭니다.
3. module은 최소한 아래 surface를 제공합니다.
   - `FAMILY`
   - `FAMILY_LABEL`
   - `list_manifests(level)`
   - `build_episode(level, seed, *, template_id=None)`
4. `src/table_env_bench/data/families/__init__.py`의 `CANONICAL_FAMILY_ADAPTERS`에 `FamilyAdapter` 하나를 추가합니다.
5. authoring pipeline, static readability audit, pytest를 통과시킵니다.

## Codex Skill

Repo에 포함된 skill source:

```text
docs/skills/tableqa-family-author/SKILL.md
```

Codex가 해당 skill을 인식하지 못하는 환경에서는 repo의 skill directory를 `~/.codex/skills` 아래로 복사해서 추가합니다.

```bash
mkdir -p ~/.codex/skills/tableqa-family-author
cp -R /mnt/c/Users/imssh/Documents/TableMagnifier/docs/skills/tableqa-family-author/. ~/.codex/skills/tableqa-family-author/
```

## 주요 경로

- [src/table_env_bench/env/environment.py](src/table_env_bench/env/environment.py)
- [src/table_env_bench/render/renderer.py](src/table_env_bench/render/renderer.py)
- [src/table_env_bench/render/image_renderer.py](src/table_env_bench/render/image_renderer.py)
- [src/table_env_bench/data/families](src/table_env_bench/data/families)
- [src/table_env_bench/data/families/adapters.py](src/table_env_bench/data/families/adapters.py)
- [src/table_env_bench/data/canonical_catalog.py](src/table_env_bench/data/canonical_catalog.py)
- [src/table_env_bench/data/instances.py](src/table_env_bench/data/instances.py)
- [src/table_env_bench/server/app.py](src/table_env_bench/server/app.py)
