"""Replay logging and export."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _rect_right(rect: dict[str, Any]) -> float:
    return float(rect.get("x", 0.0)) + float(rect.get("width", 0.0))


def _rect_bottom(rect: dict[str, Any]) -> float:
    return float(rect.get("y", 0.0)) + float(rect.get("height", 0.0))


def _intersection_area(a: dict[str, Any], b: dict[str, Any]) -> float:
    overlap_x = max(0.0, min(_rect_right(a), _rect_right(b)) - max(float(a.get("x", 0.0)), float(b.get("x", 0.0))))
    overlap_y = max(0.0, min(_rect_bottom(a), _rect_bottom(b)) - max(float(a.get("y", 0.0)), float(b.get("y", 0.0))))
    return overlap_x * overlap_y


def viewport_target_matches(*, viewbox: dict[str, Any], target_rect: dict[str, Any], match: str) -> bool:
    """Return whether one target rect is covered by the current viewport.

    This function is intentionally pure so replay and static validation can
    share the same viewport-target matching semantics.
    """

    if match == "viewbox_intersects_target":
        return _intersection_area(viewbox, target_rect) > 0.0
    if match == "target_center_in_viewbox":
        center_x = float(target_rect.get("x", 0.0)) + (float(target_rect.get("width", 0.0)) / 2.0)
        center_y = float(target_rect.get("y", 0.0)) + (float(target_rect.get("height", 0.0)) / 2.0)
        return (
            float(viewbox.get("x", 0.0)) <= center_x <= _rect_right(viewbox)
            and float(viewbox.get("y", 0.0)) <= center_y <= _rect_bottom(viewbox)
        )
    return False


def viewport_state_matches_event(
    required_state: dict[str, Any],
    event_state: dict[str, Any],
    cumulative_action_types: set[str],
) -> bool:
    """Return whether an event after-state satisfies a required viewport state."""

    if event_state.get("sheet_id", event_state.get("sheet_name")) != required_state.get("sheet_id"):
        return False
    if event_state.get("page_id") != required_state.get("page_id"):
        return False
    if int(event_state.get("zoom_index", 0)) < int(required_state.get("min_zoom_index", 0)):
        return False
    required_action_types = {str(action_type) for action_type in required_state.get("required_action_types", [])}
    if not required_action_types.issubset(cumulative_action_types):
        return False
    viewbox = event_state.get("viewbox")
    if not isinstance(viewbox, dict):
        return False
    match_mode = str(required_state.get("match", "target_center_in_viewbox"))
    target_rects = list(required_state.get("target_rects", []))
    for target in target_rects:
        rect = target.get("rect") if isinstance(target, dict) else None
        if not isinstance(rect, dict) or not viewport_target_matches(viewbox=viewbox, target_rect=rect, match=match_mode):
            return False
    return True


def matched_required_viewport_state_ids(
    required_viewport_states: list[dict[str, Any]],
    events: list["ReplayEvent"],
) -> list[str]:
    """Return required viewport-state ids matched by replay events in visit order."""

    matched: list[str] = []
    matched_set: set[str] = set()
    cumulative_action_types: set[str] = set()
    for event in events:
        action_type = event.action.get("type")
        if action_type is not None:
            cumulative_action_types.add(str(action_type))
        for required_state in required_viewport_states:
            state_id = str(required_state.get("state_id", ""))
            if not state_id or state_id in matched_set:
                continue
            if viewport_state_matches_event(required_state, event.after, cumulative_action_types):
                matched_set.add(state_id)
                matched.append(state_id)
    return matched


@dataclass
class ReplayEvent:
    step_index: int
    action: dict[str, Any]
    before: dict[str, Any]
    after: dict[str, Any]
    reward: float
    terminated: bool
    truncated: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "step_index": self.step_index,
            "action": self.action,
            "before": self.before,
            "after": self.after,
            "reward": self.reward,
            "terminated": self.terminated,
            "truncated": self.truncated,
        }
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


@dataclass
class ReplayTrace:
    episode_id: str
    family: str
    level: int
    seed: int
    workbook_id: str
    workbook_title: str
    initial_sheet_name: str | None = None
    initial_sheet_id: str | None = None
    initial_page_id: str | None = None
    events: list[ReplayEvent] = field(default_factory=list)

    def append(self, event: ReplayEvent) -> None:
        self.events.append(event)

    @property
    def action_count(self) -> int:
        return len(self.events)

    @property
    def unique_sheets_visited(self) -> int:
        sheets = {
            event.after.get("sheet_id", event.after.get("sheet_name"))
            for event in self.events
            if event.after.get("sheet_id") is not None or event.after.get("sheet_name") is not None
        }
        if self.initial_sheet_id is not None:
            sheets.add(self.initial_sheet_id)
        elif self.initial_sheet_name is not None:
            sheets.add(self.initial_sheet_name)
        return len(sheets)

    @property
    def unique_pages_visited(self) -> int:
        pages = {
            f'{event.after.get("sheet_id", event.after.get("sheet_name"))}:{event.after.get("page_id")}'
            for event in self.events
            if (event.after.get("sheet_id") is not None or event.after.get("sheet_name") is not None)
            and event.after.get("page_id") is not None
        }
        initial_sheet_key = self.initial_sheet_id or self.initial_sheet_name
        if initial_sheet_key is not None and self.initial_page_id is not None:
            pages.add(f"{initial_sheet_key}:{self.initial_page_id}")
        return len(pages)

    def metrics(self, episode_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        episode_metadata = episode_metadata or {}
        page_visits: list[str] = []
        initial_sheet_key = self.initial_sheet_id or self.initial_sheet_name
        if initial_sheet_key is not None and self.initial_page_id is not None:
            page_visits.append(f"{initial_sheet_key}:{self.initial_page_id}")
        clicked_region_ids: set[str] = set()
        opened_note_ids: set[str] = set()
        for event in self.events:
            sheet_key = event.after.get("sheet_id", event.after.get("sheet_name"))
            page_id = event.after.get("page_id")
            if sheet_key is not None and page_id is not None:
                page_visits.append(f"{sheet_key}:{page_id}")
            resolved_region = event.metadata.get("resolved_region") or {}
            if resolved_region.get("public_id") is not None:
                clicked_region_ids.add(str(resolved_region["public_id"]))
            if event.metadata.get("opened_note") is not None:
                opened_note_ids.add(str(event.metadata["opened_note"]))
        page_switch_count = sum(1 for event in self.events if event.before.get("page_id") != event.after.get("page_id"))
        sheet_switch_count = sum(1 for event in self.events if event.before.get("sheet_id", event.before.get("sheet_name")) != event.after.get("sheet_id", event.after.get("sheet_name")))
        note_open_count = sum(1 for event in self.events if event.metadata.get("opened_note") is not None)
        revisit_count = max(len(page_visits) - len(set(page_visits)), 0)
        answer_submit_step = next((event.step_index for event in self.events if event.action.get("type") == "submit_answer"), None)

        relevant_region_ids = set((episode_metadata or {}).get("relevant_region_ids", []))
        first_relevant_region_step = None
        if relevant_region_ids:
            for event in self.events:
                resolved_region = event.metadata.get("resolved_region") or {}
                if resolved_region.get("public_id") in relevant_region_ids:
                    first_relevant_region_step = event.step_index
                    break

        required_navigation = dict(episode_metadata.get("required_navigation", {}))
        required_sheet_ids = set(required_navigation.get("required_sheet_ids", []))
        required_page_refs = set(required_navigation.get("required_page_refs", []))
        required_notes = list(required_navigation.get("required_notes", []))
        required_note_ids = {
            str(item.get("note_id"))
            for item in required_notes
            if isinstance(item, dict) and item.get("note_id") is not None
        }
        required_viewport_states = [
            dict(item) for item in required_navigation.get("required_viewport_states", []) if isinstance(item, dict)
        ]
        visited_viewport_states = matched_required_viewport_state_ids(required_viewport_states, self.events)
        visited_viewport_state_set = set(visited_viewport_states)
        visited_sheet_ids = {initial_sheet_key} if initial_sheet_key is not None else set()
        for event in self.events:
            sheet_id = event.after.get("sheet_id", event.after.get("sheet_name"))
            if sheet_id is not None:
                visited_sheet_ids.add(sheet_id)
        wrong_sheet_visit_count = len({sheet_id for sheet_id in visited_sheet_ids if required_sheet_ids and sheet_id not in required_sheet_ids})

        required_evidence = list(episode_metadata.get("required_evidence", []))
        visited_page_refs = set(page_visits)
        evidence_hits: list[dict[str, Any]] = []
        for item in required_evidence:
            kind = str(item.get("kind", "page"))
            matched = False
            if kind == "sheet":
                matched = str(item.get("sheet_id")) in visited_sheet_ids
            elif kind == "page":
                matched = f"{item.get('sheet_id')}:{item.get('page_id')}" in visited_page_refs
            elif kind == "region":
                matched = str(item.get("region_id")) in clicked_region_ids
            elif kind == "note":
                matched = str(item.get("note_id")) in opened_note_ids
            evidence_hits.append({"kind": kind, "matched": matched, "target": dict(item)})

        evidence_hit_count = sum(1 for item in evidence_hits if item["matched"])
        evidence_coverage = 1.0 if not evidence_hits else evidence_hit_count / len(evidence_hits)
        missed_required_evidence = [item["target"] for item in evidence_hits if not item["matched"]]
        premature_submit = answer_submit_step is not None and bool(missed_required_evidence)
        decisive_evidence_before_submit = answer_submit_step is not None and not missed_required_evidence

        required_actions = set(episode_metadata.get("required_actions", []))
        must_visit_exception = "must_visit_exception" in required_actions
        must_open_note = "must_open_note" in required_actions
        must_switch_sheet = "must_switch_sheet" in required_actions
        navigation_sheet_compliance = required_sheet_ids.issubset(visited_sheet_ids)
        navigation_page_compliance = required_page_refs.issubset(visited_page_refs)
        navigation_note_compliance = required_note_ids.issubset(opened_note_ids)
        required_viewport_state_ids = {
            str(item.get("state_id")) for item in required_viewport_states if item.get("state_id") is not None
        }
        navigation_viewport_compliance = required_viewport_state_ids.issubset(visited_viewport_state_set)
        support_surface_compliance = (
            navigation_sheet_compliance
            and navigation_page_compliance
            and navigation_note_compliance
            and navigation_viewport_compliance
        )
        if not required_navigation:
            support_surface_compliance = True
            if must_visit_exception:
                support_surface_compliance = any(":exception-" in page_ref for page_ref in visited_page_refs)
            if must_open_note:
                support_surface_compliance = support_surface_compliance and note_open_count > 0
            if must_switch_sheet:
                support_surface_compliance = support_surface_compliance and sheet_switch_count > 0

        correction_surface_visited = True
        correction_targets: list[dict[str, Any]] = []
        for item in required_evidence:
            if item.get("kind") not in {"page", "note"}:
                continue
            sheet_id = str(item.get("sheet_id", ""))
            page_id = str(item.get("page_id", ""))
            if sheet_id in {"exception", "appendix", "notes"} or page_id.endswith("p2"):
                correction_targets.append(item)
        if correction_targets:
            correction_surface_visited = any(
                hit["matched"] for hit in evidence_hits if hit["target"] in correction_targets
            )

        workflow_discipline = 1.0
        workflow_discipline -= 0.08 * float(wrong_sheet_visit_count)
        workflow_discipline -= 0.04 * float(revisit_count)
        if not correction_surface_visited or (must_open_note and note_open_count == 0) or (must_switch_sheet and sheet_switch_count == 0):
            workflow_discipline -= 0.12
        workflow_discipline = max(0.0, min(1.0, workflow_discipline))

        return {
            "sheet_switch_count": sheet_switch_count,
            "page_switch_count": page_switch_count,
            "note_open_count": note_open_count,
            "wrong_sheet_visit_count": wrong_sheet_visit_count,
            "revisit_count": revisit_count,
            "first_relevant_region_step": first_relevant_region_step,
            "answer_submit_step": answer_submit_step,
            "evidence_coverage": evidence_coverage,
            "missed_required_evidence": missed_required_evidence,
            "premature_submit": premature_submit,
            "decisive_evidence_before_submit": decisive_evidence_before_submit,
            "correction_surface_visited": correction_surface_visited,
            "workflow_discipline": workflow_discipline,
            "support_surface_compliance": support_surface_compliance,
            "visited_viewport_states": visited_viewport_states,
            "missed_required_navigation": {
                "sheet_ids": sorted(required_sheet_ids - visited_sheet_ids),
                "page_refs": sorted(required_page_refs - visited_page_refs),
                "note_ids": sorted(required_note_ids - opened_note_ids),
                "viewport_state_ids": sorted(required_viewport_state_ids - visited_viewport_state_set),
            },
        }

    def to_dict(self, episode_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "family": self.family,
            "level": self.level,
            "seed": self.seed,
            "workbook_id": self.workbook_id,
            "workbook_title": self.workbook_title,
            "initial_sheet_name": self.initial_sheet_name,
            "initial_sheet_id": self.initial_sheet_id,
            "initial_page_id": self.initial_page_id,
            "action_count": self.action_count,
            "unique_sheets_visited": self.unique_sheets_visited,
            "unique_pages_visited": self.unique_pages_visited,
            "metrics": self.metrics(episode_metadata),
            "events": [event.to_dict() for event in self.events],
        }

    def export_json(self, path: str | Path, episode_metadata: dict[str, Any] | None = None) -> Path:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(self.to_dict(episode_metadata), indent=2, ensure_ascii=False), encoding="utf-8")
        return file_path
