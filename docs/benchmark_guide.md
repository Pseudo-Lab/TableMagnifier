# table-env-bench 벤치마크 가이드

`table-env-bench`는 workbook-style 상호작용 위에서 한국어 `Visual TableQA` 추론을 측정하는 benchmark다. 현재 canonical 기준은 `canonical_real_tableqa` 하나이며, 사람이 읽어도 바로 이해되는 실제 업무형 합성 표를 기본 surface로 사용한다.

## 현재 노출 경로

현재 repo는 frozen `public_*` instance pack을 포함하지 않는다.
workbench와 API의 기본 노출 경로는 generator family catalog이며, hidden holdout은 `TABLE_BENCH_PRIVATE_DATA_DIR` 아래의 별도 instance pack으로 같은 loader 경로를 통해 읽는다.

새 frozen instance pack이 필요하면 `freeze_real_instance_packs`로 별도 release artifact를 만든 뒤, 그 pack을 명시적으로 추가한다.

## 현재 family 우선순위

- `marker_position_rule_transfer`
  - 현재 우선 generator family다.
  - 예시/범례/반례에서 셀 모서리 표식 위치 규칙을 유도하고 query table에 전이한다.

Active canonical/dev family:

- `excel_viewport_sheet_navigation`
  - 넓은 worksheet에서 target column까지 pan/zoom으로 이동해야 하는 viewport navigation 과업이다.

이전 comparison generator family는 canonical registry와 UI/API 노출 경로에서 제거했다.

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
- release blocker는 canonical generator readability audit다. 별도 frozen pack을 만든 release에서는 해당 pack audit도 추가한다.

## 빠르게 실행해 보기

```bash
cd /mnt/c/Users/imssh/Documents/TableMagnifier
uv run pytest
```

```bash
cd /mnt/c/Users/imssh/Documents/TableMagnifier
uv run python -m table_env_bench.scripts.freeze_real_instance_packs
```

```bash
cd /mnt/c/Users/imssh/Documents/TableMagnifier
uv run python -m table_env_bench.scripts.export_preview_gallery --out artifacts/previews_real
```

```bash
cd /mnt/c/Users/imssh/Documents/TableMagnifier
uv run python -m table_env_bench.scripts.audit_readability
```

```bash
cd /mnt/c/Users/imssh/Documents/TableMagnifier
uv run python -m table_env_bench.scripts.audit_readability --smoke --seed-samples 0
```

```bash
cd /mnt/c/Users/imssh/Documents/TableMagnifier/frontend
npm run visual:readability:smoke
```

```bash
cd /mnt/c/Users/imssh/Documents/TableMagnifier
uv run python -m table_env_bench.scripts.eval_baselines --suite canonical_dev
```

## 관련 문서

- [real_data_authoring_policy.md](./real_data_authoring_policy.md)
- [domain_vocab_policy.md](./domain_vocab_policy.md)
- [human_readability_checklist.md](./human_readability_checklist.md)
- [visual_cue_inventory.md](./visual_cue_inventory.md)
- [operator_taxonomy.md](./operator_taxonomy.md)
- [answer_form_policy.md](./answer_form_policy.md)
- [level_design_policy.md](./level_design_policy.md)
