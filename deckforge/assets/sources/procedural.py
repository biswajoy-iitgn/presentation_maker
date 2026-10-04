"""Procedural backgrounds: owned by construction, brand-coloured, available air-gapped.

Styles follow the image roles seen in the corpus:
- light_arcs:    dark cover with glowing arcs and soft light columns (keynote covers)
- light_planes:  bright architectural interior with light shafts (keynote backdrops)
- motion_streaks: long-exposure light trails converging to a vanishing point (header bands, panels)
- aurora:        soft colour fields on dark (closing and divider slides)
- contours:      faint topographic lines on light (subtle content backdrops)
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from deckforge.assets.treatment import hex_rgb


def _grid(w, h):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return xx, yy


def _finish(img: np.ndarray, rng, grain=0.012, vignette=0.0) -> Image.Image:
    h, w = img.shape[:2]
    if vignette:
        xx, yy = _grid(w, h)
        r = ((xx / w - 0.5) ** 2 + (yy / h - 0.5) ** 2) / 0.5
        img = img * (1 - vignette * r)[..., None]
    img = img + rng.normal(0, grain, img.shape).astype(np.float32)   # grain hides banding
    return Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))


def _screen(a, b):
    return 1 - (1 - a) * (1 - b)


def light_arcs(w=1920, h=1080, palette=("#060D1F", "#1D3F8F", "#38BDF8"), seed=0,
               arcs=((1.32, 0.52, 0.62), (-0.30, 0.38, 0.78))) -> Image.Image:
    rng = np.random.default_rng(seed)
    deep, mid, glow = (hex_rgb(c) for c in palette)
    xx, yy = _grid(w, h)
    # radial base, brighter off-centre
    r = np.sqrt(((xx - 0.6 * w) / w) ** 2 + ((yy - 0.45 * h) / h) ** 2)
    t = np.clip(r / 0.85, 0, 1) ** 0.9
    img = mid * (1 - t[..., None]) * 0.75 + deep * (0.25 + 0.75 * t[..., None])
    # soft vertical light columns for depth
    for xc, width, amp in ((0.30, 0.05, 0.22), (0.82, 0.07, 0.28), (0.12, 0.03, 0.12)):
        band = amp * np.exp(-((xx / w - xc) / width) ** 2) * (0.6 + 0.4 * np.sin(yy / h * np.pi))
        img = _screen(img, band[..., None] * glow)
    # glowing arcs: circles centred off-canvas so only an arc shows
    for cx, cy, rad in arcs:
        d = np.abs(np.sqrt((xx - cx * w) ** 2 + (yy - cy * h) ** 2) - rad * w)
        fade = np.exp(-((yy - cy * h) / (0.75 * h)) ** 2)
        core = np.exp(-(d / 1.6) ** 2) * fade
        halo = (0.55 * np.exp(-(d / 14) ** 2) + 0.25 * np.exp(-(d / 70) ** 2)) * fade
        img = _screen(img, halo[..., None] * glow)
        img = _screen(img, core[..., None] * (0.35 * glow + 0.65))
    return _finish(img, rng, vignette=0.35)


def light_planes(w=1920, h=1080, palette=("#C9CEDB", "#DDE1EA", "#F7F8FB"), seed=0) -> Image.Image:
    """Bright, low-contrast interior: wall planes, a floor line and one diagonal light shaft."""
    rng = np.random.default_rng(seed)
    shade, base, light = (hex_rgb(c) for c in palette)
    xx, yy = _grid(w, h)
    img = base * (1 - 0.15 * (yy / h))[..., None] + shade * (0.15 * (yy / h))[..., None]

    def plane(poly, color, blur, strength):
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).polygon([(x * w, y * h) for x, y in poly], fill=255)
        a = np.asarray(m.filter(ImageFilter.GaussianBlur(blur)), dtype=np.float32)[..., None] / 255 * strength
        return a, color

    layers = [
        plane([(0, 0), (0.17, 0), (0.17, 0.83), (0, 0.90)], shade, 6, 0.55),          # left wall
        plane([(0.17, 0.83), (1, 0.84), (1, 1), (0, 1), (0, 0.9)], light, 10, 0.55),    # floor
        plane([(0.50, 0), (0.62, 0), (0.12, 1), (-0.05, 1)], light, 40, 0.65),          # light shaft
        plane([(0.78, 0), (1, 0), (1, 0.25)], shade, 30, 0.35),                          # ceiling shade
        plane([(0.035, 0.47), (0.115, 0.45), (0.115, 0.85), (0.035, 0.88)], np.ones(3), 7, 0.7),   # window light
    ]
    for a, color in layers:
        img = img * (1 - a) + color * a
    return _finish(img, rng, grain=0.006)


def motion_streaks(w=1920, h=600, palette=("#05070D", "#FF5A36", "#E8F1FF"), seed=0,
                   vanish=(0.52, 0.42), n=520) -> Image.Image:
    """Long-exposure traffic trails: warm on one side, cool on the other."""
    rng = np.random.default_rng(seed)
    deep, warm, cool = (hex_rgb(c) for c in palette)
    vx, vy = vanish[0] * w, vanish[1] * h
    layers = {"warm": Image.new("L", (w, h), 0), "cool": Image.new("L", (w, h), 0)}
    draws = {k: ImageDraw.Draw(v) for k, v in layers.items()}
    reach = 1.3 * max(w, h)
    for _ in range(n):
        side = rng.random() < 0.5
        lane = rng.choice([5.0, 13.0, 22.0], p=[0.25, 0.5, 0.25])     # elevated lights, road, near lane
        ang = np.deg2rad(rng.normal(lane, 4) if side else 180 - rng.normal(lane, 4))
        ang += np.deg2rad(rng.normal(0, 1.5))
        r0 = rng.uniform(0.02, 0.4) * reach
        r1 = r0 + rng.uniform(0.15, 0.7) * reach
        p0 = (vx + r0 * np.cos(ang), vy + r0 * np.sin(ang) * 0.9)
        p1 = (vx + r1 * np.cos(ang), vy + r1 * np.sin(ang) * 0.9)
        width = max(1, int(rng.uniform(1, 4) * r1 / reach * 3))
        draws["warm" if side else "cool"].line([p0, p1], fill=int(rng.uniform(70, 255)), width=width)
    img = np.ones((h, w, 3), np.float32) * deep
    xx, yy = _grid(w, h)
    img = img + (0.10 * np.exp(-((yy - vy) / (0.35 * h)) ** 2))[..., None] * cool   # horizon haze
    for key, color in (("warm", warm), ("cool", cool)):
        sharp = np.asarray(layers[key].filter(ImageFilter.GaussianBlur(1.2)), np.float32)[..., None] / 255
        glow = np.asarray(layers[key].filter(ImageFilter.GaussianBlur(9)), np.float32)[..., None] / 255
        img = _screen(img, sharp * (0.6 * color + 0.4))
        img = _screen(img, glow * color * 0.9)
    return _finish(img, rng, grain=0.01, vignette=0.25)


def aurora(w=1920, h=1080, palette=("#060D1F", "#1D3F8F", "#0EA5A4"), seed=0, blobs=6) -> Image.Image:
    rng = np.random.default_rng(seed)
    deep, c1, c2 = (hex_rgb(c) for c in palette)
    xx, yy = _grid(w, h)
    img = np.ones((h, w, 3), np.float32) * deep
    for k in range(blobs):
        cx, cy = rng.uniform(0.2, 1.0) * w, rng.uniform(0.0, 0.9) * h
        sx, sy = rng.uniform(0.15, 0.35) * w, rng.uniform(0.10, 0.3) * h
        g = np.exp(-(((xx - cx) / sx) ** 2 + ((yy - cy) / sy) ** 2))
        img = _screen(img, (g * rng.uniform(0.35, 0.7))[..., None] * (c1 if k % 2 else c2))
    return _finish(img, rng, vignette=0.3)


def contours(w=1920, h=1080, palette=("#FFFFFF", "#D5DBE5"), seed=0, levels=26) -> Image.Image:
    rng = np.random.default_rng(seed)
    paper, line = (hex_rgb(c) for c in palette)
    xx, yy = _grid(w, h)
    field = np.zeros((h, w), np.float32)
    for _ in range(7):
        cx, cy = rng.uniform(-0.2, 1.2) * w, rng.uniform(-0.2, 1.2) * h
        s = rng.uniform(0.15, 0.45) * w
        field += rng.uniform(0.5, 1.0) * np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * s * s)))
    scaled = (field - field.min()) / (field.max() - field.min()) * levels
    gy, gx = np.gradient(scaled)
    frac = scaled % 1.0
    to_level = np.minimum(frac, 1.0 - frac)                 # distance to nearest iso-level, level units
    px_dist = to_level / (np.hypot(gx, gy) + 1e-6)          # approximate distance in pixels
    a = np.clip(1.0 - px_dist / 1.1, 0, 1)                  # about 2 px anti-aliased stroke
    img = paper * (1 - a[..., None]) + line * a[..., None]
    return _finish(img, rng, grain=0.004)


STYLES = {
    "light_arcs": light_arcs,
    "light_planes": light_planes,
    "motion_streaks": motion_streaks,
    "aurora": aurora,
    "contours": contours,
}
