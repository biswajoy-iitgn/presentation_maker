import io
import json

import pytest
from PIL import Image

SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" '
       'stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>')

GEOJSON = {"type": "FeatureCollection", "features": [
    {"type": "Feature", "properties": {"ADM0_A3": "AAA", "NAME": "Squareland", "LABEL_X": 5, "LABEL_Y": 5},
     "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]}},
    {"type": "Feature", "properties": {"ADM0_A3": "BBB", "NAME": "Islands"},
     "geometry": {"type": "MultiPolygon", "coordinates": [[[[20, 20], [24, 20], [24, 24], [20, 24], [20, 20]]],
                                                          [[[30, 30], [31, 30], [31, 31], [30, 30]]]]}},
    {"type": "Feature", "properties": {"ADM0_A3": "ATA", "NAME": "Antarctica"},
     "geometry": {"type": "Polygon", "coordinates": [[[0, -80], [10, -80], [10, -70], [0, -80]]]}},
]}


def jpeg_bytes(w=1600, h=900, color=(90, 110, 140)):
    img = Image.new("RGB", (w, h), color)
    for x in range(0, w, 40):                       # texture so the sharpness check has edges
        for y in range(0, h, 40):
            img.paste((200, 210, 220), (x, y, x + 6, y + 6))
    buf = io.BytesIO()
    img.save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture
def fake_get():
    calls = []

    def get(url, headers=None):
        calls.append((url, headers))
        if url.endswith(".svg"):
            return SVG.encode()
        if url.endswith(".geojson"):
            return json.dumps(GEOJSON).encode()
        if "api.pexels.com" in url:
            return json.dumps({"photos": [{"src": {"large2x": "https://img/p1.jpg"}, "width": 1600, "height": 900,
                                           "photographer": "A. Person", "url": "https://pexels/p1"}]}).encode()
        if "api.unsplash.com/search" in url:
            return json.dumps({"results": [{"urls": {"regular": "https://img/u1.jpg"}, "width": 1600, "height": 900,
                                            "user": {"name": "B. Person"},
                                            "links": {"html": "https://unsplash/u1",
                                                      "download_location": "https://api.unsplash.com/dl/u1"}}]}).encode()
        if "api.openverse.org" in url:
            return json.dumps({"results": [{"url": "https://img/o1.jpg", "width": 1600, "height": 900,
                                            "license": "cc0", "creator": "C", "foreign_landing_url": "https://o/1"}]}).encode()
        if url.endswith(".jpg"):
            return jpeg_bytes()
        return b"{}"

    get.calls = calls
    return get
