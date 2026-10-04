"""Exhibit design tokens, organised as style families.

A family is the full visual identity a deck renders in: palette, type, header treatment, sidebar
treatment and imagery. Families are inspired by the look of top firms' published decks, never
their trade dress (no logos, no proprietary fonts, no exact brand colours).

Module-level names (INK, ACCENT, ...) always hold the active family's values. Call use(name)
before rendering. Ramps were validated with the dataviz palette validator (ordinal mode).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class Type:
    title: float = 26
    exhibit_title: float = 13
    unit: float = 11.5
    label: float = 12
    value: float = 12.5
    value_hero: float = 16
    annotation: float = 11
    commentary_head: float = 13.5
    commentary: float = 13
    source: float = 9
    kpi: float = 34


@dataclass(frozen=True)
class Family:
    name: str
    inspired_by: str
    ink: str
    text2: str
    muted: str
    rule: str
    track: str
    panel: str
    neutral: str
    accent: str
    accent_dark: str
    accent_light: str
    accent2: str
    negative: str
    positive: str
    waves: tuple[str, str, str]
    heat: tuple[str, str, str, str, str]
    title_font: str
    font: str
    title_bold: bool
    header: str                     # "rule": title over a hairline. "band": title on an image band
    sidebar: str                    # fill of the big-number sidebar
    sidebar_text: str
    sidebar_number: str
    cover_style: str                # procedural or illustration style for covers
    band_style: str                 # image style for header bands and panels
    glow: tuple[str, str, str]      # palette for dark procedural imagery
    type: Type = field(default_factory=Type)


MERIDIAN = Family(
    name="meridian", inspired_by="McKinsey-style research and board decks",
    ink="#051C2C", text2="#3D4A5C", muted="#6B7280", rule="#C5CCD6", track="#E9ECF1", panel="#F2F5F9",
    neutral="#BCC4CF", accent="#2251FF", accent_dark="#1533B8", accent_light="#D6E0FF", accent2="#00A9F4",
    negative="#C0391B", positive="#2251FF",
    waves=("#1533B8", "#2251FF", "#7C9BFF"), heat=("#C7D4FF", "#9DB3FF", "#7090FF", "#3F66F5", "#1533B8"),
    title_font="Georgia", font="Arial", title_bold=True, header="rule",
    sidebar="#051C2C", sidebar_text="#FFFFFF", sidebar_number="#38BDF8",
    cover_style="factory", band_style="motion_streaks", glow=("#051C2C", "#1D3F8F", "#38BDF8"),
)

VERDANT = Family(
    name="verdant", inspired_by="BCG-style executive perspectives",
    ink="#0D2A22", text2="#33463F", muted="#5F6F69", rule="#C9D3CF", track="#E7EDEA", panel="#EEF5F1",
    neutral="#BFCBC6", accent="#11865A", accent_dark="#0A5C3D", accent_light="#D3EFE0", accent2="#2EB872",
    negative="#C0391B", positive="#11865A",
    waves=("#0A5C3D", "#11865A", "#5CC896"), heat=("#C6EBD8", "#93D6B4", "#5CBF8F", "#1E7D55", "#0A5C3D"),
    title_font="Arial", font="Arial", title_bold=True, header="band",
    sidebar="#EEF5F1", sidebar_text="#0D2A22", sidebar_number="#11865A",
    cover_style="factory", band_style="motion_streaks", glow=("#04140F", "#0B4A33", "#3DDC97"),
)

FAMILIES = {f.name: f for f in (MERIDIAN, VERDANT)}

ACTIVE: Family = MERIDIAN
TYPE: Type = MERIDIAN.type
INK = TEXT2 = MUTED = RULE = TRACK = PANEL = NEUTRAL = ACCENT = ACCENT_DARK = ACCENT_LIGHT = ACCENT2 = ""
NEGATIVE = POSITIVE = TITLE_FONT = FONT = ""
WAVES: tuple = ()
HEAT: tuple = ()


def use(name_or_family: str | Family) -> Family:
    """Activate a family: module-level tokens now resolve to its values."""
    global ACTIVE, TYPE, INK, TEXT2, MUTED, RULE, TRACK, PANEL, NEUTRAL, ACCENT, ACCENT_DARK, ACCENT_LIGHT
    global ACCENT2, NEGATIVE, POSITIVE, TITLE_FONT, FONT, WAVES, HEAT
    f = FAMILIES[name_or_family] if isinstance(name_or_family, str) else name_or_family
    ACTIVE, TYPE = f, f.type
    INK, TEXT2, MUTED, RULE, TRACK, PANEL, NEUTRAL = f.ink, f.text2, f.muted, f.rule, f.track, f.panel, f.neutral
    ACCENT, ACCENT_DARK, ACCENT_LIGHT, ACCENT2 = f.accent, f.accent_dark, f.accent_light, f.accent2
    NEGATIVE, POSITIVE = f.negative, f.positive
    TITLE_FONT, FONT = f.title_font, f.font
    WAVES, HEAT = f.waves, f.heat
    return f


use(MERIDIAN)


def with_type(f: Family, **sizes) -> Family:
    return replace(f, type=replace(f.type, **sizes))
