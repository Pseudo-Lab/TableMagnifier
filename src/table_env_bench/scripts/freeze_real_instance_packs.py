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
        "benchmark_track": "korean_visual_table_agent_reasoning",
        "instances": (
            {
                "family": "k_vis_table_arc",
                "level": 1,
                "template_id": "symbol_rule_induction",
                "seed": 0,
                "instance_label": "기호 규칙 유도 L1",
                "workbook_title": "기호 규칙 유도",
                "question": "완성 행에서 특수 기호 규칙을 유도했을 때 질의 행의 합계는 원 단위로 얼마인가?",
                "task_summary": "완성된 행을 보고 기호 의미를 유도한 뒤 미완성 행에 적용한다.",
                "expected_failure_mode": "기호가 붙은 셀과 붙지 않은 셀을 구분하지 못하면 오답을 낸다.",
            },
            {
                "family": "k_vis_table_arc",
                "level": 2,
                "template_id": "abbrev_doc_reference",
                "seed": 0,
                "instance_label": "약어 문서 참조 L2",
                "workbook_title": "합성 약어 문서 참조",
                "question": "서울A 지점의 총계약조정액에 권역 보정계수를 반영한 금액은 원 단위로 얼마인가?",
                "task_summary": "메인 표의 합성 약어를 별도 문서에서 해석하고 단위를 변환해 계산한다.",
                "expected_failure_mode": "약어 문서를 보지 않으면 TCA 단위와 K-Adj 적용 방식을 놓친다.",
            },
            {
                "family": "k_vis_table_arc",
                "level": 3,
                "template_id": "wide_table_navigation",
                "seed": 0,
                "instance_label": "넓은 테이블 탐색 L3",
                "workbook_title": "넓은 테이블 탐색 계산",
                "question": "부산권 B2B 채널에서 2024년 3분기 신규 계약액과 2025년 1분기 해지 환급액의 차이를 원 단위로 구하라.",
                "task_summary": "유사한 열명과 단위를 구분하며 넓은 테이블에서 필요한 값을 찾는다.",
                "expected_failure_mode": "계약액/계약건수 또는 천 원/원 단위를 혼동하면 오답을 낸다.",
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
