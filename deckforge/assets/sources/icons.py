"""Open icon sets and flags, fetched as SVG, recoloured, rasterised at slide resolution."""

from __future__ import annotations

import io
import re

import cairosvg
from PIL import Image

from deckforge.assets.cache import HttpGet, http_get

ICON_SETS = {
    # name: (url template, licence, attribution)
    "lucide": ("https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/{name}.svg",
               "ISC", "Lucide contributors"),
    "tabler": ("https://raw.githubusercontent.com/tabler/tabler-icons/main/icons/outline/{name}.svg",
               "MIT", "Tabler Icons, Pawel Kuna"),
}
FLAGS = ("https://raw.githubusercontent.com/lipis/flag-icons/main/flags/4x3/{code}.svg", "MIT",
         "flag-icons, Panayiotis Lipiridis")


def icon_svg(name: str, icon_set: str = "lucide", get: HttpGet = http_get) -> tuple[str, str]:
    url = ICON_SETS[icon_set][0].format(name=name)
    return get(url, None).decode(), url


def recolour(svg: str, color: str, stroke_width: float | None = None) -> str:
    svg = svg.replace("currentColor", color)
    if stroke_width is not None:
        svg = re.sub(r'stroke-width="[\d.]+"', f'stroke-width="{stroke_width}"', svg, count=1)
    return svg


def rasterise(svg: str, width_px: int, height_px: int | None = None) -> Image.Image:
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=width_px, output_height=height_px)
    return Image.open(io.BytesIO(png)).convert("RGBA")


def icon_png(name: str, color: str, px: int = 256, icon_set: str = "lucide", stroke_width: float = 1.5,
             get: HttpGet = http_get) -> tuple[Image.Image, str]:
    svg, url = icon_svg(name, icon_set, get)
    return rasterise(recolour(svg, color, stroke_width), px, px), url


def flag_png(code: str, width_px: int = 240, get: HttpGet = http_get) -> tuple[Image.Image, str]:
    url = FLAGS[0].format(code=code.lower())
    svg = get(url, None).decode()
    return rasterise(svg, width_px, int(width_px * 3 / 4)), url
