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
          source: str = "", notes: list[str] = ()) -> Box:
    """Draws tracker, action title, rule and footer. Returns the content box."""
    if sections:
        _tracker(c, sections, active)
    size = S.TYPE.title
    while metrics.text_height(title, S.TITLE_FONT, size, True, X1 - X0) > RULE_Y - TITLE_Y - Inches(0.05) and size > 18:
        size -= 1
    M.label(c, X0, TITLE_Y, X1 - X0, RULE_Y - TITLE_Y, title, size=size, bold=True, font=S.TITLE_FONT,
            name="DF_title")
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


def _tracker(c: Canvas, sections: list[str], active: int | None):
    runs = []
    for i, s in enumerate(sections):
        if i:
            runs.append(("   |   ", False, S.RULE))
        runs.append((s, i == active, S.INK if i == active else S.MUTED))
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


def commentary(c: Canvas, box: Box, heading: str, points: list[tuple[int | None, str, str]], *,
               fill=S.PANEL) -> None:
    """Right-hand insight column. points: (marker number or None, bold lead, body)."""
    c.rect(box.x, box.y, box.w, box.h, fill, name="commentary_panel")
    pad = Inches(0.22)
    M.label(c, box.x + pad, box.y + pad, box.w - 2 * pad, Inches(0.3), heading, size=S.TYPE.commentary_head,
            bold=True, name="commentary_head")
    M.hline(c, box.x + pad, box.r - pad, box.y + pad + Inches(0.36), S.INK, 0.75)
    y = box.y + pad + Inches(0.52)
    text_x = box.x + pad + Inches(0.42)
    text_w = box.r - pad - text_x
    for i, (n, lead, body) in enumerate(points):
        content = [[(lead + " ", True, S.INK), (body, False, S.TEXT2)]] if lead else body
        h = metrics.text_height(f"{lead} {body}", S.FONT, S.TYPE.commentary, True, text_w)
        if n is not None:
            M.marker(c, box.x + pad + Inches(0.13), y + Inches(0.12), n)
        M.label(c, text_x, y, text_w, h, content, size=S.TYPE.commentary, name=f"commentary_{i}")
        y += h + Inches(0.24)
