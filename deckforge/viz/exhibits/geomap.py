"""Site map with sized markers beside a ranked bar of the same measure: where it is, and how much.

Country outlines come from Natural Earth (public domain) and are drawn as native editable shapes.
"""

from __future__ import annotations

import json
import math
from typing import Callable

from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches

from deckforge.assets.cache import http_get
from deckforge.render.canvas import Canvas
from deckforge.viz import marks as M
from deckforge.viz import style as S
from deckforge.viz.frame import Box
from deckforge.viz.scale import Linear

NE_50M = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson"


def _hit(a, b) -> bool:
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


_SIDES = ("r", "l", "ur", "dr", "ul", "dl", "u", "d")


def _dodge(pos: dict[str, list], dia: dict[str, int], gap=Inches(0.03), rounds: int = 60) -> bool:
    """Push overlapping markers apart (bigger markers move less). Returns True if anything moved."""
    moved = False
    names = list(pos)
    for _ in range(rounds):
        clean = True
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                (ax, ay), (bx, by) = pos[a], pos[b]
                need = (dia[a] + dia[b]) / 2 + gap
                dx, dy = bx - ax, by - ay
                dist = math.hypot(dx, dy)
                if dist >= need:
                    continue
                clean, moved = False, True
                if dist < 1:
                    dx, dy, dist = 0.0, 1.0, 1.0
                push = need - dist
                wa = dia[b] / (dia[a] + dia[b])
                pos[a] = [ax - dx / dist * push * wa, ay - dy / dist * push * wa]
                pos[b] = [bx + dx / dist * push * (1 - wa), by + dy / dist * push * (1 - wa)]
        if clean:
            break
    for n in pos:
        pos[n] = [int(pos[n][0]), int(pos[n][1])]
    return moved


def _label_rect(side: str, cx, cy, d, w, h, reach):
    """Label box beside the marker on one side, pushed out by reach. Returns rect, alignment, leader end."""
    g = Inches(0.05)
    half = d / 2
    k = 0.72
    if side == "r":
        x, y = cx + half + g + reach, cy - h / 2
        return (int(x), int(y), w, h), PP_ALIGN.LEFT, (int(x - g / 2), int(cy))
    if side == "l":
        x, y = cx - half - g - reach - w, cy - h / 2
        return (int(x), int(y), w, h), PP_ALIGN.RIGHT, (int(x + w + g / 2), int(cy))
    if side == "u":
        x, y = cx - w / 2, cy - half - g - reach - h
        return (int(x), int(y), w, h), PP_ALIGN.CENTER, (int(cx), int(y + h))
    if side == "d":
        x, y = cx - w / 2, cy + half + g + reach
        return (int(x), int(y), w, h), PP_ALIGN.CENTER, (int(cx), int(y))
    sx = 1 if side[1] == "r" else -1
    sy = -1 if side[0] == "u" else 1
    ox = cx + sx * (half * k + g + reach * 0.8)
    oy = cy + sy * (half * k + reach * 0.6)
    x = ox if sx > 0 else ox - w
    y = oy - h if sy < 0 else oy
    return (int(x), int(y), w, h), PP_ALIGN.LEFT if sx > 0 else PP_ALIGN.RIGHT, (int(ox), int(oy))


def _edge(cx, cy, d, to):
    dx, dy = to[0] - cx, to[1] - cy
    n = math.hypot(dx, dy) or 1
    return int(cx + dx / n * d / 2), int(cy + dy / n * d / 2)


def _ccw(a, b, c) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _cross(s1, s2) -> bool:
    a, b = s1
    c, d = s2
    return _ccw(a, b, c) * _ccw(a, b, d) < 0 and _ccw(c, d, a) * _ccw(c, d, b) < 0


def _seg_hits_rect(seg, r) -> bool:
    x, y, w, h = r
    (ax, ay), (bx, by) = seg
    for t in (0.2, 0.4, 0.6, 0.8):
        px, py = ax + (bx - ax) * t, ay + (by - ay) * t
        if x < px < x + w and y < py < y + h:
            return True
    return False


def _country_rings(iso3: str, get=http_get) -> list[list[tuple[float, float]]]:
    data = json.loads(get(NE_50M, None))
    for f in data["features"]:
        p = f["properties"]
        if iso3 in (p.get("ADM0_A3"), p.get("ISO_A3")):
            g = f["geometry"]
            polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
            return [[tuple(pt) for pt in poly[0]] for poly in polys]
    raise KeyError(iso3)


def site_map(c: Canvas, box: Box, *, country: str, sites: list[dict], value_title: str,
             fmt_value: Callable[[float], str], size_note: str = "", highlight: set[str] = frozenset(),
             label_side: dict[str, str] | None = None, split: float = 0.5, hot_color: str | None = None,
             max_d=Inches(0.6), get=http_get) -> dict:
    """sites: name, lat, lon, size (marker area), value (ranked bar), note.

    Markers that would overlap (plants in one cluster) are pushed apart until they touch, then each label
    takes the position next to its marker that collides with nothing; a leader is drawn only when the
    label must sit away from the marker, and leaders may not cross each other or pass over a marker.
    hot_color: colour of the highlighted sites, e.g. the negative colour when the measure is a cost gap.
    """
    map_box, bar_box = box.split_x(split, gap=Inches(0.45))
    rings = _country_rings(country, get)
    lons = [x for r in rings for x, _ in r]
    lats = [y for r in rings for _, y in r]
    lat0 = math.radians((min(lats) + max(lats)) / 2)
    xs = [lo * math.cos(lat0) for lo in lons]
    sx = map_box.w / (max(xs) - min(xs))
    sy = (map_box.h - Inches(0.3)) / (max(lats) - min(lats))
    k = min(sx, sy)
    ox = map_box.x + (map_box.w - (max(xs) - min(xs)) * k) / 2
    oy = map_box.y + Inches(0.3)

    def P(lon, lat):
        return int(ox + (lon * math.cos(lat0) - min(xs)) * k), int(oy + (max(lats) - lat) * k)

    big = [r for r in rings if len(r) > 12]
    c.freeform([[P(lo, la) for lo, la in r] for r in big], S.TRACK, line=("#FFFFFF", 0.5), name=f"map_{country}")
    smax = max(s["size"] for s in sites)
    hot_color = hot_color or S.ACCENT
    pos = {s["name"]: list(P(s["lon"], s["lat"])) for s in sites}
    dia = {s["name"]: max(Inches(0.16), int(max_d * math.sqrt(s["size"] / smax))) for s in sites}
    dodged = _dodge(pos, dia)
    note = ". ".join(x.rstrip(".") for x in (size_note, "Nearby sites offset slightly" if dodged else "") if x)
    if note:
        M.label(c, map_box.x, map_box.y, map_box.w, Inches(0.24), note, size=S.TYPE.annotation, color=S.MUTED,
                name="map_note")
    for s in sorted(sites, key=lambda q: -q["size"]):                 # big first, small drawn on top
        cx, cy = pos[s["name"]]
        M.dot(c, cx, cy, dia[s["name"]], hot_color if s["name"] in highlight else S.NEUTRAL, ring="#FFFFFF",
              name=f"site_{s['name']}")

    occupied = [(int(x - dia[n] / 2), int(y - dia[n] / 2), dia[n], dia[n]) for n, (x, y) in pos.items()]
    if note:
        occupied.append((map_box.x, map_box.y, map_box.w, Inches(0.26)))
    leaders: list[tuple[tuple[int, int], tuple[int, int]]] = []
    bounds = (map_box.x - Inches(0.25), map_box.y, map_box.r + Inches(0.25), map_box.b)
    for s in sorted(sites, key=lambda q: -q["size"]):
        name = s["name"]
        cx, cy = pos[name]
        d = dia[name]
        lines = [[(name, True, S.INK)]] + ([[(s["note"], False, S.TEXT2)]] if s.get("note") else [])
        w = max(M.text_w(name, S.TYPE.label, True), M.text_w(s.get("note", ""), S.TYPE.label, False)) + Inches(0.1)
        h = Inches(0.44 if s.get("note") else 0.26)
        own = (int(cx - d / 2), int(cy - d / 2), d, d)
        pref = (label_side or {}).get(name, "r")
        best = None
        for reach in (0.0, 0.3, 0.6, 0.95):
            for side in [pref] + [k for k in _SIDES if k != pref]:
                r, anchor, end_pt = _label_rect(side, cx, cy, d, w, h, Inches(reach))
                cost = 10 * sum(_hit(r, o) for o in occupied if o != own)
                inside = r[0] >= bounds[0] and r[0] + r[2] <= bounds[2] and r[1] >= bounds[1] and r[1] + r[3] <= bounds[3]
                cost += 0 if inside else 8
                seg = None
                if reach:
                    seg = (_edge(cx, cy, d, end_pt), end_pt)
                    cost += 6 * sum(_cross(seg, other) for other in leaders)
                    cost += 6 * sum(_seg_hits_rect(seg, o) for o in occupied if o != own)
                cost += reach * 2 + (0 if side == pref else 0.4)
                if best is None or cost < best[0]:
                    best = (cost, r, anchor, seg)
            if best[0] < 1:
                break
        _, r, anchor, seg = best
        if seg:
            c.line(*seg[0], *seg[1], S.TEXT2, 0.75)
            leaders.append(seg)
        M.label(c, *r, lines, size=S.TYPE.label, align=anchor, anchor=MSO_ANCHOR.MIDDLE, name=f"site_label_{name}")
        occupied.append(r)
    # ranked bars of the value
    ranked = sorted(sites, key=lambda q: -q["value"])
    M.label(c, bar_box.x, bar_box.y, bar_box.w, Inches(0.3), value_title, size=S.TYPE.label, bold=True,
            name="site_bar_title")
    top = bar_box.y + Inches(0.55)
    row_h = (bar_box.b - top) / len(ranked)
    name_w = Inches(1.15)
    lo = min(0.0, min(s["value"] for s in ranked))
    hi = max(s["value"] for s in ranked)
    x = Linear(lo, hi, bar_box.x + name_w + Inches(0.15), bar_box.r - Inches(0.85))
    zero = x(0)
    anchors = {}
    for i, s in enumerate(ranked):
        cy = top + row_h * (i + 0.5)
        hot = s["name"] in highlight
        color = hot_color if hot else S.NEUTRAL
        M.label(c, bar_box.x, cy - Inches(0.15), name_w, Inches(0.3), s["name"], size=S.TYPE.label, bold=hot,
                name=f"site_bar_name_{i}")
        bh = min(Inches(0.36), row_h * 0.5)
        M.bar(c, min(zero, x(s["value"])), cy - bh / 2, abs(x(s["value"]) - zero), bh, color, name=f"site_bar_{i}")
        txt = fmt_value(s["value"])
        M.label(c, max(zero, x(s["value"])) + Inches(0.08), cy - Inches(0.15), Inches(1.2), Inches(0.3), txt,
                size=S.TYPE.value, bold=True, color=(S.ACCENT_DARK if hot_color == S.ACCENT else hot_color) if hot else S.TEXT2,
                name=f"site_bar_val_{i}")
        anchors[s["name"]] = (int(max(zero, x(s["value"])) + Inches(1.15)), int(cy))
    M.vline(c, zero, top, bar_box.b, S.INK, 0.75)
    return anchors
