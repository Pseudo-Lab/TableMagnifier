from __future__ import annotations

import math
from typing import Any, Iterable


def _norm_string(value: Any) -> str:
    return str(value).strip().lower()


def is_correct_answer(
    submitted: Any,
    reference: Any,
    answer_type: str = "string",
    tolerance: float | None = None,
) -> bool:
    if submitted is None:
        return False

    if answer_type == "integer":
        try:
            return int(str(submitted).replace(",", "").strip()) == int(reference)
        except Exception:
            return False

    if answer_type == "float":
        tol = 1e-6 if tolerance is None else tolerance
        try:
            return math.isclose(float(str(submitted).replace(",", "").strip()), float(reference), abs_tol=tol, rel_tol=0.0)
        except Exception:
            return False

    if answer_type == "boolean":
        true_values = {"true", "yes", "y", "1"}
        false_values = {"false", "no", "n", "0"}
        s = _norm_string(submitted)
        r = _norm_string(reference)
        if s in true_values:
            s = "true"
        if s in false_values:
            s = "false"
        if r in true_values:
            r = "true"
        if r in false_values:
            r = "false"
        return s == r

    if answer_type == "ordered_list":
        return _as_list(submitted) == _as_list(reference)

    if answer_type == "unordered_set":
        return set(_as_list(submitted)) == set(_as_list(reference))

    return _norm_string(submitted) == _norm_string(reference)


def _as_list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [_norm_string(v) for v in value]
    return [_norm_string(v) for v in str(value).replace(";", ",").split(",") if str(v).strip()]


def efficiency_score(
    action_count: int,
    human_baseline_actions: float | int | None,
    correct: bool,
    power: float = 2.0,
) -> float:
    """Human-normalized action efficiency.

    Wrong answers receive 0. Correct answers are capped at 1.0.
    """
    if not correct:
        return 0.0
    if action_count <= 0:
        raise ValueError("action_count must be positive")
    if human_baseline_actions is None or human_baseline_actions <= 0:
        return 0.0
    ratio = min(1.0, float(human_baseline_actions) / float(action_count))
    return ratio**power


def accuracy(correct_values: Iterable[bool]) -> float:
    vals = list(correct_values)
    if not vals:
        return 0.0
    return sum(1 for x in vals if x) / len(vals)


def mean(values: Iterable[float]) -> float:
    vals = list(values)
    if not vals:
        return 0.0
    return sum(vals) / len(vals)
