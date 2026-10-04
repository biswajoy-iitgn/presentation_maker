"""Peer benchmark ranges: one row per KPI, every row oriented so right is better."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches

from deckforge.render.canvas import Canvas
from deckforge.viz import marks as M
from deckforge.viz import style as S
from deckforge.viz.frame import Box
from deckforge.viz.scale import Linear


@dataclass
class KPI:
    name: str
    unit: str
    ours: float
    lo: float
    q1: float
    median: float
    q3: float
    hi: float
    higher_is_better: bool
    fmt: Callable[[float], str]

    def gap(self) -> float:
        """Positive when better than the peer median."""
        d = self.ours - self.median
        return d if self.higher_is_better else -d

    @property
    def better_than_median(self) -> bool:
        return self.gap() >= 0


def range_benchmark(c: Canvas, box: Box, kpis: list[KPI], *, ours_label: str, peers_label: str,
                    fmt_gap: Callable[[KPI], str] | None = None) -> dict:
    label_w, gap_w = Inches(2.7), Inches(1.45)
    track_x, track_w = box.x + label_w + Inches(0.95), box.w - label_w - gap_w - Inches(1.95)
    head_h, foot_h = Inches(0.45), Inches(0.5)
    row_h = (box.h - head_h - foot_h) / len(kpis)

    # header: direction cues over the tracks, gap column title
    cue_y = box.y + Inches(0.12)
    M.label(c, track_x, cue_y, Inches(1.0), Inches(0.22), "\u25c2 Worse", size=S.TYPE.annotation, color=S.MUTED,
            name="bench_worse")
    M.label(c, track_x + track_w - Inches(1.0), cue_y, Inches(1.0), Inches(0.22), "Better \u25b8",
            size=S.TYPE.annotation, color=S.MUTED, align=PP_ALIGN.RIGHT, name="bench_better")
    M.label(c, box.r - gap_w, box.y, gap_w, Inches(0.4), ["Gap to", "peer median"], size=S.TYPE.annotation,
            bold=True, color=S.INK, align=PP_ALIGN.RIGHT, name="bench_gap_head")

    # footer: legend row, then the peer set
    ly = box.b - foot_h + Inches(0.06)
    lx = box.x
    M.bar(c, lx, ly + Inches(0.07), Inches(0.3), Inches(0.08), S.TRACK, register=False)
    M.label(c, lx + Inches(0.36), ly, Inches(0.9), Inches(0.22), "Peer range", size=S.TYPE.annotation,
            color=S.TEXT2, name="lg_range")
    M.bar(c, lx + Inches(1.25), ly + Inches(0.04), Inches(0.3), Inches(0.14), S.NEUTRAL, register=False)
    M.label(c, lx + Inches(1.61), ly, Inches(1.0), Inches(0.22), "Middle 50%", size=S.TYPE.annotation,
            color=S.TEXT2, name="lg_iqr")
    M.vline(c, lx + Inches(2.65), ly + Inches(0.01), ly + Inches(0.21), S.INK, 1.5)
    M.label(c, lx + Inches(2.73), ly, Inches(0.7), Inches(0.22), "Median", size=S.TYPE.annotation, color=S.TEXT2,
            name="lg_median")
    M.dot(c, lx + Inches(3.55), ly + Inches(0.11), Inches(0.15), S.NEGATIVE)
    M.dot(c, lx + Inches(3.73), ly + Inches(0.11), Inches(0.15), S.ACCENT)
    M.label(c, lx + Inches(3.88), ly, Inches(3.4), Inches(0.22), f"{ours_label}, worse or better than median",
            size=S.TYPE.annotation, color=S.TEXT2, name="lg_ours")

    anchors = {}
    for i, k in enumerate(kpis):
        ry = box.y + head_h + row_h * i
        cy = ry + row_h / 2
        if i:
            M.hline(c, box.x, box.r, ry, S.RULE, 0.5)
        M.label(c, box.x, cy - Inches(0.22), label_w, Inches(0.46),
                [[(k.name, True, S.INK)], [(k.unit, False, S.MUTED)]], size=S.TYPE.label, anchor=MSO_ANCHOR.MIDDLE,
                name=f"bench_kpi_{i}")
        span = k.hi - k.lo
        d0, d1 = (k.lo - span * 0.06, k.hi + span * 0.06)
        x = Linear(d0, d1, track_x, track_x + track_w) if k.higher_is_better else Linear(d1, d0, track_x,
                                                                                           track_x + track_w)
        xa, xb = sorted((x(k.lo), x(k.hi)))
        M.bar(c, xa, cy - Inches(0.04), xb - xa, Inches(0.08), S.TRACK)
        qa, qb = sorted((x(k.q1), x(k.q3)))
        M.bar(c, qa, cy - Inches(0.08), qb - qa, Inches(0.16), S.NEUTRAL)
        M.vline(c, x(k.median), cy - Inches(0.15), cy + Inches(0.15), S.INK, 1.5)
        M.label(c, xa - Inches(0.9), cy - Inches(0.11), Inches(0.82), Inches(0.22), k.fmt(k.lo if k.higher_is_better
                else k.hi), size=S.TYPE.annotation, color=S.MUTED, align=PP_ALIGN.RIGHT, name=f"bench_min_{i}")
        M.label(c, xb + Inches(0.08), cy - Inches(0.11), Inches(0.82), Inches(0.22), k.fmt(k.hi if k.higher_is_better
                else k.lo), size=S.TYPE.annotation, color=S.MUTED, name=f"bench_max_{i}")
        color = S.ACCENT if k.better_than_median else S.NEGATIVE
        ox = x(k.ours)
        M.dot(c, ox, cy, Inches(0.2), color, ring="#FFFFFF", name=f"bench_ours_{i}")
        M.centered_label(c, ox, cy - Inches(0.36), k.fmt(k.ours), w=Inches(1.0), size=S.TYPE.value, bold=True,
                         color=color, name=f"bench_val_{i}")
        gap_text = fmt_gap(k) if fmt_gap else k.fmt(k.gap())
        M.label(c, box.r - gap_w, cy - Inches(0.22), gap_w, Inches(0.44),
                [[(gap_text, True, color)], [(f"median {k.fmt(k.median)}", False, S.MUTED)]], size=S.TYPE.value,
                align=PP_ALIGN.RIGHT, name=f"bench_gap_{i}")
        anchors[k.name] = (int(ox), int(cy))
    M.label(c, box.x, box.b - Inches(0.2), box.w, Inches(0.2), peers_label, size=S.TYPE.annotation, color=S.MUTED,
            name="bench_peers")
    return anchors
