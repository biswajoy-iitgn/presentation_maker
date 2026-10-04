"""Asset contracts: what a slide needs, and the provenance record of what it got."""

from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import BaseModel, Field

AssetKind = Literal["background", "photo", "illustration", "icon", "flag", "map", "logo"]
Role = Literal["cover", "divider", "band", "panel", "backdrop", "inline"]


class AssetNeed(BaseModel):
    kind: AssetKind
    role: Role = "inline"
    subject: str = ""                      # what the image shows, icon name, ISO code
    style: str = ""                        # procedural style, icon set, mood keywords
    width_px: int = 1920
    height_px: int = 1080
    text_zone: tuple[float, float, float, float] | None = None   # fractions of the frame where text sits
    seed: int = 0


class AssetRecord(BaseModel):
    need: AssetNeed
    source: str                            # e.g. procedural:light_arcs, lucide, flag-icons, pexels, t2i:flux1-schnell
    licence: str
    attribution: str | None = None
    url: str | None = None
    ai_generated: bool = False
    fallback_from: list[str] = Field(default_factory=list)   # sources tried before this one
    sha256: str
    qa: dict = Field(default_factory=dict)

    @staticmethod
    def digest(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()
