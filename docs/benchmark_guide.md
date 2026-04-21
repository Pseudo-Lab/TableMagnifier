# table-env-bench 벤치마크 가이드

`table-env-bench`는 workbook-style 상호작용 위에서 한국어 `Visual TableQA` 추론을 측정하는 benchmark다. 현재 canonical 기준은 `canonical_real_tableqa` 하나이며, 사람이 읽어도 바로 이해되는 실제 업무형 합성 표를 기본 surface로 사용한다.

## 현재 public pack

- `public_dev_real_v1`
  - 12문항
  - family당 4문항
- `public_smoke_real_v1`
  - 3문항
  - family당 1문항

hidden holdout은 `TABLE_BENCH_PRIVATE_DATA_DIR` 아래의 별도 instance pack으로 같은 loader 경로를 통해 읽는다.

## 현재 family

- `channel_policy_transfer`
  - 사례 표의 집행 기준을 현재 채널표에 옮겨 적용한다.
- `inventory_exception_disambiguation`
  - 재고 표시 사례와 예외 사례를 비교해 현재 재고표의 해석을 확정한다.
- `report_scope_reconciliation`
  - 중첩 헤더, 반복 팀 라벨, 소계 구조를 읽고 올바른 보고 범위를 고른다.

세 family 모두 table/worksheet evidence가 중심이고, note나 보조 시트는 실제 범위를 좁히는 용도로만 쓴다.

## 무엇을 측정하나

- visually rendered table에서 relevant scope를 찾는 능력
- headers, row groups, markers, notes를 함께 읽는 능력
- 여러 시트와 페이지에 흩어진 evidence를 합쳐 답을 정하는 능력
- text-only shortcut 없이 실제 viewport를 읽는 능력

headline metric은 아래 세 가지다.

- `overall`
- `raw_accuracy`
- `generalization_score`

`generalization_score`는 `generalization_group x level` 기준의 balanced mean accuracy다.

## Integrity Rules

- 모든 canonical surface는 zero-overlap이어야 한다.
- `invalidLayout == false`, `layoutErrors == []`가 기본 기준이다.
- 미세 겹침이나 heading collision도 허용하지 않는다.
- text가 안 들어가면 자동 축소로 숨기지 않고 copy나 layout을 다시 설계한다.
- release blocker는 `public_smoke_real_v1`, `public_dev_real_v1`의 public pack readability audit다.

## 빠르게 실행해 보기

```bash
cd /path/to/table-env-bench
uv run pytest
```

```bash
cd /path/to/table-env-bench
uv run python -m table_env_bench.scripts.freeze_real_instance_packs
```

```bash
cd /path/to/table-env-bench
uv run python -m table_env_bench.scripts.export_preview_gallery --out artifacts/previews_real --pack public_dev_real_v1
```

```bash
cd /path/to/table-env-bench
uv run python -m table_env_bench.scripts.audit_readability
```

```bash
cd /path/to/table-env-bench
uv run python -m table_env_bench.scripts.audit_readability --pack public_smoke_real_v1
```

```bash
cd /path/to/table-env-bench
uv run python -m table_env_bench.scripts.audit_readability --pack public_dev_real_v1
```

```bash
cd /path/to/table-env-bench
uv run python -m table_env_bench.scripts.audit_readability --pack public_dev_real_v1 --instance-id public_dev_real_v1__channel_policy_transfer_icon_scope_cell_l2_s0
```

```bash
cd /path/to/table-env-bench/frontend
npm run visual:readability:public-smoke
```

```bash
cd /path/to/table-env-bench/frontend
npm run visual:readability:public-dev
```

```bash
cd /path/to/table-env-bench
uv run python -m table_env_bench.scripts.eval_baselines --suite public_dev_real_v1
```

## 관련 문서

- [real_data_authoring_policy.md](./real_data_authoring_policy.md)
- [domain_vocab_policy.md](./domain_vocab_policy.md)
- [human_readability_checklist.md](./human_readability_checklist.md)
- [visual_cue_inventory.md](./visual_cue_inventory.md)
- [operator_taxonomy.md](./operator_taxonomy.md)
- [answer_form_policy.md](./answer_form_policy.md)
- [level_design_policy.md](./level_design_policy.md)
