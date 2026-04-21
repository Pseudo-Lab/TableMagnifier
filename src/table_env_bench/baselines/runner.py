"""Helpers for running agents against the benchmark."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from table_env_bench.env.environment import WorkbookEnv
from table_env_bench.eval.scoring import EpisodeEvaluation, EpisodeEvaluator


class Agent(Protocol):
    name: str

    def reset(self, observation: dict[str, Any], info: dict[str, Any]) -> None:
        ...

    def act(self, observation: dict[str, Any], info: dict[str, Any]):
        ...


@dataclass(frozen=True)
class EpisodeRunResult:
    agent_name: str
    episode_id: str
    prediction: str | None
    terminated: bool
    truncated: bool
    evaluation: EpisodeEvaluation
    replay_path: str | None
    run_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "episode_id": self.episode_id,
            "prediction": self.prediction,
            "terminated": self.terminated,
            "truncated": self.truncated,
            "evaluation": self.evaluation.to_dict(),
            "replay_path": self.replay_path,
            "run_metadata": self.run_metadata,
        }


def run_episode(
    env: WorkbookEnv,
    agent: Agent,
    *,
    evaluator: EpisodeEvaluator | None = None,
    replay_path: str | None = None,
) -> EpisodeRunResult:
    evaluator = evaluator or EpisodeEvaluator()
    observation, info = env.reset()
    agent.reset(observation, info)
    terminated = False
    truncated = False
    while not (terminated or truncated):
        action = agent.act(observation, info)
        observation, _, terminated, truncated, info = env.step(action)

    exported_replay = env.export_replay(replay_path) if replay_path else None
    replay_metrics = env.replay.metrics(env.spec.metadata)
    coverage = {
        "family": env.spec.family,
        "level": env.spec.level,
        "template_id": env.spec.metadata.get("template_id"),
        "pack_id": env.spec.metadata.get("pack_id"),
        "instance_id": env.spec.metadata.get("instance_id"),
        "instance_label": env.spec.metadata.get("instance_label"),
        "difficulty_tier": env.spec.metadata.get("difficulty_tier"),
        "required_capabilities": list(env.spec.metadata.get("required_capabilities", [])),
        "operator_tags": list(env.spec.metadata.get("operator_tags", [])),
        "cue_tags": list(env.spec.metadata.get("cue_tags", [])),
        "answer_form": env.spec.metadata.get("answer_form"),
        "shortcut_probes": list(env.spec.metadata.get("shortcut_probes", [])),
        "track": env.spec.metadata.get("track"),
        "benchmark_track": env.spec.metadata.get("benchmark_track", env.spec.metadata.get("track")),
        "reasoning_archetype": env.spec.metadata.get("reasoning_archetype"),
        "abstraction_tier": env.spec.metadata.get("abstraction_tier"),
        "support_surface_policy": env.spec.metadata.get("support_surface_policy"),
        "qa_dependency": env.spec.metadata.get("qa_dependency"),
        "generalization_group": env.spec.metadata.get("generalization_group"),
    }
    evaluation = evaluator.evaluate(
        prediction=env.submitted_answer,
        answer=env.spec.answer,
        action_count=env.replay.action_count,
        max_actions=env.spec.max_actions,
        unique_sheets_visited=env.unique_sheets_visited,
        unique_pages_visited=env.unique_pages_visited,
        metadata={"agent": agent.name, "family": env.spec.family, "level": env.spec.level, "navigation": replay_metrics, "coverage": coverage},
    )
    run_metadata = {}
    metadata_getter = getattr(agent, "run_metadata", None)
    if callable(metadata_getter):
        run_metadata = dict(metadata_getter())
    return EpisodeRunResult(
        agent_name=agent.name,
        episode_id=env.spec.episode_id,
        prediction=env.submitted_answer,
        terminated=terminated,
        truncated=truncated,
        evaluation=evaluation,
        replay_path=exported_replay,
        run_metadata=run_metadata,
    )
