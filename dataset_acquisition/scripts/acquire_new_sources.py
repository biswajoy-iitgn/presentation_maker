#!/usr/bin/env python3
"""Resume-safe acquisition for the expanded presentation and dataset brief.

Only direct presentation candidates are downloaded here. The permission-gated
McKinsey PDF and gated research datasets remain metadata-only. Network requests
are sequential, capped, hashed, and validated before a local file is retained.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
import fitz

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "consulting_corpus"
NEWROOT = ROOT / "dataset_acquisition"
MANIFESTS = NEWROOT / "manifests"
LOG = NEWROOT / "logs" / "acquisition.log"
MAX_NEW_BYTES = 10 * 1024**3
MAX_SINGLE_FILE = 500 * 1024**2

PDF_CANDIDATES = [
    ("B01", "McKinsey", "Emerging Generative AI Use Cases in Credit", "https://iacpm.org/wp-content/uploads/2025/03/IACPM-McKinsey-Gen-AI-Webinar-2025.pdf", "permission_required", "PDF states internal use only and use without specific permission of McKinsey is strictly prohibited.", "https://iacpm.org/"),
    ("B02", "Bain", "Bain presentation hosted by IABC Chicago", "https://www.chicago.iabc.com/wp-content/uploads/2019/10/Bain-Presentation-Deck.pdf", "unknown", "Public file hosted by IABC Chicago; no reuse licence verified.", "https://www.chicago.iabc.com/"),
    ("B03", "Bain", "Board of the Future", "https://www.bain.com/contentassets/88ae8242ec8a4b38847e2eaba562ad38/231110-board-of-the-future-_final.pdf", "unknown", "Official Bain host; no reuse licence verified.", "https://www.bain.com/"),
    ("B04", "Deloitte", "Unlocking GBS Potential: The Transformative Power of AI", "https://deloitte.co.uk/sharedservicesconference/assets/pdf/deloitte-uk-ssc2025-presentation-deloitte-ai.pdf", "unknown", "Deloitte conference PDF; no reuse licence verified.", "https://www.deloitte.co.uk/sharedservicesconference/highlights/"),
    ("B05", "Deloitte", "Beyond the Headlines from Deloitte's Economists", "https://deloitte.co.uk/sharedservicesconference/assets/pdf/deloitte-uk-ssc2025-presentation-deloitte-economics.pdf", "unknown", "Deloitte conference PDF; no reuse licence verified.", "https://www.deloitte.co.uk/sharedservicesconference/highlights/"),
    ("B06", "Deloitte", "Finance 2025 Revisited", "https://nor.deloitte.com/rs/712-CNF-326/images/Crunchtime-finance-2025-revisited-presentation_Norway.pdf", "unknown", "Deloitte-hosted presentation PDF; 2025 appears in title/horizon, publication date not inferred.", "https://nor.deloitte.com/"),
    ("B07", "Deloitte", "Deloitte–NEMA National Risk Study 2025", "https://nemaweb.org/wp-content/uploads/2025/11/National-Risk-Study-Presentation.pdf", "unknown", "NEMA-hosted presentation; attribution/year to verify in PDF.", "https://nemaweb.org/"),
    ("B08", "PwC", "PwC treasury presentation", "https://cdn.prod.website-files.com/67bca1bf8744a6a2d7811b35/68265e64645741f70d1da9c8_PwC%20Presentation.pdf", "unknown", "Public PDF; title and date to verify in PDF.", "https://cdn.prod.website-files.com/"),
    ("C05-30JUN", "KPMG", "Are you ready for 30 June 2025 reporting?", "https://assets.kpmg.com/content/dam/kpmgsites/au/pdf/2025/30-june-2025-reporting-webinar-presentation-slides.pdf.coredownload.inline.pdf", "unknown", "KPMG marks the PDF Document Classification: KPMG Public; all rights reserved.", "https://kpmg.com/au/en/insights/financial-reporting/accounting-reporting-webinars/30-june-2025-financial-reporting-guidance.html"),
    ("C05-31DEC", "KPMG", "Are you ready for 31 December 2025 reporting?", "https://assets.kpmg.com/content/dam/kpmgsites/au/pdf/2025/31-december-2025-reporting-webinar-presentation-slides.pdf.coredownload.inline.pdf", "unknown", "KPMG marks the PDF Document Classification: KPMG Public; all rights reserved.", "https://kpmg.com/au/en/insights/financial-reporting/accounting-reporting-webinars/financial-reporting-31-december-webinar.html"),
    ("C05-AVIATION", "KPMG", "Global Aviation Conference Final Presentation", "https://kpmg.com/content/dam/kpmgsites/xx/pdf/2025/09/global-aviation-conference-final-presentation.pdf.coredownload.inline.pdf", "unknown", "Linked from the official KPMG conference page; use rights not separately stated.", "https://kpmg.com/xx/en/what-we-do/industries/infrastructure/global-aviation-conference.html"),
    ("C04-PFIZER", "Pfizer", "The Pfizer Hub Formula: Transactional to Transformational", "https://www.deloitte.co.uk/sharedservicesconference/assets/pdf/deloitte-uk-ssc2025-presentation-pfizer.pdf", "unknown", "Publicly linked by Deloitte conference highlights; speaker is Pfizer; reuse rights not verified.", "https://www.deloitte.co.uk/sharedservicesconference/highlights/"),
    ("C04-HSE", "HSE", "A New Era for Irish Healthcare: HSE Shared Services", "https://www.deloitte.co.uk/sharedservicesconference/assets/pdf/deloitte-uk-ssc2025-presentation-hse.pdf", "unknown", "Publicly linked by Deloitte conference highlights; speaker is HSE; reuse rights not verified.", "https://www.deloitte.co.uk/sharedservicesconference/highlights/"),
    ("C04-META", "Meta", "Pioneering AI-Driven Finance at Meta", "https://www.deloitte.co.uk/sharedservicesconference/assets/pdf/deloitte-uk-ssc2025-presentation-meta.pdf", "unknown", "Publicly linked by Deloitte conference highlights; speaker is Meta; reuse rights not verified.", "https://www.deloitte.co.uk/sharedservicesconference/highlights/"),
    ("C04-BAKKAVOR", "Bakkavor", "Bakkavor conference presentation", "https://www.deloitte.co.uk/sharedservicesconference/assets/pdf/deloitte-uk-ssc2025-presentation-bakkavor.pdf", "unknown", "Publicly linked by Deloitte conference highlights; speaker is Bakkavor; reuse rights not verified.", "https://www.deloitte.co.uk/sharedservicesconference/highlights/"),
    ("C07-BCG", "BCG", "BCG Executive Perspectives: Guide to Cost and Growth", "https://www.bcg.com/assets/2025/executive-perspectives-guide-to-cost-and-growth-15jan.pdf", "unknown", "Official BCG presentation PDF; copyright 2025, all rights reserved; no reuse licence verified.", "https://www.bcg.com/assets/2025/executive-perspectives-guide-to-cost-and-growth-15jan.pdf"),
]

SOURCE_FIELDS = "source_id name category seed_url official_url revision accessed_at_utc advertised_count discovered_count pagination_complete estimated_size_bytes downloaded_size_bytes status license_name license_url rights_evidence missing_components".split()
ENTRY_FIELDS = "entry_id source_id title firm listed_url resolved_url file_id status reason".split()
FILE_FIELDS = "file_id source_id title firm attribution_evidence publication_year year_evidence language document_type source_page_url requested_url final_url accessed_at_utc local_path format mime_type size_bytes sha256 page_or_slide_count editable_original validation_status dataset_split dataset_configuration rights_status license_name license_url rights_evidence".split()
DUP_FIELDS = "duplicate_entry_id canonical_file_id sha256 source_url".split()
FAIL_FIELDS = "source_id entry_id url_or_file status http_status attempts reason next_action".split()
QUALITY_FIELDS = "file_id review_method reviewed_pages classification readability_notes layout_notes quality_status reviewer".split()

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def read_csv(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)

def log(message):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{now()} {message}\n")

def slug(s):
    s = unquote(s)
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return (s[:100] or "document")

def existing_sha_map():
    out = {}
    for row in read_csv(CORPUS / "manifests" / "downloads.csv"):
        if row.get("sha256") and row.get("local_path"):
            out[row["sha256"]] = {"local_path": row["local_path"], "file_id": row.get("download_id", "")}
    for row in read_csv(MANIFESTS / "candidate_files.csv"):
        if row.get("sha256") and row.get("local_path"):
            out[row["sha256"]] = {"local_path": row["local_path"], "file_id": row.get("file_id", "")}
    for p in (CORPUS / "files").rglob("*"):
        if p.is_file() and p.suffix.lower() in {".pdf", ".pptx", ".ppt"}:
            h = hashlib.sha256()
            with p.open("rb") as f:
                for block in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(block)
            out.setdefault(h.hexdigest(), {"local_path": str(p.relative_to(CORPUS)), "file_id": ""})
    return out

def disk_used_new():
    total = 0
    for p in (CORPUS / "files").rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total

def download_pdfs():
    # Keep resumable source-level acquisition records separate from the
    # crosswalk manifests generated by build_master_manifests.py.
    sources = read_csv(MANIFESTS / "candidate_sources.csv")
    entries = read_csv(MANIFESTS / "candidate_entries.csv")
    files = read_csv(MANIFESTS / "candidate_files.csv")
    duplicates = read_csv(MANIFESTS / "candidate_duplicates.csv")
    failures = read_csv(MANIFESTS / "candidate_failures.csv")
    source_ids = {r.get("source_id") for r in sources}
    entry_ids = {r.get("entry_id") for r in entries}
    file_ids = {r.get("file_id") for r in files}
    fail_ids = {(r.get("source_id"), r.get("url_or_file")) for r in failures}
    known_hashes = existing_sha_map()
    new_bytes = sum(int(r.get("size_bytes") or 0) for r in files if r.get("local_path"))
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; consulting-corpus-acquisition/1.0)"})
    host_last = {}
    for sid, firm, title, url, rights, rights_evidence, source_page_url in PDF_CANDIDATES:
        source_status = "permission_required" if rights == "permission_required" else "unresolved"
        source_row = {"source_id": sid, "name": title, "category": "presentation_pdf", "seed_url": source_page_url,
                      "official_url": url, "accessed_at_utc": now(), "status": source_status,
                      "rights_status": rights, "rights_evidence": rights_evidence}
        if sid not in source_ids:
            sources.append(source_row); source_ids.add(sid)
        eid = sid + "-01"
        prior_entry = next((r for r in entries if r.get("entry_id") == eid), None)
        if prior_entry and prior_entry.get("file_id") and prior_entry.get("status") in {"downloaded", "duplicate"}:
            continue
        if eid not in entry_ids:
            entries.append({"entry_id": eid, "source_id": sid, "title": title, "firm": firm,
                            "listed_url": url, "resolved_url": url,
                            "status": "permission_required" if rights == "permission_required" else "unresolved",
                            "reason": rights_evidence if rights == "permission_required" else ""})
            entry_ids.add(eid)
        if rights == "permission_required":
            continue
        part = CORPUS / "files" / slug(firm) / (slug(sid + " " + title) + ".pdf.part")
        final = part.with_suffix("")
        host = urlparse(url).netloc
        wait = 2.0 - (time.monotonic() - host_last.get(host, -999))
        if wait > 0:
            time.sleep(wait)
        attempts = 0
        try:
            for attempt in range(1, 4):
                attempts = attempt
                try:
                    with session.get(url, stream=True, timeout=(20, 90), allow_redirects=True) as response:
                        host_last[host] = time.monotonic()
                        if response.status_code in (401, 403, 429):
                            failures.append({"source_id": sid, "entry_id": eid, "url_or_file": url,
                                             "status": "access_restricted", "http_status": response.status_code,
                                             "attempts": attempt, "reason": "server access/rate restriction; retries stopped",
                                             "next_action": "use only an openly published alternate"})
                            entries = [dict(r, status="access_restricted", reason=f"http_{response.status_code}") if r.get("entry_id")==eid else r for r in entries]
                            source_row["status"] = "access_restricted"
                            break
                        if response.status_code == 404:
                            failures.append({"source_id": sid, "entry_id": eid, "url_or_file": url,
                                             "status": "dead_link", "http_status": 404, "attempts": attempt,
                                             "reason": "http_404", "next_action": "search exact title on official publisher"})
                            entries = [dict(r, status="dead_link", reason="http_404") if r.get("entry_id")==eid else r for r in entries]
                            source_row["status"] = "dead_link"
                            break
                        response.raise_for_status()
                        length = int(response.headers.get("Content-Length") or 0)
                        if length > MAX_SINGLE_FILE or new_bytes + length > MAX_NEW_BYTES:
                            raise RuntimeError(f"size cap: declared {length}; already retained {new_bytes}")
                        part.parent.mkdir(parents=True, exist_ok=True)
                        received = 0
                        with part.open("wb") as out:
                            for chunk in response.iter_content(1024 * 1024):
                                if not chunk:
                                    continue
                                received += len(chunk)
                                if received > MAX_SINGLE_FILE or new_bytes + received > MAX_NEW_BYTES:
                                    raise RuntimeError("stream exceeded size cap")
                                out.write(chunk)
                    raw = part.read_bytes()
                    if not raw.startswith(b"%PDF-"):
                        raise ValueError("response is not a PDF signature")
                    doc = fitz.open(stream=raw, filetype="pdf")
                    pages = doc.page_count
                    if doc.is_encrypted:
                        raise ValueError("encrypted PDF")
                    text = " ".join((doc.load_page(i).get_text() or "") for i in range(min(2, pages)))
                    doc.close()
                    sha = hashlib.sha256(raw).hexdigest()
                    if sha in known_hashes:
                        part.unlink(missing_ok=True)
                        canonical_id = known_hashes[sha].get("file_id", "")
                        canonical_path = known_hashes[sha]["local_path"]
                        duplicates.append({"duplicate_entry_id": eid, "canonical_file_id": canonical_id,
                                           "sha256": sha, "source_url": response.url})
                        entries = [dict(r, file_id=canonical_id, status="duplicate", reason=f"sha256 exact match: {canonical_path}") if r.get("entry_id")==eid else r for r in entries]
                        source_row["status"] = "duplicate"
                        break
                    if final.exists():
                        raise FileExistsError(f"verified target exists: {final}")
                    part.replace(final)
                    fid = sid + "-" + sha[:12]
                    # Extract the first plausible title line for attribution evidence without replacing source title.
                    local = str(final.relative_to(ROOT))
                    files.append({"file_id": fid, "source_id": sid, "title": title, "firm": firm,
                                  "attribution_evidence": rights_evidence, "publication_year": "",
                                  "year_evidence": "not established; title horizons are not treated as publication dates",
                                  "language": "unknown", "document_type": "presentation", "source_page_url": source_page_url,
                                  "requested_url": url, "final_url": response.url, "accessed_at_utc": now(),
                                  "local_path": local, "format": "PDF", "mime_type": "application/pdf",
                                  "size_bytes": len(raw), "sha256": sha, "page_or_slide_count": pages,
                                  "editable_original": "no", "validation_status": "validated",
                                  "rights_status": rights, "rights_evidence": rights_evidence})
                    file_ids.add(fid); known_hashes[sha] = {"local_path": local, "file_id": fid}; new_bytes += len(raw)
                    entries = [dict(r, file_id=fid, status="downloaded") if r.get("entry_id")==eid else r for r in entries]
                    source_row.update({"status": "downloaded", "downloaded_size_bytes": len(raw), "discovered_count": 1})
                    log(f"downloaded {sid} {len(raw)} bytes {pages} pages sha256={sha}")
                    break
                except (requests.RequestException, TimeoutError) as exc:
                    if attempt == 3:
                        raise
                    time.sleep(min(2 ** (attempt - 1), 8))
            sources = [source_row if r.get("source_id")==sid else r for r in sources]
        except Exception as exc:
            part.unlink(missing_ok=True)
            if (sid, url) not in fail_ids:
                failures.append({"source_id": sid, "entry_id": eid, "url_or_file": url,
                                 "status": "validation_failed" if isinstance(exc, (ValueError, fitz.FileDataError)) else "unresolved",
                                 "attempts": attempts, "reason": str(exc), "next_action": "review response; retry only if transient"})
            entries = [dict(r, status="validation_failed", reason=str(exc)) if r.get("entry_id")==eid else r for r in entries]
            source_row["status"] = "validation_failed" if isinstance(exc, (ValueError, fitz.FileDataError)) else "unresolved"
            sources = [source_row if r.get("source_id")==sid else r for r in sources]
            log(f"failed {sid}: {exc}")
    write_csv(MANIFESTS / "candidate_sources.csv", SOURCE_FIELDS, sources)
    write_csv(MANIFESTS / "candidate_entries.csv", ENTRY_FIELDS, entries)
    write_csv(MANIFESTS / "candidate_files.csv", FILE_FIELDS, files)
    write_csv(MANIFESTS / "candidate_duplicates.csv", DUP_FIELDS, duplicates)
    write_csv(MANIFESTS / "candidate_failures.csv", FAIL_FIELDS, failures)
    if not (MANIFESTS / "quality_review.csv").exists():
        write_csv(MANIFESTS / "quality_review.csv", QUALITY_FIELDS, [])

if __name__ == "__main__":
    download_pdfs()
