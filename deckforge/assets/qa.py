"""Technical image QA (part of QA-9). Model-based scorers (relevance, aesthetics) plug in on GPU nodes."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from PIL import Image


def laplacian_variance(img: Image.Image, size: int = 512) -> float:
    """Sharpness proxy: variance of the Laplacian on a fixed-width greyscale copy."""
    w, h = img.size
    g = np.asarray(img.convert("L").resize((size, max(1, int(size * h / w)))), dtype=np.float32)
    lap = -4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:]
    return float(lap.var())


def dhash(img: Image.Image, size: int = 8) -> int:
    g = np.asarray(img.convert("L").resize((size + 1, size), Image.BILINEAR), dtype=np.int16)
    bits = (g[:, 1:] > g[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


@dataclass
class ImageQA:
    width: int
    height: int
    sharpness: float
    hash: int
    reasons: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.reasons

    def as_dict(self) -> dict:
        return {"width": self.width, "height": self.height, "sharpness": round(self.sharpness, 1),
                "dhash": f"{self.hash:016x}", "passed": self.passed, "reasons": self.reasons}


def check(img: Image.Image, *, min_width: int, min_sharpness: float | None = None,
          seen_hashes: list[int] = (), max_similar_bits: int = 6) -> ImageQA:
    q = ImageQA(img.width, img.height, laplacian_variance(img), dhash(img))
    if img.width < min_width:
        q.reasons.append(f"width {img.width}px below {min_width}px")
    if min_sharpness is not None and q.sharpness < min_sharpness:
        q.reasons.append(f"sharpness {q.sharpness:.0f} below {min_sharpness:.0f}")
    if any(hamming(q.hash, h) <= max_similar_bits for h in seen_hashes):
        q.reasons.append("near-duplicate of an image already in the deck")
    return q
