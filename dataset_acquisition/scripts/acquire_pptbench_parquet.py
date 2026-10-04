#!/usr/bin/env python3
"""Fetch documented PPTBench Parquet shards, with stream cap and local checks."""
from __future__ import annotations

import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pyarrow.parquet as pq
import requests

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "research_datasets" / "pptbench" / "raw_parquet"
MANIFEST = ROOT / "dataset_acquisition" / "manifests" / "pptbench_parquet.csv"
LOG = ROOT / "dataset_acquisition" / "logs" / "acquisition.log"
NEW_DATA_CAP = 10 * 1024**3
EXPECTED = {
    "detection": ("D05-DET", "tyrionhuu/PPTBench-Detection"),
    "understanding": ("D05-UND", "tyrionhuu/PPTBench-Understanding"),
    "modification": ("D05-MOD", "tyrionhuu/PPTBench-Modification"),
    "generation": ("D05-GEN", "tyrionhuu/PPTBench-Generation"),
}
FIELDS = ["asset_id", "source_id", "repo_id", "revision", "split", "subset", "requested_url", "final_url", "local_path", "size_bytes", "sha256", "rows", "columns", "format", "validation_status", "rights_status", "rights_evidence", "accessed_at_utc"]

def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")

def main():
    s = requests.Session(); s.headers.update({"User-Agent": "local-corpus-dataset-acquisition/1.0"})
    manifest = []
    if MANIFEST.exists():
        with MANIFEST.open(newline="", encoding="utf-8") as f: manifest = list(csv.DictReader(f))
    known_urls = {r.get("requested_url") for r in manifest}
    new_pdf_rows = []
    files_manifest = ROOT / "dataset_acquisition" / "manifests" / "files.csv"
    if files_manifest.exists():
        with files_manifest.open(newline="", encoding="utf-8") as f: new_pdf_rows = list(csv.DictReader(f))
    pdf_bytes = sum(int(r.get("size_bytes") or 0) for r in new_pdf_rows if r.get("local_path"))
    research_bytes = sum(p.stat().st_size for p in (ROOT / "research_datasets").rglob("*") if p.is_file())
    budget_used = pdf_bytes + research_bytes
    release_data = json.loads((ROOT / "research_datasets" / "dataset_releases.json").read_text(encoding="utf-8"))
    revisions = {r["repo"]: r.get("revision", "") for r in release_data.get("huggingface", [])}
    last_host = {}
    for slug, (source_id, repo) in EXPECTED.items():
        p = ROOT / "research_datasets" / "pptbench" / f"{slug}_parquet_sources.json"
        specs = json.loads(p.read_text(encoding="utf-8"))
        for spec in specs:
            url = spec["url"]; expected_size = int(spec["size"])
            if url in known_urls: continue
            if budget_used + expected_size > NEW_DATA_CAP:
                raise RuntimeError(f"10 GiB acquisition cap would be exceeded by {url}")
            host = urlparse(url).netloc
            wait = 2 - (time.monotonic() - last_host.get(host, -999))
            if wait > 0: time.sleep(wait)
            target = DATA / slug / f"train_{url.rsplit('/',1)[-1].split('.')[0]}.parquet"
            if target.exists(): raise FileExistsError(f"refusing to overwrite {target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            part = target.with_suffix(target.suffix + ".part")
            try:
                with s.get(url, stream=True, timeout=(30,180), allow_redirects=True) as r:
                    last_host[host] = time.monotonic()
                    if r.status_code in (401,403,429): raise PermissionError(f"access restriction HTTP {r.status_code}")
                    r.raise_for_status()
                    declared = int(r.headers.get("Content-Length") or 0)
                    if declared and declared != expected_size: raise RuntimeError(f"declared size {declared} differs from API {expected_size}")
                    h=hashlib.sha256(); size=0
                    with part.open("wb") as out:
                        for chunk in r.iter_content(1024*1024):
                            if not chunk: continue
                            size += len(chunk)
                            if size > expected_size or budget_used + size > NEW_DATA_CAP:
                                raise RuntimeError("Parquet stream exceeded its declared size or 10 GiB cap")
                            h.update(chunk); out.write(chunk)
                    final_url=r.url
                if size != expected_size: raise RuntimeError(f"received {size} bytes, API declared {expected_size}")
                with part.open("rb") as f:
                    if f.read(4) != b"PAR1": raise ValueError("invalid Parquet header")
                    f.seek(-4,2)
                    if f.read(4) != b"PAR1": raise ValueError("invalid Parquet footer")
                pf=pq.ParquetFile(part)
                rows=pf.metadata.num_rows; columns=pf.metadata.num_columns
                part.replace(target)
                rights = "explicit_license" if slug == "understanding" else "unknown"
                evidence = "HF dataset card declares Apache-2.0; underlying slide rights remain separately unverified" if slug == "understanding" else "No explicit dataset license identified in the HF card; underlying slide rights unknown"
                manifest.append({"asset_id":f"{source_id}-{len(manifest)+1:04d}","source_id":source_id,"repo_id":repo,
                                 "revision":revisions.get(repo, ""),"split":spec.get("split"),
                                 "subset":spec.get("subset"),"requested_url":url,"final_url":final_url,
                                 "local_path":str(target.relative_to(ROOT)),"size_bytes":size,"sha256":h.hexdigest(),
                                 "rows":rows,"columns":columns,"format":"Parquet","validation_status":"validated",
                                 "rights_status":rights,"rights_evidence":evidence,"accessed_at_utc":now()})
                budget_used += size; known_urls.add(url)
                with LOG.open("a",encoding="utf-8") as f: f.write(f"{now()} downloaded {source_id} {target.name} {size} bytes {rows} rows sha256={h.hexdigest()}\n")
            except Exception:
                part.unlink(missing_ok=True)
                raise
            tmp=MANIFEST.with_suffix(".csv.part"); tmp.parent.mkdir(parents=True,exist_ok=True)
            with tmp.open("w",newline="",encoding="utf-8") as f:
                w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(manifest)
            tmp.replace(MANIFEST)

if __name__ == "__main__": main()
