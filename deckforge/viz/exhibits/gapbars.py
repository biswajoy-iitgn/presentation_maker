"""Gap-to-benchmark bars: one row per KPI, worse to the left, better to the right, worst first.

The familiar board form for 'how do we compare': every KPI is reduced to one comparable number
(% gap to the peer median, signed so that positive is better), with our value and the median shown
as columns so nothing is hidden.
"""

from __future__ import annotations

from typing import Callable

from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches

from deckforge.render.canvas import Canvas
from deckforge.viz import marks as M
from deckforge.viz import style as S
from deckforge.viz.frame import Box
from deckforge.viz.scale import Linear, fmt_num, nice_step


def gap_bars(c: Canvas, box: Box, rows: list[dict], *, ours_label: str, bench_label: str = "Peer median",
             fmt: dict[str, Callable[[float], str]], sort: bool = True) -> dict:
    """rows: name, unit, icon, ours, bench, higher_is_better, fmt (key into fmt)."""
    def gap(r):
        g = (r["ours"] - r["bench"]) / r["bench"] * 100
        return g if r["higher_is_better"] else -g
    data = sorted(rows, key=gap) if sort else rows
    icon_w, name_w, col_w = Inches(0.55), Inches(2.45), Inches(1.15)
    bars_x = box.x + icon_w + name_w + 2 * col_w + Inches(0.3)
    bars_w = box.r - bars_x
    head_h = Inches(0.62)
    row_h = (box.h - head_h) / len(data)
    lim = max(abs(gap(r)) for r in data)
    step = nice_step(lim, 2)
    lim = step * (int(lim / step) + 1)
    x = Linear(-lim, lim, bars_x + Inches(0.55), box.r - Inches(0.55))
    zero = x(0)

    hx = box.x + icon_w + name_w
    M.label(c, hx, box.y, col_w, head_h - Inches(0.1), ours_label, size=S.TYPE.label, bold=True,
            align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.BOTTOM, name="gap_head_ours")
    M.label(c, hx + col_w, box.y, col_w, head_h - Inches(0.1), bench_label, size=S.TYPE.label, bold=True,
            align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.BOTTOM, name="gap_head_bench")
    M.label(c, bars_x, box.y, bars_w, Inches(0.28), "Gap to peer median", size=S.TYPE.label, bold=True,
            align=PP_ALIGN.CENTER, name="gap_head_bars")
    M.label(c, bars_x, box.y + Inches(0.3), bars_w / 2 - Inches(0.1), Inches(0.24), "◂ worse", size=S.TYPE.annotation,
            color=S.NEGATIVE, align=PP_ALIGN.RIGHT, name="gap_worse")
    M.label(c, zero + Inches(0.1), box.y + Inches(0.3), bars_w / 2, Inches(0.24), "better ▸", size=S.TYPE.annotation,
            color=S.ACCENT, name="gap_better")
    M.hline(c, box.x, box.r, box.y + head_h, S.INK, 0.75)

    anchors = {}
    for i, r in enumerate(data):
        ry = box.y + head_h + row_h * i
        cy = ry + row_h / 2
        if i:
            M.hline(c, box.x, box.r, ry, S.RULE, 0.5)
        g = gap(r)
        worse = g < 0
        color = S.NEGATIVE if worse else S.ACCENT
        M.icon_disc(c, r["icon"], box.x + Inches(0.22), cy, Inches(0.4), fill=color if abs(g) >= lim * 0.45 else S.NEUTRAL)
        M.label(c, box.x + icon_w, cy - Inches(0.24), name_w, Inches(0.5),
                [[(r["name"], True, S.INK)], [(r["unit"], False, S.MUTED)]], size=S.TYPE.label,
                anchor=MSO_ANCHOR.MIDDLE, name=f"gap_name_{i}")
        f = fmt[r["fmt"]]
        M.label(c, hx, cy - Inches(0.15), col_w, Inches(0.3), f(r["ours"]), size=S.TYPE.value, bold=True,
                color=color, align=PP_ALIGN.CENTER, name=f"gap_ours_{i}")
        M.label(c, hx + col_w, cy - Inches(0.15), col_w, Inches(0.3), f(r["bench"]), size=S.TYPE.value,
                color=S.TEXT2, align=PP_ALIGN.CENTER, name=f"gap_bench_{i}")
        bh = min(Inches(0.34), row_h * 0.46)
        M.bar(c, min(zero, x(g)), cy - bh / 2, abs(x(g) - zero), bh, color, name=f"gap_bar_{i}")
        txt = fmt_num(g, 0, suffix="%", sign=True)
        tw = M.text_w(txt, S.TYPE.value, True) + Inches(0.1)
        lx = x(g) - tw - Inches(0.04) if worse else x(g) + Inches(0.06)
        M.label(c, lx, cy - Inches(0.15), tw, Inches(0.3), txt, size=S.TYPE.value, bold=True, color=color,
                align=PP_ALIGN.RIGHT if worse else PP_ALIGN.LEFT, name=f"gap_val_{i}")
        anchors[r["name"]] = (int(x(g) - tw - Inches(0.25)) if worse else int(x(g) + tw + Inches(0.25)), int(cy))
    M.vline(c, zero, box.y + head_h, box.b, S.INK, 1.0)
    return anchors
