"""Gym-like workbook environment."""

from __future__ import annotations

from dataclasses import dataclass, field
from copy import deepcopy
from typing import Any

from table_env_bench.data.generators import generate_episode
from table_env_bench.data.models import EpisodeSpec, NoteSpec, PageSpec, RegionSpec, SheetSpec
from table_env_bench.env.actions import WorkbookAction, parse_action
from table_env_bench.env.replay import ReplayEvent, ReplayTrace
from table_env_bench.eval.scoring import ExactMatchScorer
from table_env_bench.render.image_renderer import SceneImageRenderer
from table_env_bench.render.layout import Rect, find_region_at_point, make_outer_viewbox
from table_env_bench.render.renderer import RenderConfig, SvgWorkbookRenderer
from table_env_bench.render.scene import build_page_scene

ZOOM_FACTORS = (1.0, 1.4, 2.0, 2.8)
PAN_RATIO = 0.22
VALID_MODES = {"agent", "human", "dev"}


@dataclass
class _State:
    sheet_index: int
    page_index: int
    zoom_index: int
    center_x: float
    center_y: float
    selected_region_id: str | None
    open_note_id: str | None
    action_count: int
    submitted_answer: str | None
    visited_sheet_keys: set[str] = field(default_factory=set)
    visited_page_keys: set[str] = field(default_factory=set)


class WorkbookEnv:
    def __init__(
        self,
        *,
        family: str | None = None,
        level: int | None = None,
        seed: int = 0,
        template_id: str | None = None,
        episode_spec: EpisodeSpec | None = None,
        mode: str = "agent",
        debug: bool = False,
        oracle_observation: bool = False,
        renderer: SvgWorkbookRenderer | None = None,
        answer_scorer: ExactMatchScorer | None = None,
    ) -> None:
        if episode_spec is None and (family is None or level is None):
            raise ValueError("Either episode_spec or family + level must be provided")
        resolved_mode = "dev" if debug else mode
        if resolved_mode not in VALID_MODES:
            raise ValueError(f"Unsupported mode: {resolved_mode}")

        self.family = family or episode_spec.family
        self.level = level or episode_spec.level
        self.seed = seed if episode_spec is None else episode_spec.seed
        self.template_id = template_id or (episode_spec.metadata.get("template_id") if episode_spec is not None else None)
        self.mode = resolved_mode
        self.oracle_observation = oracle_observation
        self._episode_factory = (
            None
            if episode_spec is not None
            else lambda selected_seed: generate_episode(self.family, self.level, selected_seed, template_id=self.template_id)
        )
        self.spec = episode_spec or generate_episode(self.family, self.level, self.seed, template_id=self.template_id)
        self.renderer = renderer or SvgWorkbookRenderer(RenderConfig())
        self.image_renderer = SceneImageRenderer()
        self.answer_scorer = answer_scorer or ExactMatchScorer()
        self._state: _State | None = None
        self._terminated = False
        self._truncated = False
        self._replay = ReplayTrace(
            episode_id=self.spec.episode_id,
            family=self.spec.family,
            level=self.spec.level,
            seed=self.spec.seed,
            workbook_id=self.spec.workbook.workbook_id,
            workbook_title=self.spec.workbook.title,
            initial_sheet_id=self.spec.sheets[0].sheet_id,
            initial_sheet_name=self.spec.sheets[0].tab_label,
            initial_page_id=self.spec.sheets[0].pages[0].page_id,
        )

    @property
    def replay(self) -> ReplayTrace:
        return self._replay

    @property
    def submitted_answer(self) -> str | None:
        return None if self._state is None else self._state.submitted_answer

    def reset(self, seed: int | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
        if seed is not None:
            self.seed = seed
        if self._episode_factory is not None:
            self.spec = self._episode_factory(self.seed)
        self._state = self._initial_state()
        self._terminated = False
        self._truncated = False
        self._replay = ReplayTrace(
            episode_id=self.spec.episode_id,
            family=self.spec.family,
            level=self.spec.level,
            seed=self.spec.seed,
            workbook_id=self.spec.workbook.workbook_id,
            workbook_title=self.spec.workbook.title,
            initial_sheet_id=self.spec.sheets[0].sheet_id,
            initial_sheet_name=self.spec.sheets[0].tab_label,
            initial_page_id=self.spec.sheets[0].pages[0].page_id,
        )
        self._record_visit()
        return self._observation(), self._info()

    def step(self, action: WorkbookAction | dict[str, Any]) -> tuple[dict[str, Any], float, bool, bool, dict[str, Any]]:
        if self._state is None:
            raise RuntimeError("reset() must be called before step()")
        if self._terminated or self._truncated:
            raise RuntimeError("Episode already finished")

        parsed = parse_action(action)
        before = self._snapshot_state()
        reward = 0.0
        metadata: dict[str, Any] = {}

        self._state.open_note_id = None
        if parsed.type == "select_sheet":
            self._select_sheet(parsed.sheet)
        elif parsed.type == "next_page":
            self._change_page(1)
        elif parsed.type == "prev_page":
            self._change_page(-1)
        elif parsed.type == "zoom_in":
            self._state.zoom_index = min(self._state.zoom_index + 1, len(ZOOM_FACTORS) - 1)
        elif parsed.type == "zoom_out":
            self._state.zoom_index = max(self._state.zoom_index - 1, 0)
        elif parsed.type.startswith("pan_"):
            self._apply_pan(parsed.type)
        elif parsed.type == "click_region":
            metadata = self._apply_click(parsed)
        elif parsed.type == "submit_answer":
            self._state.submitted_answer = parsed.text
            correctness = self.answer_scorer.score(parsed.text, self.spec.answer)
            reward = correctness.value
            metadata["correctness"] = correctness.details
            self._terminated = True

        self._state.action_count += 1
        self._clamp_state_to_viewbox()
        self._record_visit()

        if not self._terminated and self._state.action_count >= self.spec.max_actions:
            self._truncated = True

        after = self._snapshot_state()
        event = ReplayEvent(
            step_index=self._state.action_count,
            action=parsed.to_dict(),
            before=before,
            after=after,
            reward=reward,
            terminated=self._terminated,
            truncated=self._truncated,
            metadata=metadata,
        )
        self._replay.append(event)
        info = self._info(extra={"last_action": parsed.to_dict(), "last_event": event.to_dict()})
        return self._observation(), reward, self._terminated, self._truncated, info

    def export_replay(self, path: str) -> str:
        return str(self._replay.export_json(path, self.spec.metadata))

    @property
    def unique_sheets_visited(self) -> int:
        return len(self._state.visited_sheet_keys)

    @property
    def unique_pages_visited(self) -> int:
        return len(self._state.visited_page_keys)

    def _initial_state(self) -> _State:
        page = self.spec.sheets[0].pages[0]
        outer = make_outer_viewbox(page, self._aspect_ratio())
        state = _State(
            sheet_index=0,
            page_index=0,
            zoom_index=0,
            center_x=outer.center_x,
            center_y=outer.center_y,
            selected_region_id=None,
            open_note_id=None,
            action_count=0,
            submitted_answer=None,
        )
        self._state = state
        self._apply_initial_view_for_current_page()
        return state

    def _aspect_ratio(self) -> float:
        return self.renderer.config.viewport_width / self.renderer.config.viewport_height

    def _current_sheet(self) -> SheetSpec:
        return self.spec.sheets[self._state.sheet_index]

    def _current_page(self) -> PageSpec:
        return self._current_sheet().pages[self._state.page_index]

    def _current_outer_box(self) -> Rect:
        return make_outer_viewbox(self._current_page(), self._aspect_ratio())

    def _current_viewbox(self) -> Rect:
        outer_box = self._current_outer_box()
        zoom_factor = ZOOM_FACTORS[self._state.zoom_index]
        width = outer_box.width / zoom_factor
        height = outer_box.height / zoom_factor
        min_x = outer_box.x + (width / 2)
        max_x = outer_box.x + outer_box.width - (width / 2)
        min_y = outer_box.y + (height / 2)
        max_y = outer_box.y + outer_box.height - (height / 2)
        self._state.center_x = min(max(self._state.center_x, min_x), max_x)
        self._state.center_y = min(max(self._state.center_y, min_y), max_y)
        return Rect(
            x=self._state.center_x - (width / 2),
            y=self._state.center_y - (height / 2),
            width=width,
            height=height,
        )

    def _clamp_state_to_viewbox(self) -> None:
        _ = self._current_viewbox()

    def _apply_initial_view_for_current_page(self) -> None:
        page = self._current_page()
        initial_view = page.metadata.get("initial_view") if isinstance(page.metadata, dict) else None
        if not isinstance(initial_view, dict):
            return
        outer = self._current_outer_box()
        zoom_index = int(initial_view.get("zoom_index", 0))
        self._state.zoom_index = min(max(zoom_index, 0), len(ZOOM_FACTORS) - 1)
        self._state.center_x = float(initial_view.get("center_x", outer.center_x))
        self._state.center_y = float(initial_view.get("center_y", outer.center_y))
        self._clamp_state_to_viewbox()

    def _record_visit(self) -> None:
        sheet = self._current_sheet()
        page = self._current_page()
        self._state.visited_sheet_keys.add(sheet.sheet_id)
        self._state.visited_page_keys.add(f"{sheet.sheet_id}:{page.page_id}")

    def _select_sheet(self, sheet: str | int | None) -> None:
        if sheet is None:
            raise ValueError("select_sheet requires sheet value")
        new_index = self._resolve_sheet_index(sheet)
        if new_index == self._state.sheet_index:
            return
        self._state.sheet_index = new_index
        self._state.page_index = 0
        self._state.zoom_index = 0
        self._state.selected_region_id = None
        self._state.open_note_id = None
        outer = self._current_outer_box()
        self._state.center_x = outer.center_x
        self._state.center_y = outer.center_y
        self._apply_initial_view_for_current_page()

    def _resolve_sheet_index(self, sheet: str | int) -> int:
        if isinstance(sheet, int):
            if 0 <= sheet < len(self.spec.sheets):
                return sheet
            raise ValueError(f"Unknown sheet index: {sheet}")

        if isinstance(sheet, str) and sheet.isdigit():
            return self._resolve_sheet_index(int(sheet))

        for index, sheet_spec in enumerate(self.spec.sheets):
            if sheet_spec.tab_label == sheet or sheet_spec.sheet_id == sheet:
                return index
        raise ValueError(f"Unknown sheet: {sheet}")

    def _change_page(self, delta: int) -> None:
        pages = self._current_sheet().pages
        new_index = min(max(self._state.page_index + delta, 0), len(pages) - 1)
        if new_index == self._state.page_index:
            return
        self._state.page_index = new_index
        self._state.zoom_index = 0
        self._state.selected_region_id = None
        self._state.open_note_id = None
        outer = self._current_outer_box()
        self._state.center_x = outer.center_x
        self._state.center_y = outer.center_y
        self._apply_initial_view_for_current_page()

    def _apply_pan(self, action_type: str) -> None:
        viewbox = self._current_viewbox()
        if action_type == "pan_up":
            self._state.center_y -= viewbox.height * PAN_RATIO
        elif action_type == "pan_down":
            self._state.center_y += viewbox.height * PAN_RATIO
        elif action_type == "pan_left":
            self._state.center_x -= viewbox.width * PAN_RATIO
        elif action_type == "pan_right":
            self._state.center_x += viewbox.width * PAN_RATIO

    def _apply_click(self, action: WorkbookAction) -> dict[str, Any]:
        viewbox = self._current_viewbox()
        page = self._current_page()
        page_x = viewbox.x + ((action.x or 0.0) / self.renderer.config.viewport_width) * viewbox.width
        page_y = viewbox.y + ((action.y or 0.0) / self.renderer.config.viewport_height) * viewbox.height
        resolved = find_region_at_point(page, page_x, page_y)
        metadata: dict[str, Any] = {
            "page_coordinates": {"x": page_x, "y": page_y},
            "blank_click": resolved is None,
        }
        self._state.selected_region_id = None
        if resolved is None:
            return metadata

        region = resolved.region
        self._state.center_x = resolved.rect.center_x
        self._state.center_y = resolved.rect.center_y
        self._state.selected_region_id = region.public_id
        self._state.open_note_id = region.linked_note_id
        metadata["resolved_region"] = self._region_payload(region)
        if region.linked_note_id is not None:
            metadata["opened_note"] = region.linked_note_id
        return metadata

    def _find_note(self, note_id: str | None) -> NoteSpec | None:
        if note_id is None:
            return None
        for note in self._current_page().notes:
            if note.id == note_id:
                return note
        return None

    def _region_payload(self, region: RegionSpec) -> dict[str, Any]:
        return {
            "public_id": region.public_id,
            "role": region.role,
            "label": region.label,
            "sheet_id": self._current_sheet().sheet_id,
            "sheet": self._current_sheet().tab_label,
            "page": self._current_page().page_id,
        }

    def _observation(self) -> dict[str, Any]:
        note = self._find_note(self._state.open_note_id)
        viewbox = self._current_viewbox()
        scene = build_page_scene(
            self.spec.workbook,
            sheet_index=self._state.sheet_index,
            page_index=self._state.page_index,
            viewport=viewbox,
            config=self.renderer.config,
            overlay_note=note,
            selected_region_id=self._state.selected_region_id,
        )
        viewport_png = self.image_renderer.render_png_base64(scene)
        exposed_scene = self._agent_scene_payload(scene) if self.mode == "agent" else scene
        observation: dict[str, Any] = {
            "viewport_svg": self.renderer.render_page(
                self.spec.workbook,
                sheet_index=self._state.sheet_index,
                page_index=self._state.page_index,
                viewport=viewbox,
                overlay_note=note,
                debug=self.mode == "dev",
            ),
            "viewport_scene": exposed_scene,
            "viewport_image_png_base64": viewport_png,
            "viewport_width": self.renderer.config.viewport_width,
            "viewport_height": self.renderer.config.viewport_height,
            "question": self.spec.question,
            "remaining_action_budget": max(self.spec.max_actions - self._state.action_count, 0),
            "current_sheet_name": self._current_sheet().tab_label,
            "current_sheet_index": self._state.sheet_index,
            "current_page_index": self._state.page_index,
            "page_count_in_sheet": len(self._current_sheet().pages),
            "sheet_tabs": [sheet.tab_label for sheet in self.spec.sheets],
            "action_history_summary": [event.action["type"] for event in self._replay.events[-4:]],
        }
        if self.mode in {"human", "dev"}:
            observation["sample_surfaces"] = self._sample_surfaces_payload()
        if self.mode == "dev" and self.oracle_observation:
            observation["oracle"] = self.spec.to_dict()
        return observation

    def _sample_surfaces_payload(self) -> list[dict[str, Any]]:
        surfaces: list[dict[str, Any]] = []
        for sheet_index, sheet_spec in enumerate(self.spec.sheets):
            for page_index, page_spec in enumerate(sheet_spec.pages):
                scene = build_page_scene(
                    self.spec.workbook,
                    sheet_index=sheet_index,
                    page_index=page_index,
                    viewport=make_outer_viewbox(page_spec, self._aspect_ratio()),
                    config=self.renderer.config,
                )
                page_payload = scene.get("page") if isinstance(scene, dict) else None
                elements = page_payload.get("elements", []) if isinstance(page_payload, dict) else []
                surfaces.append(
                    {
                        "sheet_id": sheet_spec.sheet_id,
                        "sheet_name": sheet_spec.tab_label,
                        "page_id": page_spec.page_id,
                        "page_title": page_spec.title,
                        "elements": elements,
                    }
                )
        return surfaces

    def _agent_scene_payload(self, scene: dict[str, Any]) -> dict[str, Any]:
        payload = deepcopy(scene)
        page = payload.get("page")
        if isinstance(page, dict):
            page.pop("elements", None)
            page.pop("regions", None)
            page.pop("notes", None)
        return payload

    def _required_navigation_payload(self) -> dict[str, Any]:
        raw = self.spec.metadata.get("required_navigation")
        if not isinstance(raw, dict):
            raw = {}
        return {
            "required_sheet_ids": list(raw.get("required_sheet_ids", [])),
            "required_page_refs": list(raw.get("required_page_refs", [])),
            "required_notes": list(raw.get("required_notes", [])),
            "required_viewport_states": list(raw.get("required_viewport_states", [])),
            "forbidden_shortcuts": list(raw.get("forbidden_shortcuts", [])),
        }

    def _info(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        viewbox = self._current_viewbox()
        info = {
            "episode_id": self.spec.episode_id,
            "family": self.spec.family,
            "family_display_name": self.spec.family_display_name,
            "level": self.spec.level,
            "seed": self.spec.seed,
            "template_id": self.spec.metadata.get("template_id"),
            "instance_id": self.spec.metadata.get("instance_id"),
            "instance_label": self.spec.metadata.get("instance_label"),
            "pack_id": self.spec.metadata.get("pack_id"),
            "track": self.spec.metadata.get("track"),
            "locale": self.spec.locale,
            "mode": self.mode,
            "workbook_title": self.spec.workbook.title,
            "sheet_count": len(self.spec.sheets),
            "sheet_tabs": [sheet.tab_label for sheet in self.spec.sheets],
            "sheet_page_counts": [len(sheet.pages) for sheet in self.spec.sheets],
            "active_sheet": self._current_sheet().tab_label,
            "active_sheet_id": self._current_sheet().sheet_id,
            "active_sheet_index": self._state.sheet_index,
            "page_count_in_sheet": len(self._current_sheet().pages),
            "current_page_index": self._state.page_index,
            "current_page_id": self._current_page().page_id,
            "zoom_index": self._state.zoom_index,
            "viewbox": {"x": viewbox.x, "y": viewbox.y, "width": viewbox.width, "height": viewbox.height},
            "required_navigation": self._required_navigation_payload(),
            "max_actions": self.spec.max_actions,
            "action_count": self._state.action_count,
            "unique_sheets_visited": len(self._state.visited_sheet_keys),
            "unique_pages_visited": len(self._state.visited_page_keys),
            "terminated": self._terminated,
            "truncated": self._truncated,
        }
        if self.mode == "dev":
            info["debug"] = {
                "viewbox": viewbox.__dict__,
                "selected_region_id": self._state.selected_region_id,
                "open_note_id": self._state.open_note_id,
                "page": self._current_page().to_dict(),
            }
        if extra:
            info.update(extra)
        return info

    def _snapshot_state(self) -> dict[str, Any]:
        viewbox = self._current_viewbox()
        return {
            "sheet_index": self._state.sheet_index,
            "sheet_id": self._current_sheet().sheet_id,
            "sheet_name": self._current_sheet().tab_label,
            "page_index": self._state.page_index,
            "page_id": self._current_page().page_id,
            "zoom_index": self._state.zoom_index,
            "center_x": self._state.center_x,
            "center_y": self._state.center_y,
            "selected_region_id": self._state.selected_region_id,
            "open_note_id": self._state.open_note_id,
            "action_count": self._state.action_count,
            "submitted_answer": self._state.submitted_answer,
            "viewbox": {"x": viewbox.x, "y": viewbox.y, "width": viewbox.width, "height": viewbox.height},
        }


TableEnv = WorkbookEnv
