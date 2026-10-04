#!/usr/bin/env python3
"""Capture small, public dataset documentation and selected annotations.

This script never reads or accepts gated dataset terms and never executes
repository code. Selected sample assets are streamed with strict size limits.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "research_datasets"
MAX_FILE = 20 * 1024 * 1024
session = requests.Session()
session.headers.update({"User-Agent": "local-corpus-metadata-review/1.0"})
last_host = {}

FILES = {
    "slideaudit": [
        ("README.md", "https://raw.githubusercontent.com/zhuohaouw/SlideAudit/main/README.md"),
        ("LICENSE", "https://raw.githubusercontent.com/zhuohaouw/SlideAudit/main/LICENSE"),
        ("metadata.csv", "https://raw.githubusercontent.com/zhuohaouw/SlideAudit/main/data/metadata.csv"),
        ("sample/annotations/slide_0001.json", "https://raw.githubusercontent.com/zhuohaouw/SlideAudit/main/data/annotations/slide_0001.json"),
        ("sample/annotations/slide_0002.json", "https://raw.githubusercontent.com/zhuohaouw/SlideAudit/main/data/annotations/slide_0002.json"),
        ("sample/annotations/slide_0003.json", "https://raw.githubusercontent.com/zhuohaouw/SlideAudit/main/data/annotations/slide_0003.json"),
        ("sample/descriptions/slide_0001.json", "https://raw.githubusercontent.com/zhuohaouw/SlideAudit/main/data/descriptions/slide_0001.json"),
        ("sample/descriptions/slide_0002.json", "https://raw.githubusercontent.com/zhuohaouw/SlideAudit/main/data/descriptions/slide_0002.json"),
        ("sample/descriptions/slide_0003.json", "https://raw.githubusercontent.com/zhuohaouw/SlideAudit/main/data/descriptions/slide_0003.json"),
        ("sample/alteration_example_1.jpg", "https://raw.githubusercontent.com/zhuohaouw/SlideAudit/main/examples/alteration_example_1.jpg"),
        ("sample/alteration_example_2.jpg", "https://raw.githubusercontent.com/zhuohaouw/SlideAudit/main/examples/alteration_example_2.jpg"),
        ("sample/alteration_example_3.jpg", "https://raw.githubusercontent.com/zhuohaouw/SlideAudit/main/examples/alteration_example_3.jpg"),
    ],
    "slidesbench": [
        ("README.md", "https://raw.githubusercontent.com/para-lost/AutoPresent/main/README.md"),
        ("LICENSE", "https://raw.githubusercontent.com/para-lost/AutoPresent/main/LICENSE"),
        ("slidesbench_README.md", "https://raw.githubusercontent.com/para-lost/AutoPresent/main/slidesbench/README.md"),
    ],
    "pptbench": [
        ("PPTBench-Eval_README.md", "https://raw.githubusercontent.com/Gastronomicluna/PPTBench-Eval/main/README.md"),
        ("PPTBench-Eval_LICENSE", "https://raw.githubusercontent.com/Gastronomicluna/PPTBench-Eval/main/LICENSE"),
    ],
}

def fetch(repo, rel, url):
    host = urlparse(url).netloc
    pause = 2.0 - (time.monotonic() - last_host.get(host, -999))
    if pause > 0:
        time.sleep(pause)
    response = session.get(url, stream=True, timeout=(20, 90))
    last_host[host] = time.monotonic()
    response.raise_for_status()
    length = int(response.headers.get("Content-Length") or 0)
    if length > MAX_FILE:
        raise RuntimeError(f"metadata/sample exceeds per-file cap: {url} ({length})")
    target = DATA / repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".part")
    size = 0
    with tmp.open("wb") as out:
        for block in response.iter_content(1024 * 1024):
            if block:
                size += len(block)
                if size > MAX_FILE:
                    raise RuntimeError(f"stream exceeds per-file cap: {url}")
                out.write(block)
    tmp.replace(target)
    return {"path": str(target.relative_to(ROOT)), "url": url, "size_bytes": size,
            "accessed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}

def main():
    inventory = {"captured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "scope": "public documentation, metadata, and representative SlideAudit samples; no gated assets or code execution", "files": []}
    for repo, rows in FILES.items():
        for rel, url in rows:
            try:
                inventory["files"].append({"dataset": repo, **fetch(repo, rel, url), "status": "downloaded"})
            except Exception as exc:
                inventory["files"].append({"dataset": repo, "url": url, "status": "failed", "reason": str(exc)})
    dest = DATA / "dataset_metadata.json"
    dest.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
