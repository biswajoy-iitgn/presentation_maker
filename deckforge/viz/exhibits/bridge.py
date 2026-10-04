"""Waterfall bridge with subtotals, axis break, grouping brackets and benchmark line."""

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


@dataclass(frozen=True)
class BarAnchor:
    cx: int
    left: int
    right: int
    top: int
    bottom: int

    def marker_point(self) -> tuple[int, int]:
        """Top-right corner, just outside the bar: where a numbered callout sits."""
        return self.right + Inches(0.17), self.top + Inches(0.02)


def _label_color(s, bar_color):
    if s.kind == "total":
        return S.INK
    return S.TEXT2 if bar_color == S.NEUTRAL else bar_color


@dataclass
class Step:
    label: str
    value: float | None          # delta for 'delta'; level for 'total' (None = close the bridge at running level)
    kind: str = "delta"          # delta | total


def levels(steps: list[Step]) -> list[tuple[float, float]]:
    """(bottom, top) of each bar in data units."""
    run, out = 0.0, []
    for s in steps:
        if s.kind == "total":
            run = run if s.value is None else s.value
            out.append((0.0, run))
        else:
            out.append((run, run + s.value))
            run += s.value
    return out


def waterfall(c: Canvas, box: Box, steps: list[Step], *, fmt_total: Callable[[float], str],
              fmt_delta: Callable[[float], str], higher_is_better: bool = True, floor: float | None = None,
              brackets: list[tuple[int, int, str]] = (), benchmark: tuple[float, str] | None = None,
              bar_frac: float = 0.62, emphasis: set[int] | None = None) -> dict[int, "BarAnchor"]:
    """Returns {index: BarAnchor} for callouts.

    floor: start the value axis here and mark totals with an axis break (keeps small deltas readable).
    emphasis: delta indices the title talks about. Others are drawn in neutral grey (emphasis form).
    """
    lv = levels(steps)
    n = len(steps)
    hi = max(max(t, b) for b, t in lv)
    if benchmark:
        hi = max(hi, benchmark[0])
    lo = floor if floor is not None else min(0.0, min(min(b, t) for b, t in lv))
    cat_size = _fit_category_size([s.label for s in steps], int(box.w / n - Inches(0.08)))
    n_lines = max(len(metrics.wrap(s.label, S.FONT, cat_size, s.kind == "total", int(box.w / n - Inches(0.08))))
                  for s in steps)
    label_h = Inches(0.12) + int(n_lines * cat_size * 1.2 * 12700)
    top_pad = Inches(0.45) + Inches(0.38) * (max((lvl for *_, lvl in _bracket_levels(brackets)), default=-1) + 1)
    plot = Box(box.x, box.y + top_pad, box.w, box.h - top_pad - label_h)
    y = Linear(lo, hi, plot.b, plot.y)
    slot = plot.w / n
    bw = slot * bar_frac
    good, bad = (S.POSITIVE, S.NEGATIVE) if higher_is_better else (S.NEGATIVE, S.POSITIVE)
    if benchmark:                                   # behind the bars and labels
        by = y(benchmark[0])
        M.hline(c, plot.x, plot.r, by, S.TEXT2, 0.75)
        M.label(c, plot.r - Inches(2.6), by - Inches(0.26), Inches(2.6), Inches(0.24), benchmark[1],
                size=S.TYPE.annotation, color=S.TEXT2, align=PP_ALIGN.RIGHT, name="wf_benchmark")
    knock = benchmark is not None
    anchors = {}
    for i, (s, (b, t)) in enumerate(zip(steps, lv)):
        cx = int(plot.x + slot * (i + 0.5))
        x = cx - bw / 2
        if s.kind == "total":
            color = S.INK
            y_top, y_bot = y(t), plot.b
        else:
            color = good if s.value >= 0 else bad
            if emphasis is not None and i not in emphasis:
                color = S.NEUTRAL
            y_top, y_bot = y(max(b, t)), y(min(b, t))
        M.bar(c, x, y_top, bw, max(Inches(0.02), y_bot - y_top), color, name=f"wf_bar_{i}")
        if s.kind == "total" and floor is not None:
            _axis_break(c, x, bw, plot.b - Inches(0.22))
        # value label: above for totals and increases, below for decreases
        if s.kind == "total" or s.value >= 0:
            M.centered_label(c, cx, y_top - Inches(0.27), fmt_total(t) if s.kind == "total" else fmt_delta(s.value),
                             w=int(slot), size=S.TYPE.value, bold=True, color=_label_color(s, color),
                             knockout=knock, name=f"wf_val_{i}")
        else:
            M.centered_label(c, cx, y_bot + Inches(0.04), fmt_delta(s.value), w=int(slot), size=S.TYPE.value,
                             bold=True, color=_label_color(s, color), knockout=knock, name=f"wf_val_{i}")
        # category label, wrapped to the slot
        lines = metrics.wrap(s.label, S.FONT, cat_size, s.kind == "total", int(slot - Inches(0.08)))
        M.centered_label(c, cx, plot.b + Inches(0.08), lines, w=int(slot - Inches(0.04)),
                         h=label_h, size=cat_size, color=S.TEXT2, bold=s.kind == "total", name=f"wf_cat_{i}")
        if i < n - 1:
            level = t if s.kind == "total" else b + s.value
            nx = int(plot.x + slot * (i + 1.5)) - bw / 2
            M.hline(c, x + bw, nx, y(level), S.MUTED, 0.5)
        anchors[i] = BarAnchor(cx, int(x), int(x + bw), y_top, y_bot)
    M.hline(c, plot.x, plot.r, plot.b, S.INK, 0.75)
    for i0, i1, text, lvl in _bracket_levels(brackets):
        x1 = plot.x + slot * i0 + (slot - bw) / 2
        x2 = plot.x + slot * (i1 + 1) - (slot - bw) / 2
        top = min(anchors[k].top for k in range(i0, i1 + 1))
        M.bracket_h(c, x1, x2, top - Inches(0.42) - Inches(0.38) * lvl, text)
    return anchors


def _fit_category_size(labels: list[str], width: int, max_size=S.TYPE.label, min_size=8.0) -> float:
    """Largest size at which no word breaks mid-word and no label needs more than three lines."""
    size = max_size
    while size > min_size:
        words_fit = all(metrics.text_width_pt(w, S.FONT, size, True) * 12700 <= width
                        for lbl in labels for w in lbl.split())
        lines_ok = all(len(metrics.wrap(lbl, S.FONT, size, True, width)) <= 3 for lbl in labels)
        if words_fit and lines_ok:
            return size
        size -= 0.5
    return min_size


def _bracket_levels(brackets):
    out = []
    for k, (i0, i1, text) in enumerate(brackets):
        lvl = sum(1 for j0, j1, _ in brackets[:k] if not (i1 < j0 or j1 < i0))
        out.append((i0, i1, text, lvl))
    return out


def _axis_break(c: Canvas, x, w, y):
    """Two white parallel slashes across a total bar: the axis does not start at zero."""
    for dy in (0, Inches(0.07)):
        c.line(int(x - Inches(0.04)), int(y + dy + Inches(0.05)), int(x + w + Inches(0.04)), int(y + dy - Inches(0.05)),
               "#FFFFFF", 2.25)
