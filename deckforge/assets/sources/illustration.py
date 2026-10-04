"""Isometric illustrations drawn by code: flat-shaded corporate style, palette-driven, owned by construction.

Scenes are composed from solids (boxes, prisms, cylinders, spheres) projected isometrically and painted
back to front. Each face takes the base colour lightened (top), as is (left) or darkened (right), which
gives the familiar three-tone isometric look.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFilter

from deckforge.assets.treatment import hex_rgb

COS30, SIN30 = math.cos(math.radians(30)), 0.5


def _mix(c, other, t):
    return tuple(int(255 * (a * (1 - t) + b * t)) for a, b in zip(hex_rgb(c), hex_rgb(other)))


def shades(base: str) -> tuple[tuple, tuple, tuple]:
    """(top, left, right) face colours."""
    return _mix(base, "#FFFFFF", 0.28), _mix(base, "#FFFFFF", 0.0), _mix(base, "#000000", 0.2)


@dataclass
class Iso:
    ox: float
    oy: float
    s: float

    def p(self, x, y, z=0.0):
        return self.ox + (x - y) * COS30 * self.s, self.oy + (x + y) * SIN30 * self.s - z * self.s


class Scene:
    def __init__(self, w, h, iso: Iso):
        self.w, self.h, self.iso = w, h, iso
        self.items: list[tuple[float, callable]] = []     # (depth, painter)

    def add(self, depth, painter):
        self.items.append((depth, painter))

    def render(self, ss=2) -> Image.Image:
        img = Image.new("RGBA", (self.w * ss, self.h * ss), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for _, paint in sorted(self.items, key=lambda t: t[0]):
            paint(d, ss)
        return img.resize((self.w, self.h), Image.LANCZOS)

    # ------------------------------------------------------------------ solids
    def box(self, x, y, z, dx, dy, dz, base, *, top=None, windows: str | None = None, doors=0):
        t, l, r = shades(base)
        if top:
            t = _mix(top, "#FFFFFF", 0.0)
        iso = self.iso

        def paint(d, ss):
            P = lambda *a: tuple(v * ss for v in iso.p(*a))
            d.polygon([P(x, y + dy, z), P(x + dx, y + dy, z), P(x + dx, y + dy, z + dz), P(x, y + dy, z + dz)], fill=l)
            d.polygon([P(x + dx, y, z), P(x + dx, y + dy, z), P(x + dx, y + dy, z + dz), P(x + dx, y, z + dz)], fill=r)
            d.polygon([P(x, y, z + dz), P(x + dx, y, z + dz), P(x + dx, y + dy, z + dz), P(x, y + dy, z + dz)], fill=t)
            if windows:
                wc = _mix(windows, "#FFFFFF", 0.1)
                n = max(1, int(dx / 0.7))
                for i in range(n):
                    wx = x + (i + 0.3) * dx / n
                    ww = dx / n * 0.45
                    for row in (0.35, 0.65):
                        if dz * row + 0.35 > dz:
                            continue
                        z0 = z + dz * row - 0.15
                        d.polygon([P(wx, y + dy, z0), P(wx + ww, y + dy, z0), P(wx + ww, y + dy, z0 + 0.3),
                                   P(wx, y + dy, z0 + 0.3)], fill=wc)
            for k in range(doors):
                dy0 = y + (k + 0.5) * dy / doors - 0.3
                d.polygon([P(x + dx, dy0, z), P(x + dx, dy0 + 0.6, z), P(x + dx, dy0 + 0.6, z + min(1.0, dz * 0.6)),
                           P(x + dx, dy0, z + min(1.0, dz * 0.6))], fill=_mix(base, "#000000", 0.38))
        self.add(x + y + z * 0.5 + (dx + dy) * 0.5, paint)

    def sawtooth(self, x, y, z, dx, dy, teeth, h, base, glass):
        """Factory roof: prisms running along y, glazed vertical faces looking toward -x."""
        t, l, r = shades(base)
        g = _mix(glass, "#FFFFFF", 0.15)
        iso = self.iso
        step = dx / teeth

        def paint(d, ss):
            P = lambda *a: tuple(v * ss for v in iso.p(*a))
            for i in range(teeth):
                x0 = x + i * step
                # glazed vertical face at x0 (seen from the left side as a sliver), sloped roof toward x0+step
                d.polygon([P(x0, y, z), P(x0, y + dy, z), P(x0, y + dy, z + h), P(x0, y, z + h)], fill=g)
                d.polygon([P(x0, y, z + h), P(x0, y + dy, z + h), P(x0 + step, y + dy, z), P(x0 + step, y, z)], fill=t)
                d.polygon([P(x0, y + dy, z), P(x0 + step, y + dy, z), P(x0, y + dy, z + h)], fill=l)
        self.add(x + y + z * 0.5 + (dx + dy) * 0.5 + 0.01, paint)

    def cylinder(self, x, y, z, r, h, base, *, band=None):
        t, l, rr = shades(base)
        iso = self.iso

        def paint(d, ss):
            cx, cy = iso.p(x, y, z)
            _, cyt = iso.p(x, y, z + h)
            rx, ry = r * iso.s * COS30 * 1.15 * ss, r * iso.s * SIN30 * 1.15 * ss
            cx, cy, cyt = cx * ss, cy * ss, cyt * ss
            d.rectangle([cx - rx, cyt, cx, cy], fill=l)
            d.rectangle([cx, cyt, cx + rx, cy], fill=rr)
            d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=rr)
            if band:
                bc = _mix(band, "#FFFFFF", 0.0)
                yb = cyt + (cy - cyt) * 0.22
                d.rectangle([cx - rx, yb, cx + rx, yb + (cy - cyt) * 0.1], fill=bc)
            d.ellipse([cx - rx, cyt - ry, cx + rx, cyt + ry], fill=t)
        self.add(x + y + z * 0.5, paint)

    def sphere(self, x, y, z, r, base):
        t, l, _ = shades(base)
        iso = self.iso

        def paint(d, ss):
            cx, cy = (v * ss for v in iso.p(x, y, z))
            rr = r * iso.s * ss
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=l)
            d.ellipse([cx - rr * 0.75, cy - rr * 0.95, cx + rr * 0.35, cy - rr * 0.05], fill=t)
        self.add(x + y + z * 0.5, paint)

    def tile(self, x, y, dx, dy, thick, base, *, z=0.0):
        """Ground slab with a visible edge, like a floating island."""
        self.box(x, y, z - thick, dx, dy, thick, base)
        self.items[-1] = (-1000 + self.items[-1][0], self.items[-1][1])


def factory(w=1600, h=1200, *, base="#E8EEF8", accent="#2251FF", accent2="#38BDF8", glass="#9CC3F5",
            ground="#1D3F8F", tree="#5CC896", smoke=True, seed=0) -> Image.Image:
    """Isometric manufacturing campus: forging hall, warehouse, chimneys, conveyor, trucks, trees, solar roof."""
    s = w / 25
    iso = Iso(w * 0.47, h * 0.34, s)
    sc = Scene(w, h, iso)
    sc.tile(-1, -1, 15, 12, 0.6, ground)
    # forging hall with sawtooth roof
    sc.box(0, 0, 0, 7, 4.5, 2.4, base, windows=glass, doors=2)
    sc.sawtooth(0, 0, 2.4, 7, 4.5, 5, 0.9, base, glass)
    # chimneys
    sc.cylinder(1.3, 0.6, 3.0, 0.35, 3.0, base, band=accent)
    sc.cylinder(2.6, 0.6, 3.0, 0.35, 2.4, base, band=accent)
    # warehouse with solar roof
    sc.box(8.5, 0.5, 0, 4.5, 3.5, 1.6, base, doors=3)
    for i in range(4):
        for j in range(3):
            sc.box(8.8 + i * 1.05, 0.8 + j * 1.0, 1.6, 0.9, 0.8, 0.06, accent, top=accent)
    # office block
    sc.box(0.5, 6.0, 0, 3.0, 2.5, 3.2, accent, windows="#FFFFFF")
    # conveyor between hall and warehouse
    sc.box(7.0, 2.0, 0.9, 1.5, 0.5, 0.15, accent2)
    for k in range(3):
        sc.box(7.15 + k * 0.45, 2.05, 1.05, 0.35, 0.4, 0.3, "#F4C46A")
    # trucks at the warehouse doors
    for k, ty in enumerate((5.2, 6.6)):
        sc.box(9.2, ty, 0, 2.6, 1.0, 1.0, base)
        sc.box(11.9, ty + 0.1, 0, 0.9, 0.8, 0.8, accent)
    # stock pallets
    for k in range(3):
        sc.box(4.6 + k * 0.8, 6.5, 0, 0.6, 0.6, 0.5 + 0.2 * (k % 2), "#F4C46A")
    # trees along the edge
    for tx, ty in ((13.0, 9.0), (11.5, 9.6), (5.0, 9.8), (6.6, 10.0), (-0.2, 9.6)):
        sc.cylinder(tx, ty, 0, 0.08, 0.6, "#8B6B4A")
        sc.sphere(tx, ty, 1.0, 0.55, tree)
    img = sc.render()
    if smoke:
        img = _smoke(img, [iso.p(1.3, 0.6, 6.3), iso.p(2.6, 0.6, 5.7)], s)
    return img


def _smoke(img: Image.Image, origins, s) -> Image.Image:
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for (ox, oy) in origins:
        for k in range(5):
            r = s * (0.35 + k * 0.16)
            cx, cy = ox + k * s * 0.35, oy - k * s * 0.55
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 140 - k * 22))
    layer = layer.filter(ImageFilter.GaussianBlur(s * 0.08))
    return Image.alpha_composite(img, layer)



ILLUSTRATIONS = {"factory": factory}
