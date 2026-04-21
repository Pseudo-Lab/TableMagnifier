"""Correctness and efficiency scoring."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from table_env_bench.data.models import AnswerSpec


@dataclass(frozen=True)
class ScoreComponent:
    name: str
    value: float
    details: dict[str, Any] = field(default_factory=dict)


class TextNormalizer(Protocol):
    def normalize(self, text: str) -> str:
        ...


class EfficiencyScorer(Protocol):
    def score(self, *, action_count: int, max_actions: int, metadata: dict[str, Any] | None = None) -> ScoreComponent:
        ...


class BasicTextNormalizer:
    def normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", text.strip().lower())


class KoreanAnswerNormalizer:
    _suffix_pattern = re.compile(r"(억원|백만원|만원|천원|원|개|건|명|%)$")

    def normalize(self, text: str) -> str:
        normalized = text.strip().lower().replace(",", "")
        normalized = re.sub(r"\s+", "", normalized)
        normalized = normalized.replace("₩", "")
        while normalized and self._suffix_pattern.search(normalized):
            normalized = self._suffix_pattern.sub("", normalized)
        return normalized


class ExactMatchScorer:
    def __init__(
        self,
        normalizer: TextNormalizer | None = None,
        normalizer_registry: dict[str, TextNormalizer] | None = None,
    ) -> None:
        default_normalizer = normalizer or BasicTextNormalizer()
        self.normalizer = default_normalizer
        self.normalizer_registry = {
            "basic": default_normalizer,
            "ko_answer": KoreanAnswerNormalizer(),
        }
        if normalizer_registry:
            self.normalizer_registry.update(normalizer_registry)

    def _resolve_normalizer(self, answer: AnswerSpec) -> TextNormalizer:
        return self.normalizer_registry.get(answer.normalizer, self.normalizer)

    def score(self, prediction: str | None, answer: AnswerSpec) -> ScoreComponent:
        normalizer = self._resolve_normalizer(answer)
        normalized_prediction = normalizer.normalize(prediction or "")
        canonical = normalizer.normalize(answer.canonical)
        accepted = [normalizer.normalize(value) for value in answer.accepted]
        matched = normalized_prediction == canonical or normalized_prediction in accepted
        return ScoreComponent(
            name="correctness",
            value=1.0 if matched else 0.0,
            details={
                "prediction": prediction or "",
                "normalized_prediction": normalized_prediction,
                "canonical": answer.canonical,
                "accepted": list(answer.accepted),
                "normalizer": answer.normalizer,
            },
        )


class ActionCountEfficiencyScorer:
    def score(self, *, action_count: int, max_actions: int, metadata: dict[str, Any] | None = None) -> ScoreComponent:
        bounded_max_actions = max(max_actions, 1)
        base_efficiency = max(0.0, min(1.0, 1.0 - ((action_count - 1) / max(bounded_max_actions - 1, 1))))
        navigation = dict((metadata or {}).get("navigation", {}))
        wrong_sheet_penalty = 0.08 * float(navigation.get("wrong_sheet_visit_count", 0) or 0)
        revisit_penalty = 0.04 * float(navigation.get("revisit_count", 0) or 0)
        evidence_penalty = 0.0
        if navigation.get("premature_submit"):
            evidence_penalty += 0.15
        evidence_penalty += 0.2 * (1.0 - float(navigation.get("evidence_coverage", 1.0) or 0.0))
        if navigation.get("support_surface_compliance") is False:
            evidence_penalty += 0.1
        efficiency = max(0.0, min(1.0, base_efficiency - wrong_sheet_penalty - revisit_penalty - evidence_penalty))
        return ScoreComponent(
            name="navigation_efficiency",
            value=efficiency,
            details={
                "action_count": action_count,
                "max_actions": max_actions,
                "base_efficiency": base_efficiency,
                "navigation_penalty": {"wrong_sheet": wrong_sheet_penalty, "revisit": revisit_penalty},
                "evidence_penalty": evidence_penalty,
                "metadata": metadata or {},
            },
        )


@dataclass(frozen=True)
class EpisodeEvaluation:
    correctness: ScoreComponent
    efficiency: ScoreComponent
    overall: float
    action_count: int
    unique_sheets_visited: int
    unique_pages_visited: int
    navigation_metrics: dict[str, Any] = field(default_factory=dict)
    coverage_slices: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "correctness": {"value": self.correctness.value, "details": self.correctness.details},
            "efficiency": {"value": self.efficiency.value, "details": self.efficiency.details},
            "navigation_efficiency": {"value": self.efficiency.value, "details": self.efficiency.details},
            "overall": self.overall,
            "action_count": self.action_count,
            "unique_sheets_visited": self.unique_sheets_visited,
            "unique_pages_visited": self.unique_pages_visited,
            "navigation_metrics": self.navigation_metrics,
            "coverage_slices": self.coverage_slices,
            "evidence_coverage": self.navigation_metrics.get("evidence_coverage", 1.0),
            "premature_submit": self.navigation_metrics.get("premature_submit", False),
            "missed_required_evidence": self.navigation_metrics.get("missed_required_evidence", []),
            "decisive_evidence_before_submit": self.navigation_metrics.get("decisive_evidence_before_submit", False),
            "correction_surface_visited": self.navigation_metrics.get("correction_surface_visited", True),
            "workflow_discipline": self.navigation_metrics.get("workflow_discipline", 1.0),
            "support_surface_compliance": self.navigation_metrics.get("support_surface_compliance", True),
        }


class EpisodeEvaluator:
    def __init__(
        self,
        *,
        answer_scorer: ExactMatchScorer | None = None,
        efficiency_scorer: EfficiencyScorer | None = None,
        combiner: Callable[[ScoreComponent, ScoreComponent], float] | None = None,
    ) -> None:
        self.answer_scorer = answer_scorer or ExactMatchScorer()
        self.efficiency_scorer = efficiency_scorer or ActionCountEfficiencyScorer()
        self.combiner = combiner or (lambda correctness, efficiency: correctness.value * efficiency.value)

    def evaluate(
        self,
        *,
        prediction: str | None,
        answer: AnswerSpec,
        action_count: int,
        max_actions: int,
        unique_sheets_visited: int = 0,
        unique_pages_visited: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> EpisodeEvaluation:
        correctness = self.answer_scorer.score(prediction, answer)
        efficiency = self.efficiency_scorer.score(action_count=action_count, max_actions=max_actions, metadata=metadata)
        navigation_metrics = dict((metadata or {}).get("navigation", {}))
        coverage_slices = dict((metadata or {}).get("coverage", {}))
        overall = self.combiner(correctness, efficiency)
        return EpisodeEvaluation(
            correctness=correctness,
            efficiency=efficiency,
            overall=overall,
            action_count=action_count,
            unique_sheets_visited=unique_sheets_visited,
            unique_pages_visited=unique_pages_visited,
            navigation_metrics=navigation_metrics,
            coverage_slices=coverage_slices,
        )
