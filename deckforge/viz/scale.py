"""Scales, nice ticks and number formats used by every exhibit."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Linear:
    """Maps a data domain onto a pixel (EMU) range. Range may be inverted (y axes)."""
    d0: float
    d1: float
    r0: int
    r1: int

    def __call__(self, v: float) -> int:
        if self.d1 == self.d0:
            return self.r0
        return int(self.r0 + (v - self.d0) / (self.d1 - self.d0) * (self.r1 - self.r0))

    def length(self, dv: float) -> int:
        return abs(self(self.d0 + dv) - self(self.d0))


def nice_step(span: float, target_ticks: int = 5) -> float:
    raw = span / max(1, target_ticks)
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


def nice_domain(lo: float, hi: float, target_ticks: int = 5, include_zero: bool = True) -> tuple[float, float, float]:
    if include_zero:
        lo, hi = min(0.0, lo), max(0.0, hi)
    step = nice_step(hi - lo or abs(hi) or 1, target_ticks)
    return math.floor(lo / step) * step, math.ceil(hi / step) * step, step


def fmt_num(v: float, decimals: int = 0, prefix: str = "", suffix: str = "", sign: bool = False) -> str:
    s = f"{abs(v):,.{decimals}f}"
    neg = v < 0 and round(abs(v), decimals) != 0
    sign_str = "\u2212" if neg else ("+" if sign and v > 0 else "")     # typographic minus
    return f"{sign_str}{prefix}{s}{suffix}"


def fmt_inr_cr(v: float, decimals: int = 0, sign: bool = False) -> str:
    return fmt_num(v, decimals, prefix="₹", suffix=" cr", sign=sign)


def fmt_pct(v: float, decimals: int = 1, sign: bool = False) -> str:
    return fmt_num(v, decimals, suffix="%", sign=sign)


def fmt_bps(v: float, sign: bool = True) -> str:
    return fmt_num(v, 0, suffix=" bps", sign=sign)
