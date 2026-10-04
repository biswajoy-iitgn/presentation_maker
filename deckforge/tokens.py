"""Design tokens. A theme is the complete visual vocabulary the compiler is allowed to use."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    title_font: str
    body_font: str
    title_bold: bool
    title_size: int
    ink: str            # primary text
    muted: str          # secondary text, chart headers, sources
    rule: str           # hairlines and axis baselines
    neutral: str        # non-answer data
    accent: str         # the answer colour
    accent2: str        # secondary accent (sparingly)
    negative: str       # negative deltas
    paper: str          # slide background
    panel: str          # dark panels and sidebars
    panel_text: str
    panel_number: str   # big numbers on dark panels
    glow: tuple[str, str, str]   # procedural background palette: deep, mid, highlight


MERIDIAN = Theme(
    name="meridian",
    title_font="Georgia",
    body_font="Arial",
    title_bold=True,
    title_size=26,
    ink="#0B1B33",
    muted="#4B5563",
    rule="#0B1B33",
    neutral="#C5CCD6",
    accent="#2563EB",
    accent2="#0EA5A4",
    negative="#C2410C",
    paper="#FFFFFF",
    panel="#0B1B33",
    panel_text="#FFFFFF",
    panel_number="#38BDF8",
    glow=("#060D1F", "#1D3F8F", "#38BDF8"),
)
