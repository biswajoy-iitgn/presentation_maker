"""Deterministic image treatment: legibility maths, colour grading, saliency-aware cropping."""

from __future__ import annotations

import math

import numpy as np
from PIL import Image


def hex_rgb(h: str) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32) / 255


def _linear(c: np.ndarray) -> np.ndarray:
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def luminance(color: str) -> float:
    r, g, b = _linear(hex_rgb(color))
    return float(0.2126 * r + 0.7152 * g + 0.0722 * b)


def luminance_map(img: Image.Image) -> np.ndarray:
    a = _linear(np.asarray(img.convert("RGB"), dtype=np.float32) / 255)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def contrast_ratio(l1: float, l2: float) -> float:
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def _pixel_window(img_box, region_box, size):
    """Map an EMU region onto pixel coordinates of an image placed at img_box."""
    ix, iy, iw, ih = img_box
    rx, ry, rw, rh = region_box
    W, H = size
    x0 = max(0, int((rx - ix) / iw * W))
    y0 = max(0, int((ry - iy) / ih * H))
    x1 = min(W, max(x0 + 1, int((rx + rw - ix) / iw * W)))
    y1 = min(H, max(y0 + 1, int((ry + rh - iy) / ih * H)))
    return x0, y0, x1, y1


def region_luminance(img: Image.Image, img_box, region_box) -> np.ndarray:
    x0, y0, x1, y1 = _pixel_window(img_box, region_box, img.size)
    return luminance_map(img.crop((x0, y0, x1, y1)))


def gradient_alpha(w: int, h: int, a0: float, a1: float, angle_deg: float) -> np.ndarray:
    """Alpha field of an OOXML linear gradient (angle clockwise from the x axis)."""
    t = math.radians(angle_deg)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    proj = xx * math.cos(t) + yy * math.sin(t)
    corners = [0, (w - 1) * math.cos(t), (h - 1) * math.sin(t), (w - 1) * math.cos(t) + (h - 1) * math.sin(t)]
    lo, hi = min(corners), max(corners)
    s = (proj - lo) / (hi - lo) if hi > lo else np.zeros_like(proj)
    return a0 + (a1 - a0) * s


def composite_gradient(img: Image.Image, img_box, scrim_box, color: str, a0: float, a1: float,
                       angle_deg: float) -> Image.Image:
    """Apply a gradient scrim to the part of img under scrim_box (used for QA, mirrors the PPTX shape)."""
    out = np.asarray(img.convert("RGB"), dtype=np.float32) / 255
    W, H = img.size
    sx0, sy0, sx1, sy1 = _pixel_window(img_box, scrim_box, (W, H))
    # alpha over the full scrim extent, then clipped to the part that lies on the image
    full_w = max(1, int(scrim_box[2] / img_box[2] * W))
    full_h = max(1, int(scrim_box[3] / img_box[3] * H))
    alpha = gradient_alpha(full_w, full_h, a0, a1, angle_deg)
    off_x = max(0, int((img_box[0] - scrim_box[0]) / img_box[2] * W))
    off_y = max(0, int((img_box[1] - scrim_box[1]) / img_box[3] * H))
    a = alpha[off_y:off_y + (sy1 - sy0), off_x:off_x + (sx1 - sx0)]
    region = out[sy0:sy0 + a.shape[0], sx0:sx0 + a.shape[1]]
    region[:] = region * (1 - a[..., None]) + hex_rgb(color) * a[..., None]
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))


def duotone(img: Image.Image, dark: str, light: str, strength: float = 1.0) -> Image.Image:
    """Map luminance onto a two-colour ramp, blended with the original by strength."""
    src = np.asarray(img.convert("RGB"), dtype=np.float32) / 255
    lum = (0.299 * src[..., 0] + 0.587 * src[..., 1] + 0.114 * src[..., 2])[..., None]
    graded = hex_rgb(dark) * (1 - lum) + hex_rgb(light) * lum
    out = src * (1 - strength) + graded * strength
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))


def _box3(a: np.ndarray) -> np.ndarray:
    p = np.pad(a, 1, mode="edge")
    return sum(p[i:i + a.shape[0], j:j + a.shape[1]] for i in range(3) for j in range(3)) / 9


def saliency(img: Image.Image, size: int = 96) -> np.ndarray:
    """Spectral residual saliency (Hou and Zhang, 2007) on a small greyscale copy, values 0..1."""
    w, h = img.size
    small = img.convert("L").resize((size, max(1, int(size * h / w))), Image.BILINEAR)
    g = np.asarray(small, dtype=np.float32) / 255
    f = np.fft.fft2(g)
    log_amp = np.log(np.abs(f) + 1e-8)
    residual = log_amp - _box3(log_amp)
    s = np.abs(np.fft.ifft2(np.exp(residual + 1j * np.angle(f)))) ** 2
    for _ in range(3):
        s = _box3(s)
    s -= s.min()
    return s / (s.max() + 1e-8)


def smart_crop(img: Image.Image, aspect: float, avoid: tuple[float, float, float, float] | None = None,
               scales=(1.0, 0.9, 0.8)) -> Image.Image:
    """Crop to aspect (w/h) keeping salient mass inside the frame and out of the text zone.

    avoid: text zone as fractions (x, y, w, h) of the output frame.
    """
    W, H = img.size
    sal = saliency(img)
    sh, sw = sal.shape
    best, best_score = None, -1e9
    for scale in scales:
        cw = min(W, int(H * aspect)) * scale
        ch = cw / aspect
        if ch > H:
            ch, cw = H * scale, H * scale * aspect
        for fx in np.linspace(0, 1, 9):
            for fy in np.linspace(0, 1, 5):
                x0, y0 = fx * (W - cw), fy * (H - ch)
                a, b = int(x0 / W * sw), int(y0 / H * sh)
                c_, d = max(a + 1, int((x0 + cw) / W * sw)), max(b + 1, int((y0 + ch) / H * sh))
                inside = sal[b:d, a:c_].sum()
                penalty = 0.0
                if avoid:
                    ax0 = a + int(avoid[0] * (c_ - a))
                    ay0 = b + int(avoid[1] * (d - b))
                    ax1 = ax0 + max(1, int(avoid[2] * (c_ - a)))
                    ay1 = ay0 + max(1, int(avoid[3] * (d - b)))
                    penalty = sal[ay0:ay1, ax0:ax1].sum()
                score = inside - 2.0 * penalty + 0.05 * scale * sal.sum()
                if score > best_score:
                    best, best_score = (int(x0), int(y0), int(x0 + cw), int(y0 + ch)), score
    return img.crop(best)


def scrim_alpha_for(img: Image.Image, img_box, text_box, text_color: str, scrim_color: str,
                    need: float, angle_deg: float = 0, start: float = 0.0) -> float:
    """Smallest uniform scrim alpha (0.05 steps) that brings the text region to the needed contrast."""
    fg = luminance(text_color)
    for a in np.arange(start, 0.96, 0.05):
        test = composite_gradient(img, img_box, text_box, scrim_color, float(a), float(a), angle_deg)
        lum = region_luminance(test, img_box, text_box)
        worst = np.percentile(lum, 95) if fg > 0.4 else np.percentile(lum, 5)
        if contrast_ratio(fg, float(worst)) >= need:
            return float(round(a, 2))
    return 0.95
