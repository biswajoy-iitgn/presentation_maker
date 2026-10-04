"""Bubble matrix for portfolio and prioritisation views, with reference lines and quadrant labels.

Labels are placed greedily: each bubble tries its preferred side, then the others, and takes the first
position that collides with no bubble, label or annotation already placed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from pptx.enum.text import PP_ALIGN
from pptx.util import Inches

from deckforge.assets.treatment import luminance
from deckforge.render import metrics
from deckforge.render.canvas import Canvas
from deckforge.viz import marks as M
from deckforge.viz import style as S
from deckforge.viz.frame import Box
from deckforge.viz.scale import Linear, nice_step

Rect = tuple[int, int, int, int]


@dataclass
class Point:
    label: str
    x: float
    y: float
    size: float
    highlight: bool = False
    note: str = ""            # second label line, e.g. the size value
    icon: str = ""            # icon drawn inside the bubble when it is large enough


def _hit(a: Rect, b: Rect) -> bool:
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def _ticks(lo: float, hi: float) -> list[float]:
    step = nice_step(hi - lo, 5)
    v = math.ceil(lo / step - 1e-9) * step
    out = []
    while v <= hi + 1e-9:
        out.append(round(v, 10))
        v += step
    return out


def _text_w(s: str, bold: bool) -> int:
    return int(metrics.text_width_pt(s, S.FONT, S.TYPE.label, bold) * 12700) + Inches(0.08)


def bubble_matrix(c: Canvas, box: Box, points: list[Point], *, x_title: str, y_title: str,
                  fmt_x: Callable[[float], str], fmt_y: Callable[[float], str],
                  x_ref: tuple[float, str] | None = None, y_ref: tuple[float, str] | None = None,
                  quadrants: dict[str, str] | None = None, shade: str | None = None, invert_y: bool = False,
                  domain_x: tuple[float, float] | None = None, domain_y: tuple[float, float] | None = None,
                  max_d=Inches(1.05), size_note: str = "", label_side: dict[str, str] | None = None) -> dict:
    """quadrants: {'tl','tr','bl','br': label}. shade: quadrant key tinted as the priority zone.
    invert_y: low values at the top (when lower is better).
    Returns {label: (cx, cy, d, (marker_x, marker_y))}: centre, diameter and a clear spot for a callout."""
    plot = Box(box.x + Inches(0.75), box.y + Inches(0.3), box.w - Inches(0.95), box.h - Inches(0.95))
    xs, ys = [p.x for p in points], [p.y for p in points]
    x0, x1 = domain_x or (min(xs), max(xs))
    y0, y1 = domain_y or (min(ys), max(ys))
    x = Linear(x0, x1, plot.x, plot.r)
    y = Linear(y0, y1, plot.y, plot.b) if invert_y else Linear(y0, y1, plot.b, plot.y)
    occupied: list[Rect] = []

    if shade and x_ref and y_ref:
        xr, yr = x(x_ref[0]), y(y_ref[0])
        qx = {"l": (plot.x, xr), "r": (xr, plot.r)}[shade[1]]
        qy = {"t": (plot.y, yr), "b": (yr, plot.b)}[shade[0]]
        M.bar(c, qx[0], qy[0], qx[1] - qx[0], qy[1] - qy[0], S.PANEL, name="priority_zone")

    # axes, ticks, titles
    M.hline(c, plot.x, plot.r, plot.b, S.INK, 0.75)
    M.vline(c, plot.x, plot.y, plot.b, S.INK, 0.75)
    for v in _ticks(x0, x1):
        M.centered_label(c, x(v), plot.b + Inches(0.06), fmt_x(v), w=Inches(0.8), size=S.TYPE.annotation,
                         color=S.MUTED, name=f"xt_{v:g}")
    for v in _ticks(y0, y1)[1:] if _ticks(x0, x1)[0] == x0 else _ticks(y0, y1):     # origin labelled once
        M.label(c, plot.x - Inches(0.75), y(v) - Inches(0.1), Inches(0.68), Inches(0.2), fmt_y(v),
                size=S.TYPE.annotation, color=S.MUTED, align=PP_ALIGN.RIGHT, name=f"yt_{v:g}")
    M.label(c, plot.x, plot.b + Inches(0.32), plot.w, Inches(0.24), x_title, size=S.TYPE.unit, color=S.TEXT2,
            align=PP_ALIGN.CENTER, name="x_title")
    M.label(c, box.x, box.y, box.w - (Inches(3.5) if size_note else 0), Inches(0.24), y_title, size=S.TYPE.unit,
            color=S.TEXT2, name="y_title")
    if size_note:
        M.label(c, box.r - Inches(3.4), box.y, Inches(3.4), Inches(0.24), size_note, size=S.TYPE.annotation,
                color=S.MUTED, align=PP_ALIGN.RIGHT, name="size_note")

    # reference lines, labels placed at the plot edge and reserved
    if y_ref:
        ry = y(y_ref[0])
        M.hline(c, plot.x, plot.r, ry, S.MUTED, 0.75)
        if y_ref[1]:
            r = (plot.r - Inches(2.2), ry - Inches(0.24), Inches(2.2), Inches(0.22))
            M.label(c, *r, y_ref[1], size=S.TYPE.annotation, color=S.TEXT2, align=PP_ALIGN.RIGHT, name="y_ref")
            occupied.append(r)
    if x_ref:
        rx = x(x_ref[0])
        M.vline(c, rx, plot.y, plot.b, S.MUTED, 0.75)
        if x_ref[1]:
            r = (rx + Inches(0.06), plot.b - Inches(0.26), Inches(1.8), Inches(0.22))
            M.label(c, *r, x_ref[1], size=S.TYPE.annotation, color=S.TEXT2, name="x_ref")
            occupied.append(r)

    smax = max(p.size for p in points)
    uniform = len({p.size for p in points}) == 1         # no size encoding: equal icon discs
    geo = []
    for p in points:
        d = Inches(0.52) if uniform else max(Inches(0.22), int(max_d * math.sqrt(p.size / smax)))
        geo.append((p, x(p.x), y(p.y), d))
        occupied.append((int(x(p.x) - d / 2), int(y(p.y) - d / 2), d, d))
    for p, cx, cy, d in sorted(geo, key=lambda g: -g[3]):            # big first, small drawn on top
        fill = S.ACCENT if p.highlight else S.NEUTRAL
        M.dot(c, cx, cy, d, fill, ring="#FFFFFF", name=f"bubble_{p.label}")
        if p.icon and d >= Inches(0.42):
            s_ = d * 0.48
            M.icon(c, p.icon, cx - s_ / 2, cy - s_ / 2, s_, color=S.INK if luminance(fill) > 0.45 else "#FFFFFF")

    if quadrants:
        # each label takes the first corner of its quadrant that no bubble or label covers
        xr = x(x_ref[0]) if x_ref else (plot.x + plot.r) // 2
        yr = y(y_ref[0]) if y_ref else (plot.y + plot.b) // 2
        pad, qh = Inches(0.1), Inches(0.22)
        for key, text in quadrants.items():
            w = _text_w(text, True)
            qx0, qx1 = (plot.x, xr) if key[1] == "l" else (xr, plot.r)
            qy0, qy1 = (plot.y, yr) if key[0] == "t" else (yr, plot.b)
            corners = [(qx0 + pad, qy0 + pad), (qx1 - pad - w, qy0 + pad), (qx0 + pad, qy1 - pad - qh),
                       (qx1 - pad - w, qy1 - pad - qh)]
            if key[0] == "b":
                corners = corners[2:] + corners[:2]
            if key[1] == "r":
                corners = [corners[1], corners[0], corners[3], corners[2]]
            r = min(((int(cx_), int(cy_), w, qh) for cx_, cy_ in corners),
                    key=lambda rr: sum(_hit(rr, o) for o in occupied))
            M.label(c, *r, text, size=S.TYPE.annotation, bold=True, color=S.ACCENT_DARK if key == shade else S.MUTED,
                    align=PP_ALIGN.LEFT, name=f"quad_{key}")
            occupied.append(r)

    # a label must not straddle a reference line: the line would read as a strike-through
    lines_ = []
    if x_ref:
        lines_.append((int(x(x_ref[0])) - Inches(0.02), plot.y, Inches(0.04), plot.h))
    if y_ref:
        lines_.append((plot.x, int(y(y_ref[0])) - Inches(0.02), plot.w, Inches(0.04)))
    anchors = {}
    order = ["r", "l", "t", "b", "tr", "br", "tl", "bl"]

    def crowding(g):            # the most boxed-in bubble picks its label spot first
        return sum(math.hypot(g[1] - o[1], g[2] - o[2]) < Inches(1.3) for o in geo if o is not g)
    for p, cx, cy, d in sorted(geo, key=lambda g: (-crowding(g), -g[3])):
        lw = max(_text_w(p.label, True), _text_w(p.note, False) if p.note else 0)
        lh = Inches(0.42 if p.note else 0.24)
        own = (int(cx - d / 2), int(cy - d / 2), d, d)
        prefs = [(label_side or {}).get(p.label, "r")] + order
        best, best_cost = None, None
        for reach in (0.0, 0.25, 0.5):             # next to the bubble first, then out on a short leader
            for side in prefs:
                r, al = _place(side, cx, cy, d, lw, lh, Inches(reach))
                inside = (r[0] >= plot.x and r[0] + r[2] <= box.r and r[1] >= box.y + Inches(0.25)
                          and r[1] + r[3] <= plot.b)
                cost = sum(_hit(r, o) for o in occupied if o != own) + (0 if inside else 5)
                cost += sum(_hit(r, ln) for ln in lines_) + reach * 1.5
                if best_cost is None or cost < best_cost:
                    best, best_cost = (r, al, reach), cost
                if cost == 0:
                    break
            if best_cost < 1:
                break
        (r, al, reach) = best
        if reach:
            tx = min(max(cx, r[0]), r[0] + r[2])
            ty = min(max(cy, r[1]), r[1] + r[3])
            n = math.hypot(tx - cx, ty - cy) or 1
            c.line(int(cx + (tx - cx) / n * d / 2), int(cy + (ty - cy) / n * d / 2), int(tx), int(ty), S.TEXT2, 0.75)
        lines = [[(p.label, True, S.INK)]] + ([[(p.note, False, S.TEXT2)]] if p.note else [])
        M.label(c, *r, lines, size=S.TYPE.label, align=al, name=f"bubble_label_{p.label}")
        occupied.append(r)
        anchors[p.label] = (int(cx), int(cy), d)

    # callout marker spot per bubble: the first rim position clear of every label and other bubble
    m = Inches(0.29)
    for p, cx, cy, d in geo:
        own = (int(cx - d / 2), int(cy - d / 2), d, d)
        spots = []
        for ang in (135, 45, 225, 315, 90, 180, 0, 270):
            mx = cx + math.cos(math.radians(ang)) * d * 0.5
            my = cy - math.sin(math.radians(ang)) * d * 0.5
            rr = (int(mx - m / 2), int(my - m / 2), m, m)
            spots.append((sum(_hit(rr, o) for o in occupied if o != own), int(mx), int(my)))
        cost, mx, my = min(spots, key=lambda t: t[0])
        anchors[p.label] = anchors[p.label] + ((mx, my),)
    return anchors


def _place(side: str, cx, cy, d, lw, lh, reach=0) -> tuple[Rect, object]:
    g = Inches(0.06)
    half = d / 2 + reach
    if side == "r":
        return (int(cx + half + g), int(cy - lh / 2), lw, lh), PP_ALIGN.LEFT
    if side == "l":
        return (int(cx - half - g - lw), int(cy - lh / 2), lw, lh), PP_ALIGN.RIGHT
    if side == "t":
        return (int(cx - lw / 2), int(cy - half - g - lh), lw, lh), PP_ALIGN.CENTER
    if side == "b":
        return (int(cx - lw / 2), int(cy + half + g), lw, lh), PP_ALIGN.CENTER
    dx = half * 0.75 + g
    if side == "tr":
        return (int(cx + dx), int(cy - dx - lh), lw, lh), PP_ALIGN.LEFT
    if side == "br":
        return (int(cx + dx), int(cy + dx), lw, lh), PP_ALIGN.LEFT
    if side == "tl":
        return (int(cx - dx - lw), int(cy - dx - lh), lw, lh), PP_ALIGN.RIGHT
    return (int(cx - dx - lw), int(cy + dx), lw, lh), PP_ALIGN.RIGHT
