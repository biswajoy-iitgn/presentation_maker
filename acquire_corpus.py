#!/usr/bin/env python3
"""Resumable public consulting-presentation corpus acquisition.

Network policy: one request at a time per host, >=2s between requests,
robots.txt enforced, descriptive UA, max three retries, 5 GiB total.
"""
from __future__ import annotations
import argparse, csv, hashlib, html, io, json, logging, os, re, shutil, sys, time, zipfile, threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.robotparser import RobotFileParser

try:
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("BeautifulSoup4 is required; use the environment package if available.")
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

ROOT = Path(__file__).resolve().parent / "consulting_corpus"
SEEDS = [
  ("slideworks_750", "https://slideworks.io/resources/750-real-consulting-presentations-from-mckinsey-deloitte-ey-and-more", "750+"),
  ("analyst_academy", "https://www.theanalystacademy.com/consulting-presentations/", "600+"),
  ("slidescience_consulting", "https://slidescience.co/consulting-presentations/", "500+; individual entries listed; bulk archive form-gated"),
  ("slideworks_mckinsey", "https://slideworks.io/resources/47-real-mckinsey-presentations", "160+"),
  ("ampler_bcg", "https://ampler.io/articles/bcg-slide-decks/", "60+"),
 ("slidescience_mckinsey", "https://slidescience.co/mckinsey-presentations/", "200+; bulk archive form-gated"),
 ("slideworks_bcg", "https://slideworks.io/resources/54-real-bcg-presentations", "105+; linked from the 750+ catalog"),
 ("slideworks_bain", "https://slideworks.io/resources/30-real-bain-presentations", "55+; linked from the 750+ catalog"),
  ("ampler_bain", "https://ampler.io/articles/40-free-bain-powerpoint-slide-decks/", "40+"),
  ("ampler_mckinsey", "https://ampler.io/articles/50-free-mckinsey-powerpoint-slide-decks/", "50+"),
  ("makeslides_oliver_wyman", "https://makeslides.com/blog/4-oliver-wyman-presentations-ready-to-download-for-free", "4"),
]
UA = "ConsultingCorpusResearch/1.0 (public-resource acquisition; contact: corpus-local)"
MAX_BYTES = 5 * 1024**3
INTERVAL = 2.0
DOC_EXTS = (".pdf", ".ppt", ".pptx")
EXCLUDE = re.compile(r"template|course|subscribe|newsletter|contact|pricing|sign.?in|download presentation collection|slide.?start|learn to design|image:|logo|cookie|privacy|terms|founder|about us|read more|sponsor", re.I)
FIRM_RE = re.compile(r"McKinsey|Bain|BCG|Boston Consulting|Deloitte|EY|Ernst & Young|KPMG|PwC|Pricewaterhouse|Strategy&|Accenture|Oliver Wyman|Kearney|A\.T\. Kearney|L\.E\.K|LEK|Roland Berger|Booz Allen|Alvarez & Marsal", re.I)

def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def slug(s):
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").lower()
    return s[:100] or "unknown"
def normalize_firm(s):
    if not s: return ""
    key=re.sub(r"[^a-z0-9]+","",s.lower())
    for aliases,canonical in [
        (("ey","ernstyoung"),"EY"), (("bostonconsulting","bcg"),"BCG"),
        (("atkearney","kearney"),"Kearney"), (("lek","leconsulting"),"L.E.K."),
        (("mckinsey","mckinseycompany"),"McKinsey"), (("bain","bainco"),"Bain"),
        (("deloitte",),"Deloitte"), (("kpmg",),"KPMG"), (("pwc","pricewaterhouse"),"PwC"),
        (("strategy",),"Strategy&"), (("accenture",),"Accenture"),
        (("oliverwyman",),"Oliver Wyman"), (("rolandberger",),"Roland Berger"),
    ]:
        if any(key==alias or key.startswith(alias) for alias in aliases): return canonical
    return s
def csv_write(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    tmp.replace(path)
def csv_read(path):
    if not path.exists(): return []
    with path.open(newline="", encoding="utf-8") as f: return list(csv.DictReader(f))

class Client:
    def __init__(self, log): self.last=defaultdict(float); self.robots={}; self.log=log; self.opener=build_opener(); self.blocked=set(); self.http403=defaultdict(int); self.host_locks=defaultdict(threading.RLock); self.robots_lock=threading.Lock()
    def robots_ok(self, url):
        p=urlparse(url); host=f"{p.scheme}://{p.netloc}"
        with self.robots_lock:
          if host not in self.robots:
            ru=host+"/robots.txt"
            try:
                text=self.get_bytes(ru, 128_000, check_robots=False)[0].decode("utf-8","replace")
                rp=RobotFileParser(); rp.set_url(ru); rp.parse(text.splitlines()); self.robots[host]=rp
            except Exception as e:
                self.robots[host]=False; self.log.warning("robots unavailable %s: %s",host,e)
        rp=self.robots[host]
        return bool(rp and rp.can_fetch(UA,url))
    def get_bytes(self, url, cap=8*1024*1024, check_robots=True):
        if check_robots and not self.robots_ok(url): raise PermissionError("robots.txt disallows URL or could not be verified")
        host=urlparse(url).netloc
        with self.host_locks[host]:
            if host in self.blocked: raise PermissionError("host stopped after HTTP 403/429 blocking")
            delay=INTERVAL-(time.monotonic()-self.last[host])
            if delay>0: time.sleep(delay)
            req=Request(url,headers={"User-Agent":UA,"Accept":"application/pdf,application/vnd.openxmlformats-officedocument.presentationml.presentation,application/vnd.ms-powerpoint,text/html;q=0.9,*/*;q=0.5"})
            last=None
            for attempt in range(3):
                try:
                    with self.opener.open(req,timeout=25) as r:
                        self.last[host]=time.monotonic(); chunks=[]; size=0; deadline=time.monotonic()+60
                        while True:
                            if time.monotonic()>deadline: raise TimeoutError("response exceeded 60-second transfer window")
                            chunk=r.read(min(256*1024,cap+1-size))
                            if not chunk: break
                            chunks.append(chunk); size+=len(chunk)
                            if size>cap: raise ValueError(f"response exceeds {cap} bytes")
                        data=b"".join(chunks)
                        return data, r.headers, r.geturl(), r.status
                except HTTPError as e:
                    self.last[host]=time.monotonic(); last=e
                    if e.code==403:
                        self.http403[host]+=1; self.blocked.add(host); self.log.warning("Stopping requests to %s after HTTP 403",host); raise
                    if e.code==429:
                        retry=e.headers.get("Retry-After","")
                        try: wait=max(float(retry),2**attempt)
                        except ValueError: wait=max(2**attempt,2.0)
                        self.log.warning("HTTP 429 from %s; honoring backoff %.1fs",host,wait)
                        if attempt<2: time.sleep(min(wait,300))
                        else: self.blocked.add(host)
                        continue
                    if e.code not in (408,425,500,502,503,504): raise
                    if attempt<2: time.sleep(2**attempt)
                except (URLError, TimeoutError, OSError) as e:
                    self.last[host]=time.monotonic(); last=e
                    if attempt<2: time.sleep(2**attempt)
            raise last

def page_links(soup, base):
    areas=soup.select("main, article, .entry-content, .post-content")
    if not areas: areas=[soup.body or soup]
    seen=set()
    for area in areas:
      for a in area.select("a[href]"):
        title=" ".join(a.get_text(" ",strip=True).split())
        url=urljoin(base,a.get("href",""))
        if not title or url in seen or url.startswith("mailto:") or url.startswith("javascript:"): continue
        src_host=urlparse(base).netloc.lower().removeprefix("www.")
        dst_host=urlparse(url).netloc.lower().removeprefix("www.")
        # Same-site navigation, product pages, and related article links are not
        # presentation entries; linked catalogs are tracked as collections.
        if src_host==dst_host and not re.search(r"\.(pdf|pptx?)(?:$|\?)",url,re.I): continue
        seen.add(url)
        if a.find("img") and len(title)<8: continue
        if EXCLUDE.search(title): continue
        # Collection articles are curated lists. Keep substantive linked deck titles,
        # including third-party landing pages, while dropping navigation/hash links.
        if len(title)<12 and not re.search(r"\.(pdf|pptx?)(?:$|\?)",url,re.I): continue
        if not a.find_parent("li") and not re.search(r"\.(pdf|pptx?)(?:$|\?)",url,re.I): continue
        if urlparse(url).netloc==urlparse(base).netloc and urlparse(url).path.rstrip("/")==urlparse(base).path.rstrip("/"): continue
        yield title,url

def extension(url, content_type=""):
    path=urlparse(url).path.lower()
    for ext,fmt in ((".pdf","PDF"),(".pptx","PPTX"),(".ppt","PPT")):
        if path.endswith(ext): return fmt
    c=content_type.lower()
    if "pdf" in c: return "PDF"
    if "presentationml" in c: return "PPTX"
    if "ms-powerpoint" in c: return "PPT"
    return ""

def find_doc(client, start):
    current=start; visited=set()
    for hop in range(4):
        if current in visited: return None,"redirect_or_link_loop"
        visited.add(current)
        try: data,headers,final,status=client.get_bytes(current,cap=32*1024*1024)
        except HTTPError as e: return None,f"http_{e.code}"
        except PermissionError: return None,"robots_disallowed"
        except Exception as e: return None,f"fetch_error:{type(e).__name__}:{e}"
        fmt=extension(final,headers.get("Content-Type",""))
        if fmt: return (data,headers,final,fmt),None
        ct=headers.get("Content-Type","").lower()
        if "html" not in ct and not data.lstrip().startswith((b"<!doctype html",b"<html")): return None,"unsupported_format"
        soup=BeautifulSoup(data,"html.parser")
        candidates=[]
        for a in soup.select("a[href]"):
            target=urljoin(final,a["href"]); label=" ".join(a.get_text(" ",strip=True).split())
            if extension(target) or (label and re.search(r"download|pdf|powerpoint|presentation",label,re.I)):
                if extension(target): candidates.append(target)
        # Embed/frame links may be direct public document URLs.
        for tag in soup.select("iframe[src], embed[src], object[data]"):
            target=urljoin(final,tag.get("src") or tag.get("data") or "")
            if extension(target): candidates.append(target)
        if not candidates: return None,"no_public_document_link_within_three_hops"
        current=candidates[0]
    return None,"hop_limit"

def validate(data, fmt):
    if fmt=="PDF":
        if not data.startswith(b"%PDF-"): return False,"signature_mismatch",None
        if PdfReader is None: return False,"unsupported_validation:pypdf_missing",None
        try:
            r=PdfReader(io.BytesIO(data),strict=False)
            if r.is_encrypted: return False,"encrypted",None
            n=len(r.pages)
            if n<1: return False,"corrupt_or_empty_pdf",None
            return True,"validated",n
        except Exception as e: return False,"corrupt_pdf:"+str(e)[:180],None
    if fmt=="PPTX":
        try:
            z=zipfile.ZipFile(io.BytesIO(data)); names=set(z.namelist())
            if "ppt/presentation.xml" not in names or "[Content_Types].xml" not in names: return False,"invalid_ooxml_presentation",None
            slides=sum(1 for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml",n))
            return (slides>0,"validated" if slides else "no_slides",slides or None)
        except Exception as e: return False,"corrupt_pptx:"+str(e)[:180],None
    if fmt=="PPT": return False,"unsupported_validation_legacy_ppt",None
    return False,"unsupported_format",None

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--inventory-only",action="store_true"); ap.add_argument("--refresh-inventory",action="store_true"); args=ap.parse_args()
    for sub in ("files","manifests","logs"): (ROOT/sub).mkdir(parents=True,exist_ok=True)
    log=logging.getLogger("corpus"); log.setLevel(logging.INFO)
    fh=logging.FileHandler(ROOT/"logs"/"acquisition.log",encoding="utf-8"); fh.setFormatter(logging.Formatter("%(asctime)sZ %(levelname)s %(message)s")); log.addHandler(fh)
    client=Client(log); cpath=ROOT/"manifests"/"collections.csv"; epath=ROOT/"manifests"/"entries.csv"
    dpath=ROOT/"manifests"/"downloads.csv"; dupath=ROOT/"manifests"/"duplicates.csv"; fpath=ROOT/"manifests"/"failures.csv"
    prior_entries=[e for e in csv_read(epath) if not EXCLUDE.search(e.get("title",""))]
    entries=[] if args.refresh_inventory else list(prior_entries)
    downloads=csv_read(dpath); collections=csv_read(cpath); failures=csv_read(fpath); duplicates=csv_read(dupath)
    kept_ids={e["entry_id"] for e in entries}
    if not args.refresh_inventory:
        failures=[f for f in failures if not f.get("entry_id") or f["entry_id"] in kept_ids]
        duplicates=[d for d in duplicates if d.get("duplicate_entry_id") in kept_ids]
    for cid,url,_ in SEEDS:
        if cid.startswith("slidescience_") and not any(f.get("status")=="approval_required" and f.get("url")==url for f in failures):
            failures.append({"entry_id":"","url":url,"status":"approval_required","http_status":"","attempts":0,"reason":"Bulk archive form requests first name and email; no submission made","next_action":"Obtain explicit approval before submitting the form"})
    known={e["entry_id"]:e for e in entries}; prior_by_id={e["entry_id"]:e for e in prior_entries}; colbyid={r["collection_id"]:r for r in collections}
    for cid,url,advertised in SEEDS:
        if cid in colbyid and colbyid[cid].get("pagination_complete")=="true": continue
        log.info("Inspecting collection %s %s",cid,url)
        rec={"collection_id":cid,"collection_url":url,"accessed_at_utc":now(),"advertised_count":advertised,"entries_discovered":0,"pagination_complete":"unknown","access_notes":"HTML page fetched; no pagination controls verified; form-gated bulk archive not submitted where present"}
        try:
            data,headers,final,status=client.get_bytes(url)
            if "html" not in headers.get("Content-Type","").lower(): raise ValueError("seed response not HTML")
            captcha=b"/.well-known/sgcaptcha" in data.lower() or b"sgcaptcha" in data.lower()
            soup=BeautifulSoup(data,"html.parser"); found=[] if captcha else list(page_links(soup,final))
            # Retain explicitly linked child curated lists for further discovery, but not merchandise/course pages.
            rec["entries_discovered"]=len(found); rec["pagination_complete"]="false"
            rec["access_notes"]=("Direct fetch returned a CAPTCHA challenge redirect; no challenge was attempted and no entries were extracted. Discovery incomplete." if captcha else "Page fetched; substantive linked entries parsed from list content. Paginated/lazy hidden entries not proven complete.")
            for title,link in found:
                eid=hashlib.sha1((cid+"\n"+link).encode()).hexdigest()[:16]
                firm=normalize_firm(FIRM_RE.search(title).group(0)) if FIRM_RE.search(title) else ""
                if eid not in known:
                    row=prior_by_id.get(eid,{"entry_id":eid,"collection_id":cid,"title":title,"firm":firm,"listed_url":link,"resolved_url":"","download_id":"","status":"unresolved","reason":"link discovered; document resolution pending"})
                    row.update(collection_id=cid,title=title,firm=firm or row.get("firm",""),listed_url=link)
                    entries.append(row); known[eid]=row
            colbyid[cid]=rec
        except PermissionError as e:
            rec["pagination_complete"]="false"; rec["access_notes"]="robots_disallowed or robots.txt unavailable; no crawl performed"
            log.warning("Collection blocked by robots: %s",url)
        except HTTPError as e:
            rec["pagination_complete"]="false"; rec["access_notes"]=f"HTTP {e.code}; collection not enumerated"
            failures.append({"entry_id":"","url":url,"status":"access_restricted" if e.code==403 else "unresolved","http_status":e.code,"attempts":1,"reason":"collection fetch failed","next_action":"retry manually if permitted"})
        except Exception as e:
            rec["pagination_complete"]="false"; rec["access_notes"]=f"fetch/parse failure: {type(e).__name__}: {e}"
            failures.append({"entry_id":"","url":url,"status":"unresolved","http_status":"","attempts":1,"reason":str(e)[:250],"next_action":"inspect seed page manually"})
        collections=[r for r in collections if r["collection_id"]!=cid]+[rec]
        csv_write(cpath,["collection_id","collection_url","accessed_at_utc","advertised_count","entries_discovered","pagination_complete","access_notes"],collections)
        csv_write(epath,["entry_id","collection_id","title","firm","listed_url","resolved_url","download_id","status","reason"],entries)
        csv_write(fpath,["entry_id","url","status","http_status","attempts","reason","next_action"],failures)
    if args.refresh_inventory:
        for old in prior_entries:
            if old.get("status") in ("downloaded","duplicate") and old["entry_id"] not in known:
                entries.append(old); known[old["entry_id"]]=old
    if args.inventory_only: return
    final_ids={e["entry_id"] for e in entries}
    failures=[f for f in failures if not f.get("entry_id") or f["entry_id"] in final_ids]
    duplicates=[d for d in duplicates if d.get("duplicate_entry_id") in final_ids]
    total_bytes=sum(int(d.get("size_bytes") or 0) for d in downloads)
    sha_to_download={d.get("sha256"):d for d in downloads if d.get("sha256")}
    # Non-document landing pages are fetched once each; repeated host requests respect robots and pacing.
    pending=[]
    for e in entries:
        if e.get("status") in ("downloaded","duplicate","approval_required","access_restricted","robots_disallowed","terms_restricted","dead_link","unsupported_format","validation_failed","excluded_confidential"): continue
        if e.get("status")=="unresolved" and e.get("reason")!="link discovered; document resolution pending": continue
        if "slidescience.co" in e["listed_url"] and re.search(r"download presentation collection",e["title"],re.I):
            e.update(status="approval_required",reason="collection archive requires first name and email; no form submitted"); continue
        pending.append(e)
    def fetch_entry(entry):
        result,err=find_doc(client,entry["listed_url"])
        return entry,result,err
    with ThreadPoolExecutor(max_workers=6) as pool:
      futures=[pool.submit(fetch_entry,e) for e in pending]
      for fut in as_completed(futures):
        e,result,err=fut.result()
        if err:
            status="robots_disallowed" if err=="robots_disallowed" else ("access_restricted" if "http_403" in err or "host stopped" in err else ("dead_link" if "http_404" in err else ("unsupported_format" if err=="unsupported_format" else "unresolved")))
            e.update(status=status,reason=err)
            failures.append({"entry_id":e["entry_id"],"url":e["listed_url"],"status":status,"http_status":err.removeprefix("http_"),"attempts":1,"reason":err,"next_action":"manual review or source-owner access"})
            csv_write(epath,["entry_id","collection_id","title","firm","listed_url","resolved_url","download_id","status","reason"],entries)
            continue
        data,headers,final,fmt=result; e["resolved_url"]=final
        ok,vstatus,count=validate(data,fmt)
        if not ok:
            e.update(status="validation_failed",reason=vstatus); failures.append({"entry_id":e["entry_id"],"url":final,"status":"validation_failed","http_status":"200","attempts":1,"reason":vstatus,"next_action":"exclude from corpus"})
            csv_write(epath,["entry_id","collection_id","title","firm","listed_url","resolved_url","download_id","status","reason"],entries)
            csv_write(fpath,["entry_id","url","status","http_status","attempts","reason","next_action"],failures)
            continue
        sha=hashlib.sha256(data).hexdigest()
        if sha in sha_to_download:
            canonical=sha_to_download[sha]; e.update(download_id=canonical["download_id"],status="duplicate",reason="SHA-256 identical to canonical file")
            duplicates.append({"duplicate_entry_id":e["entry_id"],"canonical_download_id":canonical["download_id"],"sha256":sha,"source_url":final})
            csv_write(epath,["entry_id","collection_id","title","firm","listed_url","resolved_url","download_id","status","reason"],entries)
            csv_write(dupath,["duplicate_entry_id","canonical_download_id","sha256","source_url"],duplicates)
            continue
        if total_bytes+len(data)>MAX_BYTES:
            e.update(status="approval_required",reason="5 GiB disk budget would be exceeded")
            failures.append({"entry_id":e["entry_id"],"url":final,"status":"approval_required","http_status":"200","attempts":1,"reason":"5 GiB default disk budget reached","next_action":"ask before further downloads"}); break
        firm=normalize_firm(e.get("firm") or (FIRM_RE.search(e["title"]).group(0) if FIRM_RE.search(e["title"]) else "unknown_firm"))
        dirname=slug(firm); basename=slug(e["title"]); ext={"PDF":".pdf","PPTX":".pptx","PPT":".ppt"}[fmt]
        dest=ROOT/"files"/dirname/f"{basename}_{sha[:10]}{ext}"
        dest.parent.mkdir(parents=True,exist_ok=True)
        part=dest.with_suffix(dest.suffix+".part")
        if dest.exists():
            if hashlib.sha256(dest.read_bytes()).hexdigest()==sha: pass
            else: dest=dest.with_name(dest.stem+"_"+str(int(time.time()))+dest.suffix)
        else:
            with part.open("wb") as f:
                for i in range(0,len(data),1024*1024): f.write(data[i:i+1024*1024])
            part.replace(dest)
        did="dl_"+sha[:16]; rec={"download_id":did,"title":e["title"],"firm":firm,"firm_attribution_evidence":"collection listing/title" if firm!="unknown_firm" else "not stated in entry title","year":"","source_page_url":e["listed_url"],"requested_url":e["listed_url"],"final_url":final,"accessed_at_utc":now(),"local_path":str(dest.relative_to(ROOT)),"file_format":fmt,"mime_type":headers.get("Content-Type",""),"size_bytes":len(data),"sha256":sha,"page_or_slide_count":count,"validation_status":vstatus,"rights_status":"unknown","license_name":"","license_url":"","rights_evidence":"","permitted_use_notes":"Public access recorded; no redistribution or model-training permission inferred"}
        downloads.append(rec); sha_to_download[sha]=rec; total_bytes+=len(data); e.update(download_id=did,status="downloaded",reason="")
        # Persist after every item, so interruption is resumable.
        csv_write(epath,["entry_id","collection_id","title","firm","listed_url","resolved_url","download_id","status","reason"],entries)
        csv_write(dpath,list(rec.keys()),downloads); csv_write(dupath,["duplicate_entry_id","canonical_download_id","sha256","source_url"],duplicates)
        csv_write(fpath,["entry_id","url","status","http_status","attempts","reason","next_action"],failures)
    csv_write(epath,["entry_id","collection_id","title","firm","listed_url","resolved_url","download_id","status","reason"],entries)
    csv_write(dpath,["download_id","title","firm","firm_attribution_evidence","year","source_page_url","requested_url","final_url","accessed_at_utc","local_path","file_format","mime_type","size_bytes","sha256","page_or_slide_count","validation_status","rights_status","license_name","license_url","rights_evidence","permitted_use_notes"],downloads)
    csv_write(dupath,["duplicate_entry_id","canonical_download_id","sha256","source_url"],duplicates)
    csv_write(fpath,["entry_id","url","status","http_status","attempts","reason","next_action"],failures)
    write_docs(collections,entries,downloads,failures)

def write_docs(collections,entries,downloads,failures):
    with (ROOT/"README.md").open("w",encoding="utf-8") as f:
        f.write("# Consulting presentation corpus\n\n")
        f.write("Publicly linked presentations acquired for design analysis. Public availability does not grant redistribution or training rights; consult `manifests/downloads.csv`.\n\n")
        f.write("## Resume\n\nRun `python3 acquire_corpus.py` from the project directory. The process checks robots.txt, serializes requests per host with a two-second interval, keeps an idempotent SHA-256 manifest, and does not submit gated forms. Review `logs/acquisition.log` and `manifests/` for outcomes.\n")
    formats=defaultdict(int); firms=defaultdict(int)
    for d in downloads: formats[d.get("file_format","unknown")]+=1; firms[d.get("firm","unknown")]+=1
    status=defaultdict(int)
    for e in entries: status[e.get("status","unresolved")]+=1
    unique_failures={(f.get("entry_id",""),f.get("url",""),f.get("status","")) for f in failures}
    observed=sum(int(c.get("entries_discovered") or 0) for c in collections)
    lines=["# Acquisition report", "", f"Generated: {now()}", "", "## Totals", "", f"- Collection pages listed: {len(collections)}", f"- Links observed on accessible collection pages: {observed}", f"- Entry records with outcomes, including two previously acquired links preserved across inventory refresh: {len(entries)}", f"- Unique validated files: {len(downloads)}", f"- Exact duplicate entries: {len([e for e in entries if e.get('status')=='duplicate'])}", f"- Distinct failure records: {len(unique_failures)}", f"- Explicit license evidence: {sum(1 for d in downloads if d.get('rights_status')=='explicit_license')}", f"- Current downloaded bytes: {sum(int(d.get('size_bytes') or 0) for d in downloads)}", "", "Entry outcomes:"]
    lines += [f"- {k}: {v}" for k,v in sorted(status.items())]
    lines += ["", "File formats:"]+[f"- {k}: {v}" for k,v in sorted(formats.items())]
    lines += ["", "Listed firms:"]+[f"- {k}: {v}" for k,v in sorted(firms.items())]
    lines += ["", "## Collection coverage", "", "Collection totals overlap: one document can appear in more than one source list. Advertised counts are publisher claims and are not counts of unique files. Pagination/lazy-loaded discovery is not marked complete unless verified.", ""]
    for c in collections: lines.append(f"- `{c['collection_id']}`: {c.get('entries_discovered','0')} links observed; pagination complete: {c.get('pagination_complete','unknown')}; {c.get('access_notes','')}")
    by_entry=defaultdict(list)
    for e in entries: by_entry[e.get("collection_id","")].append(e)
    lines += ["", "## Outcomes by collection", "", "| Collection | Entries recorded | Validated files referenced | Duplicates | Incomplete |", "|---|---:|---:|---:|---:|"]
    for c in collections:
        group=by_entry[c["collection_id"]]; unique={e.get("download_id") for e in group if e.get("status") in ("downloaded","duplicate") and e.get("download_id")}
        dup=sum(e.get("status")=="duplicate" for e in group); incomplete=sum(e.get("status") not in ("downloaded","duplicate") for e in group)
        lines.append(f"| {c['collection_id']} | {len(group)} | {len(unique)} | {dup} | {incomplete} |")
    fail_by_id={}
    for item in failures:
        if item.get("entry_id"): fail_by_id[item["entry_id"]]=item
    incomplete_entries=[e for e in entries if e.get("status") not in ("downloaded","duplicate")]
    lines += ["", "## Gated downloads", "", "SlideScience describes a 500+ presentation archive delivered through a form requesting first name and email. The form was not submitted. Individual publicly linked entries were processed independently where listed. No account, email, or subscription was used.", "", "## Incomplete work and unresolved entries", "", f"{len(incomplete_entries)} entries remain outside the validated corpus. Each row below gives its outcome and next action. Duplicate retry records are consolidated by entry ID.", "", "| Entry and source URL | Status | Reason | Next action |", "|---|---|---|---|"]
    for e in incomplete_entries:
        f=fail_by_id.get(e["entry_id"],{}); action=f.get("next_action") or "Manually review the public source and document link."
        title=(e.get("title","")+" — "+e.get("listed_url","")).replace("|","/").replace("\n"," ")
        reason=(e.get("reason","") or "").replace("|","/").replace("\n"," ")
        lines.append(f"| {title} | {e.get('status','unresolved')} | {reason} | {action} |")
    lines += ["", "Pagination and discovery remain incomplete wherever `collections.csv` says `false`; gaps include the Analyst Academy local-fetch CAPTCHA response, SlideScience robots restrictions, and advertised counts above links parsed from the other pages.", "", "## Rights", "", "Rights default to `unknown`. No training-ready or redistribution claim is made. Files were retained only when publicly linked and validated; firm attribution/year are left blank when not evidenced.", "", "## Storage", "", "Documents are stored under `files/<firm>/`. Manifests and logs are in their named directories. The default 5 GiB limit is enforced.", ""]
    (ROOT/"acquisition_report.md").write_text("\n".join(lines),encoding="utf-8")

if __name__=="__main__": main()
