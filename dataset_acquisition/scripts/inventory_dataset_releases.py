#!/usr/bin/env python3
"""Record concise public API inventories; does not download dataset payloads."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research_datasets" / "dataset_releases.json"
HF = [
    "Yqy6/Slides-Align", "NTT-hil-insight/SlideVQA", "Wenkaiwang/PPTBench-V3",
    "tyrionhuu/PPTBench-Detection", "tyrionhuu/PPTBench-Understanding",
    "tyrionhuu/PPTBench-Modification", "tyrionhuu/PPTBench-Generation",
]
GH = ["para-lost/AutoPresent", "zhuohaouw/SlideAudit", "nttmdlab-nlp/SlideVQA", "Gastronomicluna/PPTBench-Eval"]
s = requests.Session()
s.headers.update({"User-Agent": "local-corpus-release-inventory/1.0"})

def main():
    result = {"captured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "huggingface": [], "github": []}
    last_hf = 0.0
    for repo in HF:
        elapsed = time.monotonic() - last_hf
        if last_hf and elapsed < 2:
            time.sleep(2 - elapsed)
        u = "https://huggingface.co/api/datasets/" + repo
        r = s.get(u, timeout=90)
        last_hf = time.monotonic()
        rec = {"repo": repo, "url": "https://huggingface.co/datasets/" + repo, "http_status": r.status_code}
        if r.ok:
            j = r.json()
            c = j.get("cardData") or {}
            info = c.get("dataset_info") or {}
            rec.update({"revision": j.get("sha"), "used_storage_bytes": j.get("usedStorage"),
                        "file_count_reported": len(j.get("siblings") or []), "gated": j.get("gated"),
                        "license_name": c.get("license_name") or c.get("license"),
                        "license_url": c.get("license_url"), "task_categories": c.get("task_categories"),
                        "language": c.get("language"), "size_categories": c.get("size_categories"),
                        "dataset_configs": info.get("configs"), "dataset_splits": info.get("splits"),
                        "download_size_bytes": info.get("download_size"), "dataset_size_bytes": info.get("dataset_size"),
                        "tags": [x for x in j.get("tags", []) if x.startswith(("license:", "size_categories:"))]})
            # Do not save gated terms or full dataset cards in this compact record.
        result["huggingface"].append(rec)
    last_gh = 0.0
    for repo in GH:
        elapsed = time.monotonic() - last_gh
        if last_gh and elapsed < 2:
            time.sleep(2 - elapsed)
        r = s.get("https://api.github.com/repos/" + repo, timeout=90)
        last_gh = time.monotonic()
        rec = {"repo": repo, "url": "https://github.com/" + repo, "http_status": r.status_code}
        if r.ok:
            j = r.json(); branch = j.get("default_branch", "main")
            rec.update({"revision_branch": branch, "license_spdx": (j.get("license") or {}).get("spdx_id"),
                        "updated_at": j.get("updated_at")})
            cr = s.get(f"https://api.github.com/repos/{repo}/commits/{branch}", timeout=90)
            if cr.ok:
                rec["revision"] = (cr.json().get("sha") or "")
            elapsed = time.monotonic() - last_gh
            if elapsed < 2:
                time.sleep(2 - elapsed)
            tr = s.get(f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1", timeout=90)
            last_gh = time.monotonic()
            if tr.ok:
                tree = tr.json().get("tree", [])
                sizes = {}
                for entry in tree:
                    if entry.get("type") != "blob":
                        continue
                    path = entry.get("path", "")
                    head = path.split("/", 1)[0]
                    sizes[head] = sizes.get(head, 0) + int(entry.get("size", 0) or 0)
                rec.update({"file_count": sum(1 for x in tree if x.get("type") == "blob"),
                            "tree_size_bytes": sum(sizes.values()), "top_level_size_bytes": sizes})
        result["github"].append(rec)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for item in result["huggingface"]:
        print("HF", item["repo"], item.get("http_status"), item.get("revision"), item.get("used_storage_bytes"), "gated", item.get("gated"))
    for item in result["github"]:
        print("GH", item["repo"], item.get("http_status"), item.get("revision"), item.get("file_count"), item.get("tree_size_bytes"))

if __name__ == "__main__":
    main()
