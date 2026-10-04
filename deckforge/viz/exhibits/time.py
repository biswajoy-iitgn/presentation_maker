"""Time exhibits: paired panels sharing a time axis (instead of a dual-axis chart)."""

from __future__ import annotations

from typing import Callable

from pptx.util import Inches

from deckforge.render.canvas import Canvas
from deckforge.viz import marks as M
from deckforge.viz import style as S
from deckforge.viz.frame import Box
from deckforge.viz.scale import Linear


def columns_over_line(c: Canvas, box: Box, periods: list[str], columns: list[float], line: list[float], *,
                      col_title: str, line_title: str, fmt_col: Callable[[float], str],
                      fmt_line: Callable[[float], str], growth_label: str | None = None,
                      change_label: str | None = None, line_color=S.NEGATIVE, split=0.56) -> dict:
    """Magnitude on top (columns), rate below (line), one shared period axis.

    growth_label: text on an arrow from the first to the last column (e.g. CAGR).
    change_label: text on a bracket between first and last line points (e.g. -390 bps).
    """
    n = len(periods)
    title_w = Inches(2.1)
    plot_x, plot_w = box.x + title_w, box.w - title_w
    slot = plot_w / n
    top, bottom = box.split_y(split, gap=Inches(0.25))
    axis_h = Inches(0.32)
    bottom = Box(bottom.x, bottom.y, bottom.w, bottom.h - axis_h)

    # panel titles in the left gutter
    for panel, text in ((top, col_title), (bottom, line_title)):
        M.label(c, box.x, panel.y + Inches(0.05), title_w - Inches(0.2), Inches(0.6), text, size=S.TYPE.label,
                bold=True, color=S.INK, name=f"panel_title_{text[:12]}")

    # columns
    head = Inches(0.75 if growth_label else 0.35)
    yc = Linear(0, max(columns) * 1.02, top.b, top.y + head)
    bw = slot * 0.5
    col_tops = []
    for i, v in enumerate(columns):
        cx = plot_x + slot * (i + 0.5)
        color = S.ACCENT if i == n - 1 else S.NEUTRAL
        M.bar(c, cx - bw / 2, yc(v), bw, top.b - yc(v), color, name=f"col_{i}")
        M.centered_label(c, cx, yc(v) - Inches(0.27), fmt_col(v), size=S.TYPE.value, bold=i == n - 1,
                         color=S.INK, name=f"col_val_{i}")
        col_tops.append((cx, yc(v)))
    M.hline(c, plot_x, plot_x + plot_w, top.b, S.INK, 0.75)
    if growth_label:
        (x0, y0), (x1, y1) = col_tops[0], col_tops[-1]
        ya = min(y0, y1) - Inches(0.55)
        M.vline(c, x0, y0 - Inches(0.32), ya, S.INK, 1.0)
        c.line(int(x0), int(ya), int(x1), int(ya), S.INK, 1.0)
        M.arrow(c, x1, ya, x1, y1 - Inches(0.32), S.INK, 1.0)
        M.centered_label(c, (x0 + x1) / 2, ya - Inches(0.3), growth_label, w=Inches(2.4), size=S.TYPE.value,
                         bold=True, name="growth_label")

    # line
    lo, hi = min(line), max(line)
    pad = (hi - lo) * 0.35 or 1
    yl = Linear(lo - pad, hi + pad * 0.6, bottom.b, bottom.y + Inches(0.3))
    pts = [(plot_x + slot * (i + 0.5), yl(v)) for i, v in enumerate(line)]
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        c.line(int(xa), int(ya), int(xb), int(yb), line_color, 2.25)
    for i, ((x, y), v) in enumerate(zip(pts, line)):
        end = i in (0, n - 1)
        M.dot(c, x, y, Inches(0.13 if end else 0.1), line_color, ring="#FFFFFF")
        M.centered_label(c, x, y - Inches(0.32), fmt_line(v), size=S.TYPE.value, bold=end,
                         color=S.INK if end else S.TEXT2, name=f"line_val_{i}")
    M.hline(c, plot_x, plot_x + plot_w, bottom.b, S.RULE, 0.75)
    if change_label:
        x1, y1 = pts[-1]
        M.label(c, x1 + Inches(0.18), y1 - Inches(0.12), Inches(1.6), Inches(0.26), change_label,
                size=S.TYPE.value, bold=True, color=line_color, name="change_label")

    # shared period axis
    for i, p in enumerate(periods):
        M.centered_label(c, plot_x + slot * (i + 0.5), bottom.b + Inches(0.07), p, size=S.TYPE.label,
                         color=S.TEXT2, name=f"period_{i}")
    return {"columns": col_tops, "line": pts}
