"""Profit pool: variable-width bars, width = share of revenue, height = margin, area = profit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from pptx.enum.text import PP_ALIGN
from pptx.util import Inches

from deckforge.render import metrics
from deckforge.render.canvas import Canvas
from deckforge.viz import marks as M
from deckforge.viz import style as S
from deckforge.viz.frame import Box
from deckforge.viz.scale import Linear


@dataclass
class Segment:
    name: str
    size: float        # e.g. revenue
    rate: float        # e.g. EBITDA margin %


def profit_pool(c: Canvas, box: Box, segments: list[Segment], *, highlight: set[str],
                fmt_rate: Callable[[float], str], fmt_profit: Callable[[float], str],
                average: tuple[float, str] | None = None, x_title: str = "", y_title: str = "",
                icons: dict[str, str] | None = None) -> dict:
    total = sum(s.size for s in segments)
    label_h = Inches(1.15 if icons else 0.75)
    plot = Box(box.x + Inches(0.55), box.y + Inches(0.45), box.w - Inches(0.75), box.h - Inches(0.45) - label_h)
    x = Linear(0, total, plot.x, plot.r)
    hi = max(s.rate for s in segments) * 1.18
    y = Linear(0, hi, plot.b, plot.y)
    anchors = {}
    cum = 0.0
    for i, s in enumerate(segments):
        x0, x1 = x(cum) + M.GAP / 2, x(cum + s.size) - M.GAP / 2
        cum += s.size
        hot = s.name in highlight
        color = S.ACCENT if hot else S.NEUTRAL
        M.bar(c, x0, y(s.rate), x1 - x0, plot.b - y(s.rate), color, name=f"pool_{i}")
        cx = (x0 + x1) / 2
        M.centered_label(c, cx, y(s.rate) - Inches(0.28), fmt_rate(s.rate), w=int(x1 - x0), size=S.TYPE.value_hero,
                         bold=True, color=S.ACCENT if hot else S.INK, name=f"pool_rate_{i}")
        profit = s.size * s.rate / 100
        if plot.b - y(s.rate) > Inches(0.5):
            M.centered_label(c, cx, plot.b - Inches(0.34), fmt_profit(profit), w=int(x1 - x0), size=S.TYPE.label,
                             bold=True, color="#FFFFFF" if hot else S.INK, name=f"pool_profit_{i}")
        share = f"{s.size / total * 100:.0f}%"
        ty = plot.b + Inches(0.08)
        if icons and s.name in icons:
            M.icon_disc(c, icons[s.name], cx, ty + Inches(0.2), Inches(0.4), fill=S.ACCENT if hot else S.NEUTRAL)
            ty += Inches(0.46)
        lines = metrics.wrap(s.name, S.FONT, S.TYPE.label, True, int(x1 - x0 - Inches(0.05)))
        M.centered_label(c, cx, ty, [[(ln, True, S.INK)] for ln in lines] + [[(share, False, S.TEXT2)]],
                         w=int(x1 - x0), h=label_h, size=S.TYPE.label, name=f"pool_name_{i}")
        anchors[s.name] = (int(x1), int(y(s.rate)))
    M.hline(c, plot.x, plot.r, plot.b, S.INK, 0.75)
    if average:
        ay = y(average[0])
        M.hline(c, plot.x, plot.r, ay, S.INK, 1.0)
        M.label(c, plot.r - Inches(2.2), ay - Inches(0.25), Inches(2.2), Inches(0.24), average[1],
                size=S.TYPE.annotation, bold=True, align=PP_ALIGN.RIGHT, name="pool_average")
    if y_title:
        M.label(c, box.x, box.y, box.w - Inches(5.1), Inches(0.24), y_title, size=S.TYPE.unit, color=S.MUTED,
                name="pool_y")
    if x_title:
        M.label(c, box.r - Inches(5), box.y, Inches(5), Inches(0.24), x_title, size=S.TYPE.unit, color=S.MUTED,
                align=PP_ALIGN.RIGHT, name="pool_x")
    return anchors
