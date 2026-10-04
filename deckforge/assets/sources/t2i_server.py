"""Reference text-to-image service for on-prem GPU nodes.

Requires a CUDA GPU, torch and diffusers. Not exercised in CI. The default model is
FLUX.1 [schnell] (Apache 2.0). Set DECKFORGE_T2I_MODEL to swap in another permissively
licensed model that diffusers can load with the same pipeline interface.

Run:  python -m deckforge.assets.sources.t2i_server --port 8601
API:  POST / {"prompt", "negative_prompt", "width", "height", "seed"} -> {"image_base64", "model"}
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

MODEL_ID = os.environ.get("DECKFORGE_T2I_MODEL", "black-forest-labs/FLUX.1-schnell")


def load_pipeline():
    import torch
    from diffusers import FluxPipeline

    pipe = FluxPipeline.from_pretrained(MODEL_ID, torch_dtype=torch.bfloat16)
    pipe.enable_model_cpu_offload()
    return pipe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8601)
    args = ap.parse_args()
    import torch

    pipe = load_pipeline()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            # schnell is guidance-distilled: no negative prompt, guidance 0, about 4 steps
            image = pipe(body["prompt"], width=body.get("width", 1344), height=body.get("height", 768),
                         guidance_scale=0.0, num_inference_steps=4, max_sequence_length=256,
                         generator=torch.Generator("cpu").manual_seed(body.get("seed", 0))).images[0]
            buf = io.BytesIO()
            image.save(buf, "PNG")
            out = json.dumps({"image_base64": base64.b64encode(buf.getvalue()).decode(), "model": MODEL_ID})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(out.encode())

    HTTPServer(("0.0.0.0", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
