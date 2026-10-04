"""Deterministic QA (QA-5 geometry, legibility part of QA-9) over the canvas placement records."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from pptx.util import Inches

from deckforge.assets.treatment import contrast_ratio, luminance, region_luminance
from deckforge.render.canvas import Deck, Placed

TOL = Inches(0.02)


@dataclass(frozen=True)
class Issue:
    slide: int
    code: str
    message: str

    def __str__(self) -> str:
        return f"slide {self.slide} [{self.code}] {self.message}"


def _overlap(a, b) -> bool:
    return (a[0] + TOL < b[0] + b[2] and b[0] + TOL < a[0] + a[2]
            and a[1] + TOL < b[1] + b[3] and b[1] + TOL < a[1] + a[3])


def _contains(outer, x, y) -> bool:
    return outer[0] <= x <= outer[0] + outer[2] and outer[1] <= y <= outer[1] + outer[3]


def min_contrast(size: float, bold: bool) -> float:
    """WCAG 2.2 SC 1.4.3: large text (>= 18 pt, or >= 14 pt bold) needs 3:1, other text 4.5:1."""
    return 3.0 if size >= 18 or (bold and size >= 14) else 4.5


def text_contrast(text: Placed, below: list[Placed], paper: str) -> float:
    cx, cy = text.box[0] + text.box[2] // 2, text.box[1] + text.box[3] // 2
    bg = next((p for p in reversed(below) if p.kind in ("image", "fill") and _contains(p.box, cx, cy)), None)
    fg = luminance(text.color)
    if bg is None or bg.kind == "fill":
        return contrast_ratio(fg, luminance(bg.color if bg else paper))
    lum = region_luminance(bg.image, bg.box, text.box)
    worst = np.percentile(lum, 95) if fg > 0.4 else np.percentile(lum, 5)
    return contrast_ratio(fg, float(worst))


def lint(deck: Deck) -> list[Issue]:
    issues: list[Issue] = []
    for c in deck.slides:
        texts = [(i, p) for i, p in enumerate(c.placed) if p.kind in ("text", "sticker")]
        for k, (i, a) in enumerate(texts):
            x, y, w, h = a.box
            if x < 0 or y < 0 or x + w > deck.width + TOL or y + h > deck.height + TOL:
                issues.append(Issue(c.index, "off_slide", f"'{a.name}' runs off the slide"))
            for _, b in texts[k + 1:]:
                if _overlap(a.box, b.box):
                    issues.append(Issue(c.index, "overlap", f"'{a.name}' overlaps '{b.name}'"))
            if a.kind == "text":
                ratio = text_contrast(a, c.placed[:i], deck.theme.paper)
                need = min_contrast(a.size, a.bold)
                if ratio < need:
                    issues.append(Issue(c.index, "contrast",
                                        f"'{a.name}' contrast {ratio:.1f}:1 below {need}:1"))
    return issues
