"""Shared slide furniture: margins, title blocks, footers. Content flows from the returned edges."""

from __future__ import annotations

from pptx.enum.text import PP_ALIGN
from pptx.util import Inches

from deckforge.render import metrics
from deckforge.render.canvas import Canvas

MARGIN = Inches(0.45)
FOOTER_Y = Inches(6.98)


def content_right(c: Canvas) -> int:
    return c.deck.width - MARGIN


def title_block(c: Canvas, title: str, *, sub: str | None = None, rule: bool = False, y=Inches(0.45),
                width=None, color=None, x=MARGIN, size=None, rule_to=None) -> int:
    """Action title (wrapped with real metrics), optional topic line and rule. Returns bottom edge."""
    t = c.theme
    width = width or content_right(c) - x
    size = size or t.title_size
    th = metrics.text_height(title, t.title_font, size, t.title_bold, width)
    c.text(x, y, width, th, title, font=t.title_font, size=size, bold=t.title_bold,
           color=color or t.ink, name="DF_title")
    bottom = y + th
    if sub:
        c.text(x, bottom + Inches(0.06), width, Inches(0.3), sub, size=15, color=color or t.muted, name="DF_subtitle")
        bottom += Inches(0.42)
    if rule:
        bottom += Inches(0.08)
        c.line(x, bottom, rule_to or content_right(c), bottom, color or t.rule, 0.75)
    return bottom


def footer(c: Canvas, source: str, *, color=None, right=None):
    t = c.theme
    right = right or content_right(c)
    c.text(MARGIN, FOOTER_Y, right - MARGIN - Inches(0.6), Inches(0.25), source, size=9, color=color or t.muted,
           name="DF_source")
    c.text(right - Inches(0.5), FOOTER_Y, Inches(0.5), Inches(0.25), str(c.index), size=9,
           color=color or t.muted, align=PP_ALIGN.RIGHT, name="DF_page")
