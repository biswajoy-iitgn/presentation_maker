"""Text measurement with the same font files the renderer resolves.

fontconfig decides which file LibreOffice (and our rasteriser) uses for a family name, so
we ask fontconfig too. Metric-compatible substitutes (Liberation Sans for Arial, Gelasio for
Georgia) wrap exactly like the originals in PowerPoint.
"""

from __future__ import annotations

import functools
import subprocess

from PIL import ImageFont

EMU_PER_PT = 12700
LEADING = 1.2   # PowerPoint single spacing is roughly 1.2 x font size for these families


@functools.lru_cache(maxsize=64)
def font_file(family: str, bold: bool) -> tuple[str, str]:
    pattern = f"{family}:bold" if bold else family
    out = subprocess.run(["fc-match", "-f", "%{file}|%{style}", pattern],
                         capture_output=True, text=True, check=True).stdout
    path, _, style = out.partition("|")
    return path, style.split(",")[0]


@functools.lru_cache(maxsize=64)
def _font(family: str, bold: bool) -> ImageFont.FreeTypeFont:
    path, style = font_file(family, bold)
    f = ImageFont.truetype(path, 1000)
    try:
        names = [n.decode() if isinstance(n, bytes) else n for n in f.get_variation_names()]
        if style in names:
            f.set_variation_by_name(style)
        elif bold and "Bold" in names:
            f.set_variation_by_name("Bold")
    except OSError:
        pass   # static font, no variation axes
    return f


def text_width_pt(s: str, family: str, size: float, bold: bool = False) -> float:
    return _font(family, bold).getlength(s) * size / 1000


def wrap(s: str, family: str, size: float, bold: bool, width_emu: int) -> list[str]:
    """Greedy word wrap using real glyph advances."""
    max_pt = width_emu / EMU_PER_PT
    lines: list[str] = []
    for para in s.split("\n"):
        cur = ""
        for word in para.split():
            trial = f"{cur} {word}".strip()
            if text_width_pt(trial, family, size, bold) <= max_pt or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def text_height(s: str, family: str, size: float, bold: bool, width_emu: int,
                leading: float = LEADING) -> int:
    return int(len(wrap(s, family, size, bold, width_emu)) * size * leading * EMU_PER_PT)


def fit_size(s: str, family: str, bold: bool, width_emu: int, height_emu: int,
             max_size: float, min_size: float, step: float = 1.0) -> float | None:
    """Largest size in [min_size, max_size] at which the text fits the box, else None."""
    size = max_size
    while size >= min_size:
        if text_height(s, family, size, bold, width_emu) <= height_emu:
            return size
        size -= step
    return None
