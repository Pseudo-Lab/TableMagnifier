"""Adapter contract for canonical family modules."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from table_env_bench.data.families.shared import TemplateManifest
from table_env_bench.data.models import EpisodeSpec


BuildEpisode = Callable[..., EpisodeSpec]
ListManifests = Callable[[int], tuple[TemplateManifest, ...]]


@dataclass(frozen=True)
class FamilyAdapter:
    """Small public registration surface for a canonical episode family."""

    family: str
    label: str
    build_episode: BuildEpisode
    list_manifests: ListManifests
    levels: tuple[int, ...] = (1, 2, 3)

    def validate(self) -> None:
        if not self.family:
            raise ValueError("Family adapter requires a family id")
        if not self.label:
            raise ValueError(f"Family adapter {self.family!r} requires a label")
        if not self.levels:
            raise ValueError(f"Family adapter {self.family!r} requires at least one level")

        for level in self.levels:
            manifests = self.list_manifests(level)
            if not manifests:
                raise ValueError(f"Family adapter {self.family!r} has no manifests for level {level}")
            for manifest in manifests:
                if manifest.family != self.family:
                    raise ValueError(
                        f"Manifest {manifest.template_id!r} declares family {manifest.family!r}, "
                        f"expected {self.family!r}"
                    )
                if manifest.level != level:
                    raise ValueError(
                        f"Manifest {manifest.template_id!r} declares level {manifest.level}, expected {level}"
                    )
