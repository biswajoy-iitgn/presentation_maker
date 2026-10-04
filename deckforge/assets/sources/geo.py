"""World map as native, editable PowerPoint shapes from Natural Earth (public domain) boundaries."""

from __future__ import annotations

import json
from dataclasses import dataclass

from deckforge.assets.cache import HttpGet, http_get

NATURAL_EARTH_110M = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
                      "ne_110m_admin_0_countries.geojson")
LICENCE = "Public domain (Natural Earth)"

LAT_TOP, LAT_BOTTOM = 84.0, -57.0      # Antarctica excluded, as in consulting world maps


@dataclass
class Country:
    iso3: str
    name: str
    rings: list[list[tuple[float, float]]]    # outer rings only, lon/lat
    label: tuple[float, float]


def load_countries(get: HttpGet = http_get) -> dict[str, Country]:
    data = json.loads(get(NATURAL_EARTH_110M, None))
    out: dict[str, Country] = {}
    for f in data["features"]:
        p = f["properties"]
        iso3 = p.get("ADM0_A3") or p.get("ISO_A3")
        if iso3 == "ATA":
            continue
        geom = f["geometry"]
        polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        rings = [[tuple(pt) for pt in poly[0]] for poly in polys]
        label = (p.get("LABEL_X"), p.get("LABEL_Y"))
        if label[0] is None:
            biggest = max(rings, key=len)
            label = (sum(x for x, _ in biggest) / len(biggest), sum(y for _, y in biggest) / len(biggest))
        out[iso3] = Country(iso3, p.get("NAME", iso3), rings, label)
    return out


def projector(box: tuple[int, int, int, int]):
    """Equirectangular projection fitted into box (EMU), aspect preserved, centred."""
    x, y, w, h = box
    span_lon, span_lat = 360.0, LAT_TOP - LAT_BOTTOM
    scale = min(w / span_lon, h / span_lat)
    ox = x + (w - span_lon * scale) / 2
    oy = y + (h - span_lat * scale) / 2

    def proj(lon: float, lat: float) -> tuple[int, int]:
        lat = max(LAT_BOTTOM, min(LAT_TOP, lat))
        return int(ox + (lon + 180) * scale), int(oy + (LAT_TOP - lat) * scale)
    return proj, scale


def ring_area(ring) -> float:
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]))) / 2


def draw_world(canvas, box, highlight: dict[str, str], base: str, *, min_area_deg2=0.6,
               outline: tuple[str, float] | None = None, countries: dict[str, Country] | None = None
               ) -> dict[str, tuple[int, int]]:
    """Draw every country as a freeform. Returns label anchor points (EMU) for highlighted ones."""
    countries = countries or load_countries()
    proj, _ = projector(box)
    anchors = {}
    for iso3, ctry in countries.items():
        rings = [r for r in ctry.rings if ring_area(r) >= min_area_deg2]
        if not rings:
            continue
        contours = [[proj(lon, lat) for lon, lat in r] for r in rings]
        fill = highlight.get(iso3, base)
        canvas.freeform(contours, fill, line=outline, name=f"map_{iso3}")
        if iso3 in highlight:
            anchors[iso3] = proj(*ctry.label)
    return anchors
