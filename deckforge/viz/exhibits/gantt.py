"""Wave roadmap: initiatives grouped by wave, month axis, value milestones on a top lane."""

from __future__ import annotations

from dataclasses import dataclass

from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches

from deckforge.render.canvas import Canvas
from deckforge.viz import marks as M
from deckforge.viz import style as S
from deckforge.viz.frame import Box
from deckforge.viz.scale import Linear


@dataclass
class Task:
    name: str
    wave: int          # 0-based
    start: float       # month
    end: float
    note: str = ""     # right-aligned value or owner


def roadmap(c: Canvas, box: Box, tasks: list[Task], waves: list[str], *, months: int = 24, tick: int = 3,
            milestones: list[tuple[float, str]] = ()) -> dict:
    label_w, note_w = Inches(3.1), Inches(1.0)
    lane_h = Inches(0.62) if milestones else 0
    axis_h = Inches(0.3)
    x = Linear(0, months, box.x + label_w, box.r - note_w - Inches(0.1))
    top = box.y + lane_h + axis_h
    n_rows = len(tasks) + len(waves)
    row_h = min(Inches(0.36), (box.b - top) / n_rows)

    # quarter grid and axis
    for m in range(0, months + 1, tick):
        M.vline(c, x(m), top, top + row_h * n_rows, S.TRACK, 0.75)
        M.centered_label(c, x(m), box.y + lane_h, f"M{m}", w=Inches(0.6), size=S.TYPE.annotation, color=S.MUTED,
                         name=f"month_{m}")
    for m, text in milestones:
        sp = c.rect(int(x(m) - Inches(0.08)), int(box.y + lane_h - Inches(0.22)), int(Inches(0.16)),
                    int(Inches(0.16)), S.INK, shape=MSO_SHAPE.DIAMOND, register=False, name=f"milestone_{m}")
        M.centered_label(c, x(m), box.y, text, w=Inches(1.7), h=Inches(0.36), size=S.TYPE.annotation, bold=True,
                         name=f"milestone_label_{m}")

    y = top
    for w_i, wave in enumerate(waves):
        M.bar(c, box.x, y + Inches(0.04), box.w, row_h - Inches(0.08), S.PANEL, name=f"wave_band_{w_i}")
        M.bar(c, box.x + Inches(0.1), y + row_h / 2 - Inches(0.06), Inches(0.12), Inches(0.12), S.WAVES[w_i],
              register=False)
        M.label(c, box.x + Inches(0.3), y, label_w, row_h, wave, size=S.TYPE.label, bold=True, color=S.INK,
                anchor=MSO_ANCHOR.MIDDLE, name=f"wave_{w_i}")
        y += row_h
        for t in (t for t in tasks if t.wave == w_i):
            M.label(c, box.x + Inches(0.25), y, label_w - Inches(0.3), row_h, t.name, size=S.TYPE.label,
                    color=S.INK, anchor=MSO_ANCHOR.MIDDLE, name=f"task_{t.name[:14]}")
            M.bar(c, x(t.start), y + row_h * 0.28, x(t.end) - x(t.start), row_h * 0.44, S.WAVES[w_i],
                  name=f"task_bar_{t.name[:14]}")
            if t.note:
                M.label(c, box.r - note_w, y, note_w, row_h, t.note, size=S.TYPE.label, bold=True,
                        align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE, name=f"task_note_{t.name[:14]}")
            y += row_h
    return {"bottom": y}
