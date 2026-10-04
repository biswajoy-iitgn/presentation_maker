#!/usr/bin/env python3
"""Verify every SlideAudit JSON/CSV record and image in the pinned release."""
from __future__ import annotations
import csv, hashlib, json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"research_datasets"/"slideaudit"/"full_release"/"data"
OUT=ROOT/"dataset_acquisition"/"manifests"/"slideaudit_validation.json"

def main():
    results={"dataset":"SlideAudit","validated_at_utc":datetime.now(timezone.utc).isoformat(timespec="seconds"),"revision":"642d490b7c1d2e78a50a631bfd359433397f3ecf","metadata_rows":0,"annotations_json":0,"descriptions_json":0,"images_verified":0,"unique_image_sha256":0,"duplicate_image_paths":0,"failures":[]}
    for kind in ("annotations","descriptions"):
        paths=sorted((DATA/kind).glob("*.json"))
        for p in paths:
            try:
                with p.open(encoding="utf-8") as f:json.load(f)
            except Exception as e:results["failures"].append({"path":str(p.relative_to(ROOT)),"reason":str(e)})
        results[f"{kind}_json"]=len(paths)
    image_hashes=defaultdict(list)
    for p in sorted((DATA/"images").glob("*.png")):
        try:
            with Image.open(p) as im:im.verify()
            h=hashlib.sha256()
            with p.open("rb") as f:
                for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
            image_hashes[h.hexdigest()].append(p)
        except Exception as e:results["failures"].append({"path":str(p.relative_to(ROOT)),"reason":str(e)})
    results["images_verified"]=sum(map(len,image_hashes.values()))
    results["unique_image_sha256"]=len(image_hashes)
    results["duplicate_image_paths"]=results["images_verified"]-results["unique_image_sha256"]
    with (DATA/"metadata.csv").open(newline="",encoding="utf-8") as f:results["metadata_rows"]=sum(1 for _ in csv.DictReader(f))
    expected={"metadata_rows":2400,"annotations_json":2400,"descriptions_json":2400,"images_verified":2400}
    for key,value in expected.items():
        if results[key]!=value:results["failures"].append({"path":str(DATA.relative_to(ROOT)),"reason":f"{key}={results[key]}, expected {value}"})
    results["validation_status"]="validated" if not results["failures"] else "validation_failed"
    OUT.write_text(json.dumps(results,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(results,indent=2,ensure_ascii=False))
    if results["failures"]:raise SystemExit(1)

if __name__=="__main__":main()
