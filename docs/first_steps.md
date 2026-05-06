# table-env-bench 첫걸음

가장 짧게 말하면, 지금 이 저장소는 `canonical_real_tableqa` track 위에서 `marker_position_rule_transfer`를 우선 generator family로 운영하는 Visual TableQA reasoning benchmark다.
`report_scope_reconciliation`, `channel_policy_transfer`, `inventory_exception_disambiguation`은 회귀 테스트와 비교용 deprecated generator family로 남아 있다.

## 먼저 이해할 것

- 표가 중심 evidence다
- merged header, row group, subtotal, example, note가 실제 규칙을 결정한다
- 기본 observation은 `viewport_svg` 중심이다
- workbench와 API는 기본적으로 generator family catalog를 노출한다

## 먼저 실행할 것

```bash
cd /mnt/c/Users/imssh/Documents/TableMagnifier
uv run pytest
```

```bash
cd /mnt/c/Users/imssh/Documents/TableMagnifier
uv run python -m table_env_bench.scripts.export_preview_gallery --out artifacts/previews_active
```

```bash
cd /mnt/c/Users/imssh/Documents/TableMagnifier
uv run python -m table_env_bench.scripts.audit_readability --smoke --seed-samples 0
```

```bash
cd /mnt/c/Users/imssh/Documents/TableMagnifier
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

## 새 family 추가 방식

새 canonical family는 `src/table_env_bench/data/families/<family_id>.py`에 generator module로 만들고, `src/table_env_bench/data/families/__init__.py`의 `CANONICAL_FAMILY_ADAPTERS`에 `FamilyAdapter` 하나를 추가한다.

family module은 최소한 아래 surface를 제공해야 한다.

- `FAMILY`
- `FAMILY_LABEL`
- `list_manifests(level)`
- `build_episode(level, seed, *, template_id=None)`

`CANONICAL_FAMILY_LABELS`, `CANONICAL_MANIFEST_LISTERS`, `CANONICAL_BUILDERS`는 adapter 목록에서 파생되므로 직접 수정하지 않는다.

Codex로 문제 family를 만들 때는 `$tableqa-family-author` skill을 먼저 호출하면 현재 rule docs, adapter pattern, validation checklist 순서로 진행할 수 있다.

## 지금 benchmark에서 중요한 질문

- 이 표에서 어느 header scope가 질문 대상인가
- 표식이 셀 안 어느 모서리에 있는지가 어떤 규칙을 뜻하는가
- 예시에서 배운 rule을 query에 그대로 전이할 수 있는가
- 반복되는 팀 라벨 중 어느 지역 블록이 맞는가
- 반례를 보지 않으면 왜 잘못된 규칙이 남는가
- note를 읽지 않으면 왜 정답이 고정되지 않는가

## 참고

pilot / legacy 설계 문서는 역사 기록으로만 보고, 현재 public benchmark의 source-of-truth는 `benchmark_guide`, `task_families`, `real_data_authoring_policy`로 보면 된다.
