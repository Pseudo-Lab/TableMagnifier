# First Steps

현재 저장소의 기본 방향은 `korean_visual_table_agent_reasoning` track 위의 `k_vis_table_arc` family다.

이 benchmark는 정적 한국어 TableQA가 아니라 한국어 시각 테이블 환경에서 에이전트가 다음 능력을 수행하는지 본다.

- rendered table/document viewport 탐색
- 특수 기호와 병합 헤더의 규칙 유도
- 합성 약어 문서 참조
- 넓은 표에서 행/열 evidence 찾기
- 단위 변환과 계산
- action log 기반 evidence coverage와 efficiency 유지

먼저 볼 파일:

1. [docs/task_families.md](./task_families.md)
2. [docs/benchmark_guide.md](./benchmark_guide.md)
3. [src/table_env_bench/data/families/k_vis_table_arc.py](../src/table_env_bench/data/families/k_vis_table_arc.py)
4. [src/table_env_bench/data/families/__init__.py](../src/table_env_bench/data/families/__init__.py)
5. [frontend/src/App.tsx](../frontend/src/App.tsx)

기본 실행:

```bash
uv run python -m table_env_bench.scripts.run_demo --family k_vis_table_arc --level 1 --template-id symbol_rule_induction --seed 0 --agent random
```
