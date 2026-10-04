#!/usr/bin/env python3
"""Download the four optional public reference reports after deck acquisition."""
from __future__ import annotations
import csv, hashlib, re, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import fitz, requests

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/"reference_reports"/"files"
OUT=ROOT/"dataset_acquisition"/"manifests"/"reference_reports.csv"
LOG=ROOT/"dataset_acquisition"/"logs"/"acquisition.log"
REPORTS=[
 ("R01","Bain","The Working Future","https://www.bain.com/contentassets/d620202718c146359acb05c02d9060db/bain-report_the-working-future.pdf"),
 ("R02","PwC","Wealth Management Insights 2025","https://www.pwc.ch/en/publications/2025/wealth-management-insights-2025.pdf"),
 ("R03","PwC","Global Business Services Study 2025","https://www.pwc.co.uk/services/document/global-business-services-study-2025.pdf"),
 ("R04","KPMG","2025 Futures Report","https://kpmg.com/kpmg-us/content/dam/kpmg/pdf/2025/kpmg-2025-report.pdf"),
]
FIELDS=["file_id","source_id","title","firm","source_page_url","requested_url","final_url","accessed_at_utc","local_path","format","mime_type","size_bytes","sha256","page_count","validation_status","document_type","rights_status","rights_evidence"]
def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def slug(s): return re.sub(r"[^a-z0-9]+","_",s.lower()).strip("_")
def main():
 s=requests.Session();s.headers["User-Agent"]="Mozilla/5.0 (compatible; local-corpus-acquisition/1.0)"
 rows=[];last={}
 if OUT.exists():
  with OUT.open(newline="",encoding="utf-8") as f: rows=list(csv.DictReader(f))
 existing={r.get("source_id") for r in rows}
 for sid,firm,title,url in REPORTS:
  if sid in existing: continue
  host=urlparse(url).netloc;pause=2-(time.monotonic()-last.get(host,-999))
  if pause>0:time.sleep(pause)
  folder=DEST/slug(firm);folder.mkdir(parents=True,exist_ok=True)
  final=folder/(slug(title)+".pdf");part=final.with_suffix(".pdf.part")
  if final.exists():raise FileExistsError(f"refusing to overwrite {final}")
  try:
   with s.get(url,stream=True,timeout=(30,120),allow_redirects=True) as r:
    last[host]=time.monotonic()
    if r.status_code in (401,403,429):raise PermissionError(f"HTTP {r.status_code}")
    r.raise_for_status();length=int(r.headers.get("Content-Length") or 0)
    if length>500*1024**2:raise RuntimeError(f"report too large: {length}")
    size=0;h=hashlib.sha256()
    with part.open("wb") as f:
     for c in r.iter_content(1024*1024):
      if not c:continue
      size+=len(c)
      if size>500*1024**2:raise RuntimeError("stream exceeded per-report cap")
      h.update(c);f.write(c)
    final_url=r.url;mime=r.headers.get("Content-Type","").split(";")[0]
   raw=part.read_bytes()
   if not raw.startswith(b"%PDF-"):raise ValueError("not a PDF")
   d=fitz.open(stream=raw,filetype="pdf")
   if d.is_encrypted:raise ValueError("encrypted PDF")
   pages=d.page_count;d.close();part.replace(final)
   rows.append({"file_id":sid+"-"+h.hexdigest()[:12],"source_id":sid,"title":title,"firm":firm,
    "source_page_url":url,"requested_url":url,"final_url":final_url,"accessed_at_utc":now(),
    "local_path":str(final.relative_to(ROOT)),"format":"PDF","mime_type":mime or "application/pdf",
    "size_bytes":size,"sha256":h.hexdigest(),"page_count":pages,"validation_status":"validated",
    "document_type":"reference_report","rights_status":"unknown","rights_evidence":"publicly accessible PDF; no reuse licence verified"})
   LOG.parent.mkdir(parents=True,exist_ok=True)
   with LOG.open("a",encoding="utf-8") as f:f.write(f"{now()} report {sid} {size} bytes {pages} pages sha256={h.hexdigest()}\n")
  except Exception:
   part.unlink(missing_ok=True);raise
  tmp=OUT.with_suffix(".csv.part")
  with tmp.open("w",newline="",encoding="utf-8") as f:
   w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
  tmp.replace(OUT)
if __name__=="__main__":main()
