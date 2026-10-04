"""Annotation layer: think-cell style marks positioned from computed plot geometry."""

from __future__ import annotations

from pptx.enum.text import PP_ALIGN
from pptx.util import Inches

from deckforge.render.canvas import Canvas
from deckforge.render.charts import PlotBox


def pct_change(a: float, b: float) -> float:
    return (b - a) / a


def cagr(v0: float, v1: float, years: float) -> float:
    return (v1 / v0) ** (1 / years) - 1


def difference_arrow(c: Canvas, box: PlotBox, i: int, j: int, vi: float, vj: float, label: str,
                     color: str | None = None, clear_j: int = 0):
    """Bracket from the top of bar i to an arrowhead on bar j, label centred above.

    clear_j: extra clearance above bar j, e.g. when bar j carries its own value label.
    """
    color = color or c.theme.accent
    xi, xj = box.cat_center(i), box.cat_center(j)
    yi, yj = box.val(vi), box.val(vj) - clear_j
    top = min(yi, yj) - Inches(0.35)
    lift = Inches(0.06)
    c.line(xi, yi - lift, xi, top, color, 1.25)
    c.line(xi, top, xj, top, color, 1.25)
    c.line(xj, top, xj, yj - lift, color, 1.25, arrow_end=True)
    c.text((xi + xj) // 2 - Inches(0.6), top - Inches(0.32), Inches(1.2), Inches(0.28), label, size=13,
           bold=True, color=color, align=PP_ALIGN.CENTER, name="difference_label")


def data_row(c: Canvas, box: PlotBox, y: int, values: list[str], label: list[str] | str, size=12,
             x0=Inches(0.45)):
    """Row of values centred under each category, with a row label left of the plot."""
    c.text(x0, y, box.x - x0 - Inches(0.05), Inches(0.5), label if isinstance(label, list) else [label],
           size=size, color=c.theme.muted, name="data_row_label")
    cw = box.cat_width()
    for i, v in enumerate(values):
        c.text(box.cat_center(i) - cw // 2, y, cw, Inches(0.3), v, size=size, align=PP_ALIGN.CENTER,
               name=f"data_row_{i}")
