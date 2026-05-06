"""Freeze candidate real-data benchmark instance packs from canonical generators."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from table_env_bench.data.generators import FAMILY_LABELS, generate_episode
from table_env_bench.data.loader import save_episode_spec

PACK_SPECS = {
    "candidate_dev_real_v1": {
        "pack_label": "Candidate Dev Real V1",
        "version": "1.0",
        "locale": "ko-KR",
        "pack_role": "candidate",
        "benchmark_track": "canonical_real_tableqa",
        "instances": (
            {
                "family": "marker_position_rule_transfer",
                "level": 1,
                "template_id": "corner_anchor_statement",
                "seed": 0,
                "instance_label": "표식 위치 규칙 L1",
                "workbook_title": "표식 위치 규칙 전이",
                "question": "예시, 범례, 반례를 함께 보면 질의 표에 대한 올바른 설명은 어느 것인가?",
                "task_summary": "셀 모서리 표식 위치 규칙을 유도해 질의 표에 전이한다.",
                "expected_failure_mode": "표식 모양만 보고 위치 의미를 무시하면 wrong statement를 고른다.",
            },
            {
                "family": "marker_position_rule_transfer",
                "level": 3,
                "template_id": "corner_anchor_statement",
                "seed": 0,
                "instance_label": "표식 위치 규칙 L3 · 메모 반영",
                "workbook_title": "표식 위치 규칙과 적용 묶음",
                "question": "범례와 반례 메모까지 반영하면 질의 표에 대한 올바른 설명은 어느 것인가?",
                "task_summary": "범례, 반례, note를 결합해 표식 위치 규칙과 적용 묶음을 확정한다.",
                "expected_failure_mode": "note를 건너뛰면 적용 묶음을 잘못 잡아 다른 설명을 고른다.",
            },
            {
                "family": "excel_viewport_sheet_navigation",
                "level": 1,
                "template_id": "wide_sheet_rule_transfer",
                "seed": 0,
                "instance_label": "스프레드시트 뷰포트 탐색 L1",
                "workbook_title": "넓은 시트 target column 탐색",
                "question": "사례의 열 이동 규칙을 적용하면 질의 시트의 target column에서 어느 값이 맞는가?",
                "task_summary": "초기 viewport 밖 target column까지 zoom/pan으로 이동해 값을 확인한다.",
                "expected_failure_mode": "초기 viewport만 보고 제출하면 target column evidence를 놓친다.",
            },
        ),
    }
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
    parser = argparse.ArgumentParser(description="Freeze candidate real-data benchmark instance packs.")
    parser.add_argument("--repo-root", default=Path(__file__).resolve().parents[3], type=Path)
    args = parser.parse_args()
    for pack_id, config in PACK_SPECS.items():
        result = _freeze_pack(args.repo_root.resolve(), pack_id, config)
        print(f"pack={result['pack_id']} count={result['count']} manifest={result['manifest']}")


if __name__ == "__main__":
    main()
