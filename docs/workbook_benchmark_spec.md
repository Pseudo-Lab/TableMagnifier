# Workbook Benchmark Spec

이 문서는 현재 구현된 workbook/report 환경 benchmark의 핵심 설계를 요약합니다. Gym 유사 환경 루프, 결정론적 SVG renderer, replay, FastAPI session API, Streamlit human/dev UI를 유지하면서 `workbook/sheet/page/region` 추상화로 동작합니다.

## 방향 메모

이 문서는 환경과 렌더러의 현재 구현을 설명하는 문서입니다.  
장기 benchmark identity는 `Visual TableQA-rooted reasoning benchmark`이며, 다음 원칙을 따른다.

- visually rendered table 또는 worksheet fragment가 핵심 evidence다
- chart, legend, note, appendix는 표를 보조하는 surface다
- 문제는 business lookup-only task로도, pure abstract puzzle로도 흘러가지 않는다
- 구조적 reasoning은 header, row group, marker, filter, subtotal, chart/table alignment 위에서 일어나야 한다

콘텐츠 방향에 대한 자세한 기준은 [PLANS.md](/mnt/c/Users/imssh/Documents/TableMagnifier/PLANS.md)와 [docs/family_design_brief.md](/mnt/c/Users/imssh/Documents/TableMagnifier/docs/family_design_brief.md)를 따른다.

## 현재 코드에서 재사용할 축

- `src/table_env_bench/env/environment.py`
  - reset/step 루프, action budget, replay 연결
- `src/table_env_bench/render/layout.py`
  - 좌표계와 viewport geometry
- `src/table_env_bench/render/renderer.py`
  - 결정론적 SVG 렌더링 백본
- `src/table_env_bench/eval/scoring.py`
  - correctness / efficiency 분리
- `src/table_env_bench/server/`
  - 세션 API와 local human-play 흐름
- `frontend/`
  - human/dev shell의 기반 UI

## 새 핵심 추상화

- episode
  - 질문 하나와 그 질문이 걸린 workbook/report 환경
- workbook
  - 여러 sheet를 가진 보고서 또는 스프레드시트 묶음
- sheet
  - 탭 단위 내비게이션 축
- page
  - 한 sheet 안의 view 또는 pagination 단위
- region
  - agent가 시각적으로 가리키고 환경이 resolve하는 관심 영역
- note
  - 각주, 주석, callout, appendix marker를 통합한 보조 정보

## 환경 상태 모델

현재 `_State`는 `page_index/zoom/center/open_footnote/action_count` 중심입니다. build pass에서는 아래 상태를 기본으로 권장합니다.

- `sheet_index`
- `page_index`
- `zoom_index`
- `center_x`
- `center_y`
- `selected_region_id | None`
- `open_note_id | None`
- `action_count`
- `submitted_answer | None`
- `visited_sheet_keys`
- `visited_page_keys`

종료 상태는 현재처럼 `terminated` / `truncated`를 유지합니다.

## 에이전트 관측 계약

agent mode observation은 workbook을 직접 dump하지 않고, 현재 보이는 화면과 최소 내비게이션 상태만 제공합니다.

- `viewport_svg`
- `question`
- `remaining_action_budget`
- `active_sheet`
- `sheet_tabs`
- `current_page_index`
- `page_count_in_sheet`
- `action_history_summary`

기본적으로 노출 금지:

- hidden workbook spec
- raw spreadsheet text dump
- region map 전체
- answer logic
- invisible note ids
- evaluator metadata

## Workbook / Sheet / Page / Region 추상화

현재 `EpisodeSpec -> PageSpec -> CellSpec` 구조는 table-only MVP에는 적합하지만, workbook-first 목표에는 한 단계 상위 모델이 필요합니다.

권장 계층:

- `WorkbookEpisodeSpec`
  - `episode_id`, `family`, `level`, `seed`, `locale`, `question`, `answer`, `max_actions`
  - `workbook`
- `WorkbookSpec`
  - `title`, `sheets`
- `SheetSpec`
  - `sheet_id`, `tab_label`, `pages`, `metadata`
- `WorkbookPageSpec`
  - `page_id`, `title`, `canvas`, `elements`, `regions`, `notes`, `metadata`
- `ElementSpec`
  - `type`: `table`, `chart`, `legend`, `note_block`, `text_block`, `callout`
- `RegionSpec`
  - `public_id`, `role`, `bbox`, `visible_label`, `linked_note_id`, `metadata`

현재 `CellSpec`은 `TableElementSpec` 내부로 내려가는 것이 자연스럽습니다.

## 결정론적 spec format 제안

현재 JSON 기반 declarative spec 방향을 사용합니다. MVP 구현은 `src/table_env_bench/data/models.py`와 `src/table_env_bench/data/generators.py`를 중심으로 동작하고, sample spec은 `src/table_env_bench/data/specs/`에 둡니다.

아래 예시는 구조 설명용 illustration이며, 현재 canonical real-data family도 같은 상위 구조를 공유해야 합니다.

```json
{
  "episode_id": "channel_policy_transfer_icon_scope_cell_l1_s0",
  "family": "channel_policy_transfer",
  "level": 1,
  "seed": 0,
  "locale": "ko-KR",
  "question": "사례 시트의 기준을 따르면 현재 채널표에서 집행 대상으로 표시할 칸은 어디인가?",
  "max_actions": 9,
  "answer": {"canonical": "B", "normalizer": "ko_answer"},
  "workbook": {
    "title": "채널 집행 기준",
    "sheets": [
      {
        "sheet_id": "examples",
        "tab_label": "사례",
        "pages": [
          {
            "page_id": "examples-p1",
            "title": "사례 시트",
            "elements": [{"type": "table"}, {"type": "text_block"}],
            "regions": [{"public_id": "example-table", "role": "table_region"}],
            "notes": []
          }
        ]
      }
    ]
  }
}
```

## 렌더링 방향

- 기본 렌더러는 계속 SVG를 사용한다
- 차트, 범례, note overlay도 SVG로 렌더링한다
- debug overlay는 renderer 옵션으로만 켠다
- 환경 상태 전이와 렌더링 로직은 현재처럼 분리한다

앞으로의 canonical renderer에서는 아래를 더 강조한다.

- table / worksheet fragment가 메인 evidence area일 것
- merged header, row group, subtotal, marker, filter가 명확히 읽힐 것
- chart/note/legend는 table evidence를 보조할 것
- pure abstract token panel처럼 보이는 표현은 피할 것

현재 `render/layout.py`의 geometry 계산은 그대로 재사용 가능하고, `renderer.py`는 `table renderer`에서 `workbook page renderer`로 일반화하는 것이 적절합니다.

## 현재 저장소 구조

MVP 구현은 아래 구조를 사용합니다.

```text
src/table_env_bench/
  env/
    actions.py
    environment.py
    replay.py
  render/
    layout.py
    renderer.py
  data/
    models.py
    loader.py
    generators.py
    specs/
  eval/
    scoring.py
  baselines/
    random_agent.py
    heuristic_agent.py
    runner.py
  ui/
    app.py
  scripts/
    run_demo.py
    eval_baselines.py
    run_server.py
```

## Test Plan

- workbook spec loading
- renderer determinism for multi-sheet multi-page episodes
- `select_sheet` / `next_page` / `click` 상태 전이
- click이 cell id가 아니라 region으로 resolve되는지 검증
- note overlay open/close 동작
- agent mode에서 debug/oracle 정보가 숨겨지는지 검증
- dev mode에서 region overlay와 spec inspect가 보이는지 검증
- replay export에 sheet/page/region metadata가 남는지 검증
- canonical real-data smoke test와 regression smoke test를 분리해 관리

## 구현 경계

이번 패스는 문서와 리팩터 계획 고정이 목표입니다. 다음 build pass의 최소 구현은 "현재 table prototype을 workbook spec 안에 두되, table-rooted reasoning family를 올릴 수 있는 primitive 계층을 추가"하는 것에서 시작하는 것이 가장 안전합니다.
