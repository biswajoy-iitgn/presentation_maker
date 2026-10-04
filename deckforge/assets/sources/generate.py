"""Local text-to-image generation through a small HTTP service (see t2i_server.py).

The planner fills an ImageBrief. Composition constraints become prompt language plus a
negative-space instruction, so generated images leave room where text will sit.
"""

from __future__ import annotations

import base64
import io
import json
import os
import urllib.request
from dataclasses import dataclass, field
from typing import Callable

from PIL import Image

NEGATIVE = ("text, letters, watermark, logo, signature, people faces, flags, low quality, "
            "blurry, distorted, oversaturated, clutter")

STYLE_PROMPTS = {
    "architectural": "minimal architectural interior, soft daylight, clean planes, large negative space",
    "motion": "long exposure light trails at night, motion blur, cinematic, deep shadows",
    "industry": "editorial industrial photography, natural light, shallow depth of field",
    "abstract": "abstract light, smooth gradients, subtle glow, premium corporate aesthetic",
    "aerial": "aerial photograph, geometric patterns, muted tones, high detail",
}


@dataclass
class ImageBrief:
    subject: str
    style: str = "abstract"
    mood: str = "calm, confident"
    negative_space: str = "left"              # left | right | top | bottom | none
    palette_words: list[str] = field(default_factory=lambda: ["deep navy", "electric blue"])

    def prompt(self) -> tuple[str, str]:
        space = "" if self.negative_space == "none" else f", empty uncluttered area on the {self.negative_space} side"
        p = (f"{self.subject}, {STYLE_PROMPTS.get(self.style, self.style)}, {self.mood} mood, "
             f"colour palette of {', '.join(self.palette_words)}{space}, 16:9 composition")
        return p, NEGATIVE


HttpPost = Callable[[str, dict], dict]


def _post_json(url: str, payload: dict, timeout: int = 300) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


class TextToImageClient:
    def __init__(self, endpoint: str | None = None, post: HttpPost = _post_json):
        self.endpoint = endpoint or os.environ.get("DECKFORGE_T2I_URL")
        self.post = post

    @property
    def available(self) -> bool:
        return bool(self.endpoint)

    def generate(self, brief: ImageBrief, width: int = 1344, height: int = 768, seed: int = 0
                 ) -> tuple[Image.Image, dict]:
        prompt, negative = brief.prompt()
        resp = self.post(self.endpoint, {"prompt": prompt, "negative_prompt": negative,
                                         "width": width, "height": height, "seed": seed})
        img = Image.open(io.BytesIO(base64.b64decode(resp["image_base64"]))).convert("RGB")
        meta = {"model": resp.get("model", "unknown"), "prompt": prompt, "seed": seed}
        return img, meta
