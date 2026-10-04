"""Consulting slide frame: fixed zones so every slide in a deck shares one grid.

Zones (16:9, inches): tracker 0.22, title 0.42 to 1.30 (two lines max), rule 1.38,
exhibit header 1.52, content 1.95 to 6.72, footer 6.92.
"""

from __future__ import annotations

from dataclasses import dataclass

from pptx.enum.text import PP_ALIGN
from pptx.util import Inches

from deckforge.render import metrics
from deckforge.render.canvas import Canvas
from deckforge.viz import marks as M
from deckforge.viz import style as S

X0 = Inches(0.5)
X1 = Inches(12.83)
TITLE_Y = Inches(0.42)
RULE_Y = Inches(1.38)
HEADER_Y = Inches(1.52)
CONTENT_Y = Inches(1.95)
CONTENT_Y1 = Inches(6.72)
FOOTER_Y = Inches(6.92)


@dataclass(frozen=True)
class Box:
    x: int
    y: int
    w: int
    h: int

    @property
    def r(self) -> int:
        return self.x + self.w

    @property
    def b(self) -> int:
        return self.y + self.h

    def split_x(self, frac: float, gap=Inches(0.35)) -> tuple["Box", "Box"]:
        lw = int((self.w - gap) * frac)
        return Box(self.x, self.y, lw, self.h), Box(self.x + lw + gap, self.y, self.w - lw - gap, self.h)

    def split_y(self, frac: float, gap=Inches(0.2)) -> tuple["Box", "Box"]:
        th = int((self.h - gap) * frac)
        return Box(self.x, self.y, self.w, th), Box(self.x, self.y + th + gap, self.w, self.h - th - gap)

    def inset(self, dx=0, dy=0) -> "Box":
        return Box(self.x + dx, self.y + dy, self.w - 2 * dx, self.h - 2 * dy)

    def tuple(self):
        return self.x, self.y, self.w, self.h


def slide(c: Canvas, title: str, *, sections: list[str] | None = None, active: int | None = None,
          source: str = "", notes: list[str] = (), band=None) -> Box:
    """Draws tracker, action title, rule (or image band) and footer. Returns the content box.

    band: a PIL image. When given, or when the family header is 'band', the title sits in white on an
    image band across the top, the way BCG-style decks carry imagery on every content page.
    """
    use_band = band is not None
    if use_band:
        bh = RULE_Y + Inches(0.02)
        c.picture(band, 0, 0, c.deck.width, bh, name="DF_band")
        c.scrim(0, 0, c.deck.width, bh, S.ACTIVE.glow[0], 0.9, 0.62, angle_deg=0)
        c.rect(0, bh, c.deck.width, Inches(0.05), S.ACCENT, name="DF_band_rule")
    if sections:
        _tracker(c, sections, active, on_dark=use_band)
    size = S.TYPE.title
    while metrics.text_height(title, S.TITLE_FONT, size, True, X1 - X0) > RULE_Y - TITLE_Y - Inches(0.05) and size > 18:
        size -= 1
    M.label(c, X0, TITLE_Y, X1 - X0, RULE_Y - TITLE_Y, title, size=size, bold=True, font=S.TITLE_FONT,
            color="#FFFFFF" if use_band else S.INK, name="DF_title")
    if not use_band:
        M.hline(c, X0, X1, RULE_Y, S.INK, 0.75)
    foot = [*notes, source] if source else list(notes)
    if foot:
        fy = FOOTER_Y - Inches(0.16) * (len(foot) - 1)
        for i, line in enumerate(foot):
            M.label(c, X0, fy + Inches(0.16) * i, Inches(11), Inches(0.18), line, size=S.TYPE.source, color=S.MUTED,
                    name=f"DF_foot_{i}")
    M.label(c, X1 - Inches(0.5), FOOTER_Y, Inches(0.5), Inches(0.18), str(c.index), size=S.TYPE.source,
            color=S.MUTED, align=PP_ALIGN.RIGHT, name="DF_page")
    return Box(X0, CONTENT_Y, X1 - X0, CONTENT_Y1 - CONTENT_Y)


def _tracker(c: Canvas, sections: list[str], active: int | None, on_dark: bool = False):
    on, off, sep = ("#FFFFFF", "#C9D3E0", "#8796AD") if on_dark else (S.INK, S.MUTED, S.RULE)
    runs = []
    for i, s in enumerate(sections):
        if i:
            runs.append(("   |   ", False, sep))
        runs.append((s, i == active, on if i == active else off))
    M.label(c, X0, Inches(0.16), X1 - X0, Inches(0.2), [runs], size=9, align=PP_ALIGN.RIGHT, name="DF_tracker")


def exhibit_header(c: Canvas, box: Box, title: str, unit: str | None = None, *, sticker: str | None = None,
                   y=HEADER_Y) -> None:
    runs = [(title, True, S.INK)]
    if unit:
        runs.append((f"  {unit}", False, S.MUTED))
    w = box.w - (Inches(1.6) if sticker else 0)
    M.label(c, box.x, y, w, Inches(0.3), [runs], size=S.TYPE.exhibit_title, name="exhibit_header")
    if sticker:
        sw = Inches(1.35)
        c.sticker(sticker, box.r - sw, y - Inches(0.02), sw, Inches(0.27), S.NEGATIVE)


def commentary(c: Canvas, box: Box, heading: str, points: list[tuple[int | str | None, str, str]], *,
               fill=None) -> None:
    """Right-hand insight column. points: (marker number, icon name or None, bold lead, body)."""
    c.rect(box.x, box.y, box.w, box.h, fill or S.PANEL, name="commentary_panel")
    pad = Inches(0.24)
    M.label(c, box.x + pad, box.y + pad, box.w - 2 * pad, Inches(0.32), heading, size=S.TYPE.commentary_head,
            bold=True, name="commentary_head")
    M.hline(c, box.x + pad, box.r - pad, box.y + pad + Inches(0.4), S.ACCENT, 1.5)
    y = box.y + pad + Inches(0.58)
    text_x = box.x + pad + Inches(0.5)
    text_w = box.r - pad - text_x
    for i, (mark, lead, body) in enumerate(points):
        content = [[(lead + " ", True, S.INK), (body, False, S.TEXT2)]] if lead else body
        h = metrics.text_height(f"{lead} {body}", S.FONT, S.TYPE.commentary, True, text_w)
        if isinstance(mark, int):
            M.marker(c, box.x + pad + Inches(0.15), y + Inches(0.13), mark)
        elif isinstance(mark, str):
            M.icon_disc(c, mark, box.x + pad + Inches(0.17), y + Inches(0.15), Inches(0.36))
        M.label(c, text_x, y, text_w, h, content, size=S.TYPE.commentary, name=f"commentary_{i}")
        y += h + Inches(0.26)


def kpi_sidebar(c: Canvas, box: Box, items: list[tuple[str, str]], *, heading: str | None = None) -> None:
    """Big-number takeaway panel (McKinsey-style navy sidebar, or a tinted panel in lighter families)."""
    f = S.ACTIVE
    c.rect(box.x, box.y, box.w, box.h, f.sidebar, name="kpi_sidebar")
    pad = Inches(0.3)
    y = box.y + pad
    if heading:
        M.label(c, box.x + pad, y, box.w - 2 * pad, Inches(0.3), heading, size=S.TYPE.commentary_head, bold=True,
                color=f.sidebar_text, name="kpi_head")
        y += Inches(0.5)
    gap = (box.b - pad - y) / max(1, len(items))
    for i, (value, caption) in enumerate(items):
        if i:
            M.hline(c, box.x + pad, box.r - pad, y - Inches(0.14), f.sidebar_number, 0.75)
        M.kpi(c, box.x + pad, y, box.w - 2 * pad, value, caption, color=f.sidebar_number, caption_color=f.sidebar_text,
              size=30, name=f"side_kpi_{i}")
        y += gap
