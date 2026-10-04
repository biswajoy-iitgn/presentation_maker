"""Exhibit design tokens for the consulting report family.

Ramps validated with the dataviz palette validator:
- WAVES (ordinal, 3 steps): all checks pass.
- HEAT (ordinal, 5 steps): passes monotone, step gap and single hue. The light end sits below 2:1 against
  white, so every heat cell carries a printed value and a white gap (secondary encoding).
"""

from __future__ import annotations

from dataclasses import dataclass

INK = "#051C2C"          # titles, values, totals
TEXT2 = "#4D5766"        # secondary text
MUTED = "#6B7280"        # axis labels, units, sources (4.8:1 on white)
RULE = "#C5CCD6"         # hairlines
TRACK = "#E9ECF1"        # range tracks, panel fills
PANEL = "#F3F5F8"        # commentary panels
NEUTRAL = "#BCC4CF"      # context marks (emphasis form: the rest is grey)
ACCENT = "#2251FF"       # the answer
ACCENT_DARK = "#1533B8"
NEGATIVE = "#C0391B"     # unfavourable deltas, below-benchmark markers (5.5:1)
POSITIVE = "#2251FF"     # favourable deltas
WAVES = ("#1533B8", "#2251FF", "#7C9BFF")
HEAT = ("#C7D4FF", "#9DB3FF", "#7090FF", "#3F66F5", "#1533B8")

TITLE_FONT = "Georgia"
FONT = "Arial"


@dataclass(frozen=True)
class Type:
    title: float = 24
    exhibit_title: float = 12
    unit: float = 10.5
    label: float = 10.5
    value: float = 11
    value_hero: float = 14
    annotation: float = 10
    commentary_head: float = 12
    commentary: float = 11.5
    source: float = 8.5


TYPE = Type()
