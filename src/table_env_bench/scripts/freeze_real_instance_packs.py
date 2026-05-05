"""Freeze public real-data benchmark instance packs from canonical generators."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from table_env_bench.data.generators import FAMILY_LABELS, generate_episode
from table_env_bench.data.loader import save_episode_spec

PACK_SPECS = {
    "public_dev_real_v1": {
        "pack_label": "Public Dev Real V1",
        "version": "1.0",
        "locale": "ko-KR",
        "pack_role": "public",
        "benchmark_track": "canonical_real_tableqa",
        "instances": (
            {
                "family": "channel_policy_transfer",
                "level": 1,
                "template_id": "icon_scope_cell",
                "seed": 0,
                "instance_label": "채널 집행 기준 L1 · 3월 대상 칸",
                "workbook_title": "3월 채널 집행 기준표",
                "question": "사례 시트의 기준을 따르면 현재 채널표에서 집행 대상으로 표시할 칸은 어디인가?",
                "task_summary": "사례 표의 표식 위치를 읽어 현재 채널 운영표에서 집행 대상 칸을 고른다.",
                "expected_failure_mode": "표식 모양만 따라가고 적용 구간을 놓치면 다른 열의 비슷한 칸을 고른다.",
            },
            {
                "family": "channel_policy_transfer",
                "level": 2,
                "template_id": "icon_scope_cell",
                "seed": 0,
                "instance_label": "채널 집행 기준 L2 · 확장 사례",
                "workbook_title": "채널 집행 확대 적용",
                "question": "두 사례를 함께 보면 현재 채널표에서 집행 대상으로 남는 칸은 어디인가?",
                "task_summary": "두 사례 시트를 함께 읽고 공통 집행 기준을 현재 채널표에 적용한다.",
                "expected_failure_mode": "첫 사례만 보고 성급히 일반화하면 두 번째 사례가 제외한 칸을 고른다.",
            },
            {
                "family": "channel_policy_transfer",
                "level": 3,
                "template_id": "icon_scope_cell",
                "seed": 0,
                "instance_label": "채널 집행 기준 L3 · 메모 반영",
                "workbook_title": "채널 집행 기준과 메모",
                "question": "기준 사례와 보조 메모를 함께 반영하면 현재 채널표에서 집행 대상으로 표시할 칸은 어디인가?",
                "task_summary": "사례 시트와 메모 시트의 보조 조건을 결합해 현재 표의 집행 대상을 확정한다.",
                "expected_failure_mode": "보조 메모를 건너뛰면 표식 방향을 반대로 읽고 인접한 칸을 고른다.",
            },
            {
                "family": "channel_policy_transfer",
                "level": 2,
                "template_id": "icon_scope_cell",
                "seed": 1,
                "instance_label": "채널 집행 기준 L2 · 4월 변형",
                "workbook_title": "4월 채널 집행 확대 적용",
                "question": "4월 표로 바뀐 현재 채널표에서 집행 대상으로 남는 칸은 어디인가?",
                "task_summary": "같은 집행 기준을 다른 월 표에 옮겨 적용하는 변형 사례다.",
                "expected_failure_mode": "사례 구조는 맞게 읽어도 행 순서 변화에 끌리면 다른 채널 칸을 고른다.",
            },
            {
                "family": "inventory_exception_disambiguation",
                "level": 1,
                "template_id": "pattern_vs_icon_statement",
                "seed": 0,
                "instance_label": "재고 예외 판정 L1 · 적용 기준",
                "workbook_title": "재고 예외 표시 기준",
                "question": "사례와 예외 시트를 함께 보면 현재 재고표에 대해 맞는 설명은 어느 것인가?",
                "task_summary": "재고 표시 사례와 예외 사례를 비교해 현재 재고표의 판정 문장을 고른다.",
                "expected_failure_mode": "예외 시트를 보지 않으면 사선 표시와 삼각 표식 중 무엇이 기준인지 고정되지 않는다.",
            },
            {
                "family": "inventory_exception_disambiguation",
                "level": 2,
                "template_id": "pattern_vs_icon_statement",
                "seed": 0,
                "instance_label": "재고 예외 판정 L2 · 범위 메모",
                "workbook_title": "재고 예외 범위 확인",
                "question": "예외 시트와 범위 메모를 함께 보면 현재 재고표에 대해 맞는 설명은 어느 것인가?",
                "task_summary": "예외 사례와 범위 메모를 함께 읽고 현재 재고표의 예외 적용 범위를 판정한다.",
                "expected_failure_mode": "표식 기준은 맞혀도 범위 메모를 놓치면 다른 묶음의 설명을 정답으로 고른다.",
            },
            {
                "family": "inventory_exception_disambiguation",
                "level": 3,
                "template_id": "pattern_vs_icon_statement",
                "seed": 0,
                "instance_label": "재고 예외 판정 L3 · 후보 표 선택",
                "workbook_title": "재고 예외 후보 비교",
                "question": "사례, 예외, 보조 단서를 함께 반영했을 때 현재 재고표와 맞는 후보 표는 어느 것인가?",
                "task_summary": "현재 재고표를 읽은 뒤 예외 기준과 맞는 후보 표를 선택한다.",
                "expected_failure_mode": "예외 기준은 이해해도 후보 표의 행 묶음을 대충 보면 비슷한 표를 고른다.",
            },
            {
                "family": "inventory_exception_disambiguation",
                "level": 2,
                "template_id": "pattern_vs_icon_statement",
                "seed": 1,
                "instance_label": "재고 예외 판정 L2 · 창고 변형",
                "workbook_title": "재고 예외 범위 재확인",
                "question": "창고 배치가 달라진 현재 재고표에서 맞는 설명은 어느 것인가?",
                "task_summary": "같은 예외 규칙을 다른 창고 배치 표에 적용하는 변형 사례다.",
                "expected_failure_mode": "행 순서 변화에 끌리면 맞는 규칙을 알고도 다른 창고 설명을 고른다.",
            },
            {
                "family": "report_scope_reconciliation",
                "level": 1,
                "template_id": "merged_scope_cell",
                "seed": 0,
                "instance_label": "보고 범위 판정 L1 · 집계 칸",
                "workbook_title": "지역별 보고 범위 확인",
                "question": "중첩 헤더와 반복된 팀 라벨을 함께 읽으면 찾는 집계 칸은 어디인가?",
                "task_summary": "중첩 헤더와 반복 팀 라벨을 함께 읽어 정확한 집계 칸을 찾는다.",
                "expected_failure_mode": "같은 팀 이름만 따라가면 다른 지역 블록의 같은 칸을 고른다.",
            },
            {
                "family": "report_scope_reconciliation",
                "level": 2,
                "template_id": "grouped_statement",
                "seed": 0,
                "instance_label": "보고 범위 판정 L2 · 소계 설명",
                "workbook_title": "보고 범위와 소계 설명",
                "question": "소계 구간과 보조 메모를 함께 읽으면 맞는 설명은 어느 것인가?",
                "task_summary": "소계 행이 어느 구간을 요약하는지 판단해 맞는 설명을 고른다.",
                "expected_failure_mode": "소계와 총계 경계를 헷갈리면 그럴듯한 설명 오답을 고른다.",
            },
            {
                "family": "report_scope_reconciliation",
                "level": 3,
                "template_id": "subtotal_row_label",
                "seed": 0,
                "instance_label": "보고 범위 판정 L3 · 소계 묶음",
                "workbook_title": "소계 묶음과 범위 확인",
                "question": "소계 행이 실제로 묶는 팀 조합은 어느 것인가?",
                "task_summary": "반복 팀 라벨과 소계 구조를 결합해 실제 묶음 범위를 판정한다.",
                "expected_failure_mode": "지역 헤더를 무시하면 다른 블록의 같은 팀 묶음을 고른다.",
            },
            {
                "family": "report_scope_reconciliation",
                "level": 1,
                "template_id": "grouped_statement",
                "seed": 0,
                "instance_label": "보고 범위 판정 L1 · 그룹 설명",
                "workbook_title": "그룹별 보고 범위 설명",
                "question": "현재 보고표를 읽었을 때 맞는 그룹 설명은 어느 것인가?",
                "task_summary": "중첩 헤더와 그룹 행 구조를 읽어 보고 범위 설명을 고른다.",
                "expected_failure_mode": "헤더 범위보다 눈에 띄는 행 라벨만 따라가면 다른 그룹 설명을 선택한다.",
            },
        ),
    },
    "public_smoke_real_v1": {
        "pack_label": "Public Smoke Real V1",
        "version": "1.0",
        "locale": "ko-KR",
        "pack_role": "public",
        "benchmark_track": "canonical_real_tableqa",
        "instances": (
            {
                "family": "channel_policy_transfer",
                "level": 1,
                "template_id": "icon_scope_cell",
                "seed": 0,
                "instance_label": "smoke · 채널 집행 기준",
                "workbook_title": "smoke 채널 집행 기준",
                "question": "사례 기준을 따르면 현재 채널표에서 집행 대상으로 표시할 칸은 어디인가?",
                "task_summary": "채널 집행 기준 family의 smoke 문제다.",
                "expected_failure_mode": "표식만 보고 적용 구간을 놓친다.",
            },
            {
                "family": "inventory_exception_disambiguation",
                "level": 1,
                "template_id": "pattern_vs_icon_statement",
                "seed": 0,
                "instance_label": "smoke · 재고 예외 판정",
                "workbook_title": "smoke 재고 예외 판정",
                "question": "사례와 예외 시트를 함께 보면 현재 재고표에 대해 맞는 설명은 어느 것인가?",
                "task_summary": "재고 예외 판정 family의 smoke 문제다.",
                "expected_failure_mode": "예외 시트 없이 첫 가설을 유지한다.",
            },
            {
                "family": "report_scope_reconciliation",
                "level": 1,
                "template_id": "merged_scope_cell",
                "seed": 0,
                "instance_label": "smoke · 보고 범위 판정",
                "workbook_title": "smoke 보고 범위 판정",
                "question": "중첩 헤더와 반복 팀 라벨을 함께 읽으면 찾는 집계 칸은 어디인가?",
                "task_summary": "보고 범위 판정 family의 smoke 문제다.",
                "expected_failure_mode": "반복 라벨만 보고 헤더 범위를 무시한다.",
            },
        ),
    },
}


def _pack_dir(repo_root: Path, pack_id: str) -> Path:
    return repo_root / "src" / "table_env_bench" / "data" / "specs" / "instances" / pack_id


def _freeze_pack(repo_root: Path, pack_id: str, config: dict[str, object]) -> dict[str, object]:
    pack_dir = _pack_dir(repo_root, pack_id)
    pack_dir.mkdir(parents=True, exist_ok=True)
    manifest_instances: list[dict[str, object]] = []
    for item in config["instances"]:
        source_spec = generate_episode(item["family"], item["level"], seed=item["seed"], template_id=item["template_id"])
        instance_id = f"{pack_id}__{source_spec.episode_id}"
        metadata = dict(source_spec.metadata)
        metadata.update(
            {
                "instance_id": instance_id,
                "instance_label": item["instance_label"],
                "pack_id": pack_id,
                "pack_role": config["pack_role"],
                "track": config["benchmark_track"],
                "benchmark_track": config["benchmark_track"],
                "difficulty_tier": pack_id,
                "source_track": source_spec.metadata.get("track"),
                "source_episode_id": source_spec.episode_id,
                "source_template_id": item["template_id"],
                "source_seed": item["seed"],
                "task_summary": item["task_summary"],
                "generalization_group": source_spec.metadata.get("generalization_group", f"{source_spec.family}:{item['template_id']}:l{source_spec.level}"),
            }
        )
        frozen_spec = replace(
            source_spec,
            episode_id=instance_id,
            question=item["question"],
            workbook=replace(
                source_spec.workbook,
                title=item["workbook_title"],
                metadata={**source_spec.workbook.metadata, "track": config["benchmark_track"], "benchmark_track": config["benchmark_track"]},
            ),
            metadata=metadata,
        )
        filename = f"{instance_id}.json"
        save_episode_spec(frozen_spec, pack_dir / filename)
        manifest_instances.append(
            {
                "instance_id": instance_id,
                "instance_label": item["instance_label"],
                "family": source_spec.family,
                "family_display_name": FAMILY_LABELS[source_spec.family],
                "level": source_spec.level,
                "source_template_id": item["template_id"],
                "source_seed": item["seed"],
                "source_episode_id": source_spec.episode_id,
                "task_summary": item["task_summary"],
                "decisive_evidence_surfaces": list(source_spec.metadata.get("required_navigation", {}).get("required_page_refs", source_spec.metadata.get("required_page_refs", []))),
                "required_navigation": dict(source_spec.metadata.get("required_navigation", {})),
                "expected_failure_mode": item["expected_failure_mode"],
                "question": frozen_spec.question,
                "workbook_title": frozen_spec.workbook.title,
                "max_actions": frozen_spec.max_actions,
                "sheet_count": len(frozen_spec.workbook.sheets),
                "page_count": sum(len(sheet.pages) for sheet in frozen_spec.workbook.sheets),
                "spec_path": filename,
                "benchmark_track": config["benchmark_track"],
                "reasoning_archetype": frozen_spec.metadata.get("reasoning_archetype"),
                "abstraction_tier": frozen_spec.metadata.get("abstraction_tier"),
                "support_surface_policy": frozen_spec.metadata.get("support_surface_policy"),
                "qa_dependency": frozen_spec.metadata.get("qa_dependency"),
                "generalization_group": frozen_spec.metadata.get("generalization_group"),
                "pack_role": config["pack_role"],
            }
        )
    manifest = {
        "pack_id": pack_id,
        "pack_label": config["pack_label"],
        "version": config["version"],
        "locale": config["locale"],
        "benchmark_track": config["benchmark_track"],
        "pack_role": config["pack_role"],
        "instances": manifest_instances,
    }
    (pack_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"pack_id": pack_id, "manifest": str(pack_dir / "manifest.json"), "count": len(manifest_instances)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze public real-data benchmark instance packs.")
    parser.add_argument("--repo-root", default=Path(__file__).resolve().parents[3], type=Path)
    args = parser.parse_args()
    for pack_id, config in PACK_SPECS.items():
        result = _freeze_pack(args.repo_root.resolve(), pack_id, config)
        print(f"pack={result['pack_id']} count={result['count']} manifest={result['manifest']}")


if __name__ == "__main__":
    main()
