# UI Modes

이 문서는 `table-env-bench`의 UI 모드를 현재 기준으로 정리한 문서입니다.

이제 사람용 기본 경로는 `Streamlit`이 아니라 `FastAPI session API + React web UI`입니다.  
즉, human/dev/agent 모드는 모두 같은 environment contract 위에서 동작하고, 차이는 관측 정보와 UI affordance에서 만들어집니다.

## 1. Dev / Inspector mode

목적:

- family 개발
- renderer 디버깅
- click resolve / region grounding 검증
- replay 분석

현재 구현:

- `WorkbookEnv(mode="dev")`가 debug-friendly observation을 제공합니다.
- [src/table_env_bench/server/app.py](/mnt/c/Users/imssh/Documents/TableMagnifier/src/table_env_bench/server/app.py)가 `mode`와 `debug`를 받아 session을 생성합니다.
- [frontend/src/App.tsx](/mnt/c/Users/imssh/Documents/TableMagnifier/frontend/src/App.tsx)는 이벤트 로그, replay, 상태 메타데이터 같은 inspector 성격의 정보를 표시할 수 있습니다.

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

## 2. Human evaluation mode

목적:

- 사람 baseline 수집
- 조작 UX 검증
- workbook 탐색 경험 확인

보여야 하는 것:

- 질문
- sheet tabs
- page navigation
- viewport
- action budget / 진행 상태
- answer input / submit

추가 원칙:

- 중심 evidence surface는 visually rendered table / worksheet fragment여야 합니다.
- chart, note, legend는 보조 근거로만 보여야 합니다.
- debug affordance가 기본 경험을 덮으면 안 됩니다.

보이면 안 되는 것:

- hidden workbook text dump
- answer canonical
- evaluator internals
- debug-only overlay

현재 기본 shell:

- [src/table_env_bench/server/app.py](/mnt/c/Users/imssh/Documents/TableMagnifier/src/table_env_bench/server/app.py)
- [frontend/src/App.tsx](/mnt/c/Users/imssh/Documents/TableMagnifier/frontend/src/App.tsx)

## 3. Agent API mode

목적:

- 모델 / 에이전트 평가

계약:

- transport는 FastAPI session API를 사용합니다.
- agent는 JSON observation + SVG viewport만 받습니다.
- human UI 전용 정보는 최소화합니다.

보여도 되는 것:

- `viewport_svg`
- `question`
- `remaining_action_budget`
- `active_sheet`
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

- env core는 mode와 무관하게 같은 state transition을 사용합니다.
- mode 차이는 observation filtering과 UI rendering에서 만듭니다.
- server layer는 `mode=agent|human|dev`와 `debug`를 받습니다.
- canonical human path는 더 이상 Streamlit이 아니라 FastAPI + React입니다.
