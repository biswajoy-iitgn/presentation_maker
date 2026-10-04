#!/usr/bin/env python3
"""Acquire the CC BY 4.0 SlideAudit release from a pinned GitHub commit.

Downloads one repository archive, inspects every member before extraction,
rejects links/traversal/special files, enforces byte budgets, then verifies the
2400 image/annotation/description inventory. No code is executed.
"""
from __future__ import annotations
import csv, hashlib, json, tarfile, time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
import requests

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"research_datasets"/"slideaudit"/"full_release"
TMP=ROOT/"dataset_acquisition"/"tmp"/"slideaudit_repo.tar.gz.part"
META=ROOT/"research_datasets"/"dataset_releases.json"
REPO="zhuohaouw/SlideAudit"
REV="642d490b7c1d2e78a50a631bfd359433397f3ecf"
TREE_SIZE=1_245_717_017
EXTRACT_LIMIT=1_400_000_000
ARCHIVE_LIMIT=1_400_000_000
TOTAL_CAP=10*1024**3

def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def new_data_bytes():
    pdf=ROOT/"dataset_acquisition"/"manifests"/"files.csv"
    pdfn=0
    if pdf.exists():
        with pdf.open(newline="",encoding="utf-8") as f: pdfn=sum(int(r.get("size_bytes") or 0) for r in csv.DictReader(f))
    research=sum(p.stat().st_size for p in (ROOT/"research_datasets").rglob("*") if p.is_file())
    reports=ROOT/"dataset_acquisition"/"manifests"/"reference_reports.csv"
    if reports.exists():
        with reports.open(newline="",encoding="utf-8") as f: pdfn+=sum(int(r.get("size_bytes") or 0) for r in csv.DictReader(f))
    return pdfn+research

def main():
    if OUT.exists() and any(OUT.iterdir()): raise FileExistsError(f"refusing to overwrite non-empty {OUT}")
    used=new_data_bytes()
    if used+ARCHIVE_LIMIT+EXTRACT_LIMIT>TOTAL_CAP: raise RuntimeError(f"10 GiB cap: current {used}, reserve {ARCHIVE_LIMIT+EXTRACT_LIMIT}")
    TMP.parent.mkdir(parents=True,exist_ok=True)
    url=f"https://api.github.com/repos/{REPO}/tarball/{REV}"
    time.sleep(2)
    s=requests.Session();s.headers["User-Agent"]="local-corpus-acquisition/1.0"
    # Reuse a complete archive left by an interrupted extraction. Otherwise
    # resume an interrupted download when the server confirms a byte range.
    complete=False
    if TMP.exists():
        try:
            with tarfile.open(TMP,"r:gz") as tar: tar.getmembers()
            complete=True
        except (tarfile.TarError,EOFError,OSError): pass
    h=hashlib.sha256();size=TMP.stat().st_size if complete else 0
    if complete:
        with TMP.open("rb") as f:
            for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
        final_url=url
    else:
        if TMP.exists():
            with TMP.open("rb") as f:
                for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
        headers={"Range":f"bytes={size}-"} if size else {}
        with s.get(url,headers=headers,stream=True,timeout=(30,180),allow_redirects=True) as r:
            if r.status_code in (401,403,429): raise PermissionError(f"GitHub access restriction HTTP {r.status_code}")
            r.raise_for_status()
            if size:
                content_range=r.headers.get("Content-Range","")
                if r.status_code==206 and content_range.startswith(f"bytes {size}-"): mode="ab"
                else: h=hashlib.sha256();size=0;mode="wb"
            else:mode="wb"
            declared=int(r.headers.get("Content-Length") or 0)
            if size+declared>ARCHIVE_LIMIT: raise RuntimeError(f"archive declared {size+declared} > cap {ARCHIVE_LIMIT}")
            final_url=r.url
            with TMP.open(mode) as f:
                for b in r.iter_content(1024*1024):
                    if not b: continue
                    size+=len(b)
                    if size>ARCHIVE_LIMIT or new_data_bytes()+size+EXTRACT_LIMIT>TOTAL_CAP:
                        raise RuntimeError("archive stream exceeded its byte budget")
                    h.update(b);f.write(b)
    members=[];expanded=0;rootprefix=None
    with tarfile.open(TMP,"r:gz") as tar:
        for m in tar.getmembers():
            path=PurePosixPath(m.name)
            if path.is_absolute() or any(part in ("..","") for part in path.parts): raise ValueError(f"unsafe path in archive: {m.name}")
            if not (m.isdir() or m.isfile()): raise ValueError(f"link or special file rejected: {m.name}")
            if len(path.parts)==1: continue
            if rootprefix is None: rootprefix=path.parts[0]
            if path.parts[0]!=rootprefix: raise ValueError("archive contains multiple top-level roots")
            rel=Path(*path.parts[1:])
            if not str(rel) or rel.is_absolute() or ".." in rel.parts: continue
            expanded += m.size if m.isfile() else 0
            if expanded>EXTRACT_LIMIT: raise RuntimeError("archive expanded beyond 1.4 GB limit")
            members.append((m,rel))
    if not members: raise ValueError("empty repository archive")
    OUT.mkdir(parents=True,exist_ok=True)
    with tarfile.open(TMP,"r:gz") as tar:
        for m,rel in members:
            target=OUT/rel
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists(): raise FileExistsError(f"refusing to overwrite extracted file {target}")
            if m.isfile():
                src=tar.extractfile(m)
                if src is None: raise IOError(f"could not read {m.name}")
                with src as source,target.open("xb") as f:
                    while True:
                        b=source.read(1024*1024)
                        if not b: break
                        f.write(b)
    if not (OUT/"data"/"metadata.csv").exists(): raise ValueError("expected SlideAudit metadata file missing")
    with (OUT/"data"/"metadata.csv").open(newline="",encoding="utf-8") as f: rows=list(csv.DictReader(f))
    counts={k:sum(1 for p in (OUT/"data"/k).glob("*")) for k in ("images","annotations","descriptions")}
    if len(rows)!=2400 or counts!={"images":2400,"annotations":2400,"descriptions":2400}:
        raise ValueError(f"content-count mismatch: metadata={len(rows)}, assets={counts}")
    TMP.unlink()
    record={"dataset":"SlideAudit","repo":REPO,"revision":REV,"archive_download_url":url,"archive_final_url":final_url,
      "archive_sha256":h.hexdigest(),"archive_size_bytes":size,"expanded_bytes":expanded,"extracted_path":str(OUT.relative_to(ROOT)),
      "metadata_rows":len(rows),"images":counts["images"],"annotations":counts["annotations"],"descriptions":counts["descriptions"],
      "license":"CC BY 4.0","rights_evidence":"Repository README and LICENSE explicitly state CC BY 4.0 for the dataset",
      "validation_status":"validated","accessed_at_utc":now()}
    p=ROOT/"dataset_acquisition"/"manifests"/"slideaudit_release.json"
    p.write_text(json.dumps(record,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    with (ROOT/"dataset_acquisition"/"logs"/"acquisition.log").open("a",encoding="utf-8") as f:
        f.write(f"{now()} SlideAudit release extracted {expanded} bytes; archive {size} bytes; 2400 images/annotations/descriptions; sha256={h.hexdigest()}\n")
    print(json.dumps(record,indent=2))

if __name__=="__main__":main()
