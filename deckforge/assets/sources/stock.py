"""Licensed stock photo sources for connected deployments. Keys come from the environment.

Each provider allows commercial use under its own terms. Provider rules that matter here:
- Pexels: Authorization header with the API key, credit encouraged.
- Unsplash: Client-ID authorisation, and the download_location endpoint must be called when a photo is used.
- Openverse: filtered to CC0 and public-domain-mark works only, so no attribution duty arises.
"""

from __future__ import annotations

import os
import urllib.parse
from dataclasses import dataclass

from deckforge.assets.cache import HttpGet, http_get, http_get_json


@dataclass
class Candidate:
    url: str
    width: int
    height: int
    source: str
    licence: str
    attribution: str | None
    page_url: str | None
    use_ping: str | None = None     # endpoint to call when the photo is actually used (Unsplash)
    headers: dict | None = None


class PexelsSource:
    name = "pexels"

    def __init__(self, api_key: str | None = None, get: HttpGet = http_get):
        self.key = api_key or os.environ.get("PEXELS_API_KEY")
        self.get = get

    @property
    def available(self) -> bool:
        return bool(self.key)

    def search(self, query: str, orientation: str = "landscape", n: int = 10) -> list[Candidate]:
        q = urllib.parse.urlencode({"query": query, "orientation": orientation, "per_page": n})
        data = http_get_json(f"https://api.pexels.com/v1/search?{q}", {"Authorization": self.key}, self.get)
        return [Candidate(p["src"]["large2x"], p["width"], p["height"], self.name, "Pexels License",
                          f"Photo by {p['photographer']} on Pexels", p["url"]) for p in data.get("photos", [])]


class UnsplashSource:
    name = "unsplash"

    def __init__(self, access_key: str | None = None, get: HttpGet = http_get):
        self.key = access_key or os.environ.get("UNSPLASH_ACCESS_KEY")
        self.get = get

    @property
    def available(self) -> bool:
        return bool(self.key)

    def search(self, query: str, orientation: str = "landscape", n: int = 10) -> list[Candidate]:
        q = urllib.parse.urlencode({"query": query, "orientation": orientation, "per_page": n})
        auth = {"Authorization": f"Client-ID {self.key}"}
        data = http_get_json(f"https://api.unsplash.com/search/photos?{q}", auth, self.get)
        return [Candidate(r["urls"]["regular"], r["width"], r["height"], self.name, "Unsplash License",
                          f"Photo by {r['user']['name']} on Unsplash", r["links"]["html"],
                          use_ping=r["links"]["download_location"], headers=auth)
                for r in data.get("results", [])]


class OpenverseSource:
    name = "openverse"
    available = True

    def __init__(self, get: HttpGet = http_get):
        self.get = get

    def search(self, query: str, orientation: str = "landscape", n: int = 10) -> list[Candidate]:
        q = urllib.parse.urlencode({"q": query, "license": "cc0,pdm", "page_size": n,
                                    "aspect_ratio": "wide" if orientation == "landscape" else "tall"})
        data = http_get_json(f"https://api.openverse.org/v1/images/?{q}", None, self.get)
        return [Candidate(r["url"], r.get("width") or 0, r.get("height") or 0, self.name,
                          r["license"].upper(), r.get("creator"), r.get("foreign_landing_url"))
                for r in data.get("results", [])]


def download(c: Candidate, get: HttpGet = http_get) -> bytes:
    if c.use_ping:
        get(c.use_ping, c.headers)
    return get(c.url, None)
