# Benchmark Spec

Deprecated: 이 문서는 하위 호환용 요약 포인터입니다. 현재 환경/렌더러 source-of-truth는 [workbook_benchmark_spec.md](./workbook_benchmark_spec.md)이고, content direction은 family/rule/policy 문서 세트를 따릅니다. 문서 상태는 [document_status.md](./document_status.md)를 참고하세요.

현재 구현의 환경/렌더러 source of truth는 [workbook_benchmark_spec.md](./workbook_benchmark_spec.md)입니다.

다만 benchmark의 장기 content direction은 별도 문서에서 정의합니다.

- [PLANS.md](../PLANS.md)
- [task_families.md](./task_families.md)
- [episode_rulebook.md](./episode_rulebook.md)
- [primitive_glossary.md](./primitive_glossary.md)
- [episode_validation_checklist.md](./episode_validation_checklist.md)

요약하면 현재 benchmark의 기준은 다음과 같습니다.

- 구현 바탕은 workbook/sheet/page/region 환경이다
- 문제 바탕은 `Visual TableQA`다
- visually rendered table 또는 worksheet fragment가 핵심 evidence여야 한다
- chart, legend, note, appendix는 표를 보조하는 surface다
- 현재 canonical track은 `korean_visual_table_agent_reasoning`이다
- 기본 benchmark-facing 실행 단위는 `k_vis_table_arc` generator family와 `canonical_dev` generated suite catalog다
- lookup-only business task나 pure abstract puzzle로 가지 않는다

## 현재 구현 요약

- `WorkbookEnv.reset()` / `step()` 기반 Gym 유사 인터페이스
- workbook -> sheet -> page -> region 추상화
- `select_sheet / next_page / prev_page / zoom / pan / click_region / submit_answer` 액션
- deterministic SVG viewport와 agent observation용 PNG viewport
- 현재 canonical generator family: `k_vis_table_arc`
- 현재 generated suite: `canonical_dev`
- dev / human / agent mode 분리
