"""Heat-map table: values coloured on a validated sequential ramp, totals set apart."""

from __future__ import annotations

from typing import Callable

from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches

from deckforge.assets.treatment import contrast_ratio, luminance
from deckforge.render.canvas import Canvas
from deckforge.viz import marks as M
from deckforge.viz import style as S
from deckforge.viz.frame import Box


def heat_table(c: Canvas, box: Box, rows: list[str], cols: list[str], values: list[list[float]], *,
               fmt: Callable[[float], str], row_head: str = "", total_label: str = "Total",
               row_notes: list[str] | None = None, outline: set[tuple[int, int]] = frozenset(),
               row_icons: list[str] | None = None) -> dict:
    """outline: cells to frame in ink (the ones the title talks about)."""
    label_w = Inches(2.9)
    total_w = Inches(1.1)
    head_h = Inches(0.5)
    n_r, n_c = len(rows), len(cols)
    row_h = (box.h - head_h - Inches(0.5)) / n_r
    cell_w = (box.w - label_w - total_w - Inches(0.15)) / n_c
    flat = sorted(v for r in values for v in r)
    cuts = [flat[int(len(flat) * q)] for q in (0.2, 0.4, 0.6, 0.8)]

    def bin_color(v):
        return S.HEAT[sum(v >= t for t in cuts)]

    M.label(c, box.x, box.y + Inches(0.12), label_w, Inches(0.3), row_head, size=S.TYPE.label, bold=True,
            name="heat_row_head")
    for j, col in enumerate(cols):
        M.label(c, box.x + label_w + cell_w * j, box.y, cell_w, head_h, col, size=S.TYPE.label, bold=True,
                align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.BOTTOM, name=f"heat_col_{j}")
    tx = box.x + label_w + cell_w * n_c + Inches(0.15)
    M.label(c, tx, box.y, total_w, head_h, total_label, size=S.TYPE.label, bold=True, align=PP_ALIGN.CENTER,
            anchor=MSO_ANCHOR.BOTTOM, name="heat_total_head")
    M.hline(c, box.x, box.r, box.y + head_h + Inches(0.05), S.INK, 0.75)

    y0 = box.y + head_h + Inches(0.1)
    for i, (r, vals) in enumerate(zip(rows, values)):
        ry = y0 + row_h * i
        lines = [[(r, True, S.INK)]] + ([[(row_notes[i], False, S.MUTED)]] if row_notes else [])
        lx = box.x
        if row_icons:
            M.icon_disc(c, row_icons[i], box.x + Inches(0.2), ry + row_h / 2, Inches(0.38))
            lx += Inches(0.5)
        M.label(c, lx, ry, label_w - Inches(0.1) - (lx - box.x), row_h, lines, size=S.TYPE.label,
                anchor=MSO_ANCHOR.MIDDLE, name=f"heat_row_{i}")
        for j, v in enumerate(vals):
            cx = box.x + label_w + cell_w * j
            fill = bin_color(v)
            M.bar(c, cx + M.GAP, ry + M.GAP, cell_w - 2 * M.GAP, row_h - 2 * M.GAP, fill, name=f"heat_{i}_{j}")
            if (i, j) in outline:
                c.rect(int(cx + M.GAP), int(ry + M.GAP), int(cell_w - 2 * M.GAP), int(row_h - 2 * M.GAP), None,
                       line=(S.INK, 2.0), register=False)
            lf = luminance(fill)                      # whichever ink reads better on this step
            ink = "#FFFFFF" if contrast_ratio(1.0, lf) >= contrast_ratio(luminance(S.INK), lf) else S.INK
            M.label(c, cx, ry, cell_w, row_h, fmt(v), size=S.TYPE.value, bold=(i, j) in outline, color=ink,
                    align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, name=f"heat_val_{i}_{j}")
        M.label(c, tx, ry, total_w, row_h, fmt(sum(vals)), size=S.TYPE.value, bold=True, align=PP_ALIGN.CENTER,
                anchor=MSO_ANCHOR.MIDDLE, name=f"heat_rtot_{i}")
    ty = y0 + row_h * n_r + Inches(0.05)
    M.hline(c, box.x, box.r, ty, S.INK, 0.75)
    M.label(c, box.x, ty + Inches(0.08), label_w, Inches(0.3), total_label, size=S.TYPE.label, bold=True,
            name="heat_total_row")
    col_tot = [sum(r[j] for r in values) for j in range(n_c)]
    for j, v in enumerate(col_tot):
        M.label(c, box.x + label_w + cell_w * j, ty + Inches(0.08), cell_w, Inches(0.3), fmt(v), size=S.TYPE.value,
                bold=True, align=PP_ALIGN.CENTER, name=f"heat_ctot_{j}")
    M.label(c, tx, ty + Inches(0.08), total_w, Inches(0.3), fmt(sum(col_tot)), size=S.TYPE.value, bold=True,
            align=PP_ALIGN.CENTER, color=S.ACCENT, name="heat_grand")
    return {"col_totals": col_tot}
