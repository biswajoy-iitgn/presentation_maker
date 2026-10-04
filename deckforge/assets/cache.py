"""HTTP fetching with a content cache. Sources take the getter as a parameter so tests can inject one."""

from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from pathlib import Path
from typing import Callable

CACHE_DIR = Path(os.environ.get("DECKFORGE_CACHE", Path.home() / ".cache" / "deckforge"))
USER_AGENT = "DeckForge/0.1 (+asset resolver)"

HttpGet = Callable[[str, dict | None], bytes]


def http_get(url: str, headers: dict | None = None, timeout: int = 30) -> bytes:
    key = hashlib.sha256((url + json.dumps(headers or {}, sort_keys=True)).encode()).hexdigest()
    path = CACHE_DIR / "http" / key[:2] / key
    if path.exists():
        return path.read_bytes()
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def http_get_json(url: str, headers: dict | None = None, get: HttpGet = http_get):
    return json.loads(get(url, headers))
