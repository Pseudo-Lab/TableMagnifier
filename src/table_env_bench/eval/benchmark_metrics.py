"""Suite-level benchmark metrics for benchmark-facing reporting."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def raw_accuracy(records: list[dict[str, Any]]) -> float:
    if not records:
        return 0.0
    return sum(float(record["evaluation"]["correctness"]["value"]) for record in records) / len(records)


def generalization_score(records: list[dict[str, Any]]) -> float | None:
    grouped: dict[tuple[str, int], list[float]] = defaultdict(list)
    for record in records:
        evaluation = record.get("evaluation", {})
        coverage = evaluation.get("coverage_slices", {})
        benchmark_track = coverage.get("benchmark_track")
        generalization_group = coverage.get("generalization_group")
        level = coverage.get("level", record.get("level"))
        if benchmark_track != "korean_visual_table_agent_reasoning" or generalization_group is None or level is None:
            continue
        grouped[(str(generalization_group), int(level))].append(float(evaluation["correctness"]["value"]))
    if not grouped:
        return None
    per_group = [sum(values) / len(values) for values in grouped.values()]
    return sum(per_group) / len(per_group)


def slice_breakdown(records: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, float]]]:
    def _aggregate(slice_records: list[dict[str, Any]]) -> dict[str, float]:
        return {
            "count": float(len(slice_records)),
            "raw_accuracy": raw_accuracy(slice_records),
            "generalization_score": generalization_score(slice_records) or 0.0,
        }

    slices: dict[str, dict[str, dict[str, float]]] = {
        "family": {},
        "level": {},
        "reasoning_archetype": {},
        "primary_operator": {},
        "answer_form": {},
        "cue_profile": {},
    }
    families = sorted({str(record["family"]) for record in records})
    for family in families:
        slices["family"][family] = _aggregate([record for record in records if record["family"] == family])
    levels = sorted({int(record["level"]) for record in records})
    for level in levels:
        slices["level"][str(level)] = _aggregate([record for record in records if int(record["level"]) == level])

    def _coverage(record: dict[str, Any]) -> dict[str, Any]:
        return dict(record.get("evaluation", {}).get("coverage_slices", {}))

    reasoning_archetypes = sorted({str(_coverage(record).get("reasoning_archetype")) for record in records if _coverage(record).get("reasoning_archetype")})
    for value in reasoning_archetypes:
        slices["reasoning_archetype"][value] = _aggregate([record for record in records if _coverage(record).get("reasoning_archetype") == value])

    primary_operators = sorted({str(_coverage(record).get("primary_operator")) for record in records if _coverage(record).get("primary_operator")})
    for value in primary_operators:
        slices["primary_operator"][value] = _aggregate([record for record in records if _coverage(record).get("primary_operator") == value])

    answer_forms = sorted({str(_coverage(record).get("answer_form")) for record in records if _coverage(record).get("answer_form")})
    for value in answer_forms:
        slices["answer_form"][value] = _aggregate([record for record in records if _coverage(record).get("answer_form") == value])

    cue_profiles = sorted(
        {
            "|".join(sorted(str(tag) for tag in _coverage(record).get("cue_tags", [])))
            for record in records
            if _coverage(record).get("cue_tags")
        }
    )
    for value in cue_profiles:
        slices["cue_profile"][value] = _aggregate(
            [
                record
                for record in records
                if "|".join(sorted(str(tag) for tag in _coverage(record).get("cue_tags", []))) == value
            ]
        )
    return slices
