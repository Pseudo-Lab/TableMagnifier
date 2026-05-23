"""Shared design tokens for the benchmark console and SVG renderer."""

from __future__ import annotations

from dataclasses import dataclass


def rgba(hex_color: str, alpha: float) -> str:
    color = hex_color.lstrip("#")
    if len(color) != 6:
        raise ValueError(f"Expected a 6-digit hex color, got: {hex_color}")
    red = int(color[0:2], 16)
    green = int(color[2:4], 16)
    blue = int(color[4:6], 16)
    return f"rgba({red}, {green}, {blue}, {alpha:.3f})"


@dataclass(frozen=True)
class ThemeTokens:
    font_sans: str = "'Noto Sans KR', Pretendard, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', sans-serif"
    font_mono: str = "'IBM Plex Mono', 'SFMono-Regular', Consolas, monospace"
    surface: str = "#f8fafc"
    surface_container_low: str = "#f1f5f9"
    surface_container: str = "#e2e8f0"
    surface_container_high: str = "#dbe4ee"
    surface_container_highest: str = "#cbd5e1"
    surface_container_lowest: str = "#ffffff"
    primary: str = "#0f172a"
    primary_container: str = "#334155"
    primary_fixed: str = "#e2e8f0"
    primary_fixed_dim: str = "#cbd5e1"
    tertiary: str = "#475569"
    tertiary_container: str = "#e2e8f0"
    tertiary_fixed: str = "#f1f5f9"
    note_container: str = "#f8fafc"
    note_container_strong: str = "#e2e8f0"
    on_surface: str = "#0f172a"
    on_surface_variant: str = "#475569"
    outline_variant: str = "#cbd5e1"
    success_container: str = "#e2e8f0"
    warning_container: str = "#eff6ff"
    danger_container: str = "#eef2ff"
    chart_grid: str = "#e2e8f0"
    plot_fill: str = "#f8fafc"


TOKENS = ThemeTokens()

SPACING = {
    "1": 4,
    "2": 8,
    "3": 12,
    "4": 16,
    "5": 24,
    "6": 32,
}

RADII = {
    "sm": 4,
    "md": 8,
    "lg": 12,
    "xl": 14,
}


def _css_vars() -> str:
    tokens = TOKENS
    return f"""
    :root {{
      --teb-font-sans: {tokens.font_sans};
      --teb-font-mono: {tokens.font_mono};
      --teb-surface: {tokens.surface};
      --teb-surface-low: {tokens.surface_container_low};
      --teb-surface-mid: {tokens.surface_container};
      --teb-surface-high: {tokens.surface_container_high};
      --teb-surface-highest: {tokens.surface_container_highest};
      --teb-surface-lowest: {tokens.surface_container_lowest};
      --teb-primary: {tokens.primary};
      --teb-primary-container: {tokens.primary_container};
      --teb-primary-fixed: {tokens.primary_fixed};
      --teb-primary-fixed-dim: {tokens.primary_fixed_dim};
      --teb-tertiary: {tokens.tertiary};
      --teb-tertiary-container: {tokens.tertiary_container};
      --teb-note-container: {tokens.note_container};
      --teb-note-strong: {tokens.note_container_strong};
      --teb-on-surface: {tokens.on_surface};
      --teb-on-surface-variant: {tokens.on_surface_variant};
      --teb-outline: {tokens.outline_variant};
      --teb-ghost-border: {rgba(tokens.outline_variant, 0.18)};
      --teb-ghost-border-strong: {rgba(tokens.outline_variant, 0.28)};
      --teb-ambient-shadow: 0 12px 32px {rgba(tokens.on_surface, 0.06)};
      --teb-radius-sm: {RADII["sm"]}px;
      --teb-radius-md: {RADII["md"]}px;
      --teb-radius-lg: {RADII["lg"]}px;
      --teb-radius-xl: {RADII["xl"]}px;
    }}
    """


def preview_gallery_css() -> str:
    return (
        _css_vars()
        + """
    body {
      margin: 0;
      padding: 32px;
      font-family: var(--teb-font-sans);
      background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
      color: var(--teb-on-surface);
    }

    header {
      max-width: 1320px;
      margin: 0 auto;
    }

    h1 {
      margin: 0 0 8px;
      font-size: 1.55rem;
      line-height: 1.1;
    }

    p {
      margin: 0;
      color: var(--teb-on-surface-variant);
    }

    .gallery-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
      gap: 18px;
      margin-top: 22px;
      max-width: 1320px;
      margin-left: auto;
      margin-right: auto;
    }

    .preview-card {
      background: rgba(255, 255, 255, 0.88);
      border-radius: var(--teb-radius-lg);
      padding: 12px;
      box-shadow: var(--teb-ambient-shadow);
      border: 1px solid var(--teb-ghost-border);
    }

    .preview-card img {
      display: block;
      width: 100%;
      border-radius: var(--teb-radius-md);
      background: #ffffff;
      border: 1px solid var(--teb-ghost-border);
    }

    .preview-meta {
      margin-bottom: 10px;
    }

    .preview-meta strong {
      display: block;
      margin-top: 4px;
      font-size: 1rem;
    }
    """
    )
