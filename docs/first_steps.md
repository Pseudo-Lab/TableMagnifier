# table-env-bench 첫걸음

가장 짧게 말하면, 지금 이 저장소는 `canonical_real_tableqa` track 위에서 `marker_position_rule_transfer`를 우선 generator family로 운영하는 Visual TableQA reasoning benchmark다.
`report_scope_reconciliation`, `channel_policy_transfer`, `inventory_exception_disambiguation`은 frozen public pack 호환과 회귀 테스트를 위한 deprecated generator family로 남아 있다.

## 먼저 이해할 것

- 표가 중심 evidence다
- merged header, row group, subtotal, example, note가 실제 규칙을 결정한다
- 기본 observation은 `viewport_svg` 중심이다
- workbench와 API는 `public_dev_real_v1`, `public_smoke_real_v1` 인스턴스 팩을 기본 경로로 노출한다

## 먼저 실행할 것

```bash
cd /mnt/c/Users/imssh/Documents/poc_1
uv run pytest
```

```bash
cd /mnt/c/Users/imssh/Documents/poc_1
uv run python -m table_env_bench.scripts.export_preview_gallery --out artifacts/previews_active
```

```bash
cd /mnt/c/Users/imssh/Documents/poc_1
uv run python -m table_env_bench.scripts.audit_readability --pack public_smoke_real_v1
```

```bash
cd /mnt/c/Users/imssh/Documents/poc_1
uv run python -m table_env_bench.scripts.run_server --reload
```

## 먼저 읽을 것

1. [docs/benchmark_guide.md](./benchmark_guide.md)
2. [docs/task_families.md](./task_families.md)
3. [docs/real_data_authoring_policy.md](./real_data_authoring_policy.md)
4. [docs/level_design_policy.md](./level_design_policy.md)
5. [src/table_env_bench/data/families/marker_position_rule_transfer.py](../src/table_env_bench/data/families/marker_position_rule_transfer.py)
6. [src/table_env_bench/data/families/channel_policy_transfer.py](../src/table_env_bench/data/families/channel_policy_transfer.py)
7. [src/table_env_bench/data/families/report_scope_reconciliation.py](../src/table_env_bench/data/families/report_scope_reconciliation.py)
8. [src/table_env_bench/data/families/inventory_exception_disambiguation.py](../src/table_env_bench/data/families/inventory_exception_disambiguation.py)

## 지금 benchmark에서 중요한 질문

- 이 표에서 어느 header scope가 질문 대상인가
- 표식이 셀 안 어느 모서리에 있는지가 어떤 규칙을 뜻하는가
- 예시에서 배운 rule을 query에 그대로 전이할 수 있는가
- 반복되는 팀 라벨 중 어느 지역 블록이 맞는가
- 반례를 보지 않으면 왜 잘못된 규칙이 남는가
- note를 읽지 않으면 왜 정답이 고정되지 않는가

## 참고

pilot / legacy 설계 문서는 역사 기록으로만 보고, 현재 public benchmark의 source-of-truth는 `benchmark_guide`, `task_families`, `real_data_authoring_policy`로 보면 된다.
