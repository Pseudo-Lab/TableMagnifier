# Runtime Modes

이 문서는 `table-env-bench`의 runtime mode를 현재 기준으로 정리한다. 별도 web UI는 유지하지 않으며, 사람이 확인해야 하는 surface는 Python export artifact와 optional FastAPI session API를 사용한다.

## 1. Dev / Inspector Mode

목적:

- family 개발
- renderer 디버깅
- click resolve / region grounding 검증
- replay 분석

현재 구현:

- `WorkbookEnv(mode="dev")`가 debug-friendly observation을 제공한다.
- [src/table_env_bench/server/app.py](/mnt/c/Users/imssh/Documents/TableMagnifier/src/table_env_bench/server/app.py)가 optional session API를 제공한다.
- [src/table_env_bench/scripts/export_preview_gallery.py](/mnt/c/Users/imssh/Documents/TableMagnifier/src/table_env_bench/scripts/export_preview_gallery.py)가 PNG, scene JSON, `index.html`, `review.html`을 생성한다.

보여도 되는 것:

- region bounding box overlay
- resolved click target
- replay event stream
- last action / last event
- navigation state

보이면 안 되는 것:

- answer canonical
- evaluator internals
- hidden spreadsheet text dump
- oracle metadata

## 2. Human Review Mode

목적:

- 생성 surface 육안 검토
- workbook 탐색 난이도와 evidence 분포 확인
- table text overlap, clipping, invalid layout 검토

기본 경로:

```bash
uv run python -m table_env_bench.scripts.export_preview_gallery --out artifacts/previews_active
```

생성된 `index.html`과 `review.html`은 정적 PNG 기반 review artifact다.

## 3. Agent API Mode

목적:

- 모델 / 에이전트 평가

계약:

- agent는 JSON observation + rendered viewport만 받는다.
- hidden workbook text dump와 oracle metadata는 노출하지 않는다.

보여도 되는 것:

- `viewport_svg`
- `viewport_scene`
- `viewport_image_png_base64`
- `viewport_width`
- `viewport_height`
- `question`
- `remaining_action_budget`
- `current_sheet_name`
- `current_sheet_index`
- `sheet_tabs`
- `current_page_index`
- `page_count_in_sheet`
- `action_history_summary`

보이면 안 되는 것:

- hidden region ids
- raw spreadsheet data
- answer logic
- oracle spec
- debug overlay state

## 구현 메모

- env core는 mode와 무관하게 같은 state transition을 사용한다.
- 사람 검토용 artifact와 agent observation artifact를 혼동하지 않는다.
- release 판단은 `uv run pytest`, `export_preview_gallery`, `audit_readability` 결과를 우선한다.
