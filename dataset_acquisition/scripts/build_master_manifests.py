#!/usr/bin/env python3
"""Crosswalk the legacy corpus and expanded work into unified CSV manifests."""
from __future__ import annotations
import csv,hashlib,json
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/"consulting_corpus"/"manifests"
NEW=ROOT/"dataset_acquisition"/"manifests"
SOURCES=NEW/"sources.csv"; ENTRIES=NEW/"entries.csv"; FILES=NEW/"files.csv"
SF="source_id name category seed_url official_url revision accessed_at_utc advertised_count discovered_count pagination_complete estimated_size_bytes downloaded_size_bytes status license_name license_url rights_evidence missing_components".split()
EF="entry_id source_id title firm listed_url resolved_url file_id status reason".split()
FF="file_id source_id title firm attribution_evidence publication_year year_evidence language document_type source_page_url requested_url final_url accessed_at_utc local_path format mime_type size_bytes sha256 page_or_slide_count editable_original validation_status dataset_split dataset_configuration rights_status license_name license_url rights_evidence".split()
DF="duplicate_entry_id canonical_file_id sha256 source_url".split()
FAF="source_id entry_id url_or_file status http_status attempts reason next_action".split()
QF="file_id review_method reviewed_pages classification readability_notes layout_notes quality_status reviewer".split()
COLLECTION_IDS={
 "slideworks_750":"A01","analyst_academy":"A02","slidescience_consulting":"A03",
 "slideworks_mckinsey":"A04","slidescience_mckinsey":"A05","ampler_bcg":"A06",
 "ampler_bain":"A07","ampler_mckinsey":"A08","makeslides_oliver_wyman":"A09",
 "slidestart":"A10","linkedin":"A11"}
URLS={
 "A01":"https://slideworks.io/resources/750-real-consulting-presentations-from-mckinsey-deloitte-ey-and-more",
 "A02":"https://www.theanalystacademy.com/consulting-presentations/",
 "A03":"https://slidescience.co/consulting-presentations/",
 "A04":"https://slideworks.io/resources/47-real-mckinsey-presentations",
 "A05":"https://slidescience.co/mckinsey-presentations/",
 "A06":"https://ampler.io/articles/bcg-slide-decks/",
 "A07":"https://ampler.io/articles/40-free-bain-powerpoint-slide-decks/",
 "A08":"https://ampler.io/articles/50-free-mckinsey-powerpoint-slide-decks/",
 "A09":"https://makeslides.com/blog/4-oliver-wyman-presentations-ready-to-download-for-free",
 "A10":"https://www.slidestart.com/slides",
 "A11":"https://www.linkedin.com/posts/danieljgalletta_free-consulting-presentations-225-real-activity-7307875954238857216-AXK6"}
NAMES={"A01":"Slideworks consulting collection","A02":"Analyst Academy consulting presentations","A03":"SlideScience consulting presentations","A04":"Slideworks McKinsey collection","A05":"SlideScience McKinsey collection","A06":"Ampler BCG decks","A07":"Ampler Bain decks","A08":"Ampler McKinsey decks","A09":"MakeSlides Oliver Wyman presentations","A10":"SlideStart slides library","A11":"LinkedIn consulting collection post"}
URL_TO_FIRM={"mckinsey":"McKinsey","bain":"Bain","bcg":"BCG","deloitte":"Deloitte","ey":"EY","kpmg":"KPMG","pwc":"PwC","accenture":"Accenture","lek":"L.E.K.","strategy":"Strategy&"}

def rd(path):
 if not path.exists():return []
 with path.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def wr(path,fields,rows):
 tmp=path.with_suffix(path.suffix+".part")
 with tmp.open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(rows)
 tmp.replace(path)
def now():return datetime.now(timezone.utc).isoformat(timespec="seconds")
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def blank(**kw):return kw

def main():
 source_rows=[]; entry_rows=[]; file_rows=[]; duplicate_rows=[]; failure_rows=[]; quality_rows=[]
 prior_quality={r.get("file_id"):r for r in rd(NEW/"quality_review.csv")}
 old_sources=rd(OLD/"collections.csv"); old_entries=rd(OLD/"entries.csv"); old_downloads=rd(OLD/"downloads.csv"); old_dups=rd(OLD/"duplicates.csv"); old_fail=rd(OLD/"failures.csv")
 source_by_id={}
 # Preserve the old acquisition as a crosswalk; its incomplete-pagination history stays explicit.
 for r in old_sources:
  sid=COLLECTION_IDS.get(r["collection_id"],r["collection_id"])
  n=int(r.get("entries_discovered") or 0)
  if sid=="A02":status="access_restricted";missing="Cloudflare challenge; no challenge attempted"
  elif sid in ("A03","A05"):status="robots_disallowed";missing="Collection crawl stopped at robots restriction; SlideScience archive requires first name/email"
  elif sid=="A09":status="robots_disallowed";missing="Robots status unavailable/disallowed; no links enumerated"
  else:status="partial" if n else "unresolved";missing="Pagination or entry extraction incomplete"
  source_by_id[sid]={"source_id":sid,"name":NAMES.get(sid,r["collection_id"]),"category":"consulting_collection","seed_url":r["collection_url"],"official_url":r["collection_url"],"accessed_at_utc":r.get("accessed_at_utc"),"advertised_count":r.get("advertised_count"),"discovered_count":n,"pagination_complete":r.get("pagination_complete"),"status":status,"rights_status":"unknown","rights_evidence":"Collection visibility does not establish downstream reuse rights","missing_components":missing}
 # Sources present in the previous scope but missing collection records.
 source_by_id["A10"]={"source_id":"A10","name":NAMES["A10"],"category":"consulting_collection","seed_url":URLS["A10"],"official_url":URLS["A10"],"accessed_at_utc":now(),"discovered_count":0,"pagination_complete":"false","status":"partial","missing_components":"Existing review found no consulting-deck catalogue links; page appeared to be general slide/navigation material"}
 source_by_id["A11"]={"source_id":"A11","name":NAMES["A11"],"category":"public_discovery_post","seed_url":URLS["A11"],"official_url":URLS["A11"],"accessed_at_utc":now(),"discovered_count":0,"pagination_complete":"false","status":"access_restricted","missing_components":"LinkedIn content not fully accessible; no comment or form submitted"}
 # Crosswalk discovered collection entries.
 for r in old_entries:
  old_id=r.get("collection_id",""); sid=COLLECTION_IDS.get(old_id,old_id)
  entry_rows.append({"entry_id":r.get("entry_id"),"source_id":sid,"title":r.get("title"),"firm":r.get("firm"),"listed_url":r.get("listed_url"),"resolved_url":r.get("resolved_url"),"file_id":r.get("download_id"),"status":r.get("status"),"reason":r.get("reason")})
 # Legacy retained file records.
 old_file_ids=set()
 for r in old_downloads:
  fid=r.get("download_id","");old_file_ids.add(fid)
  ext=(r.get("file_format") or Path(r.get("local_path") or "").suffix).upper()
  rel=r.get("local_path","")
  if rel and not rel.startswith("consulting_corpus/"):rel="consulting_corpus/"+rel
  ext=Path(rel).suffix.upper().lstrip(".") or ext
  entry_source=next((e.get("collection_id") for e in old_entries if e.get("download_id")==fid),"")
  source_id=COLLECTION_IDS.get(entry_source,entry_source or "legacy")
  file_rows.append({"file_id":fid,"source_id":source_id,"title":r.get("title"),"firm":r.get("firm"),"attribution_evidence":r.get("firm_attribution_evidence"),"publication_year":r.get("year"),"year_evidence":"legacy manifest; year not rechecked" if r.get("year") else "not established","language":"unknown","document_type":"legacy_unclassified","source_page_url":r.get("source_page_url"),"requested_url":r.get("requested_url"),"final_url":r.get("final_url"),"accessed_at_utc":r.get("accessed_at_utc"),"local_path":rel,"format":ext,"mime_type":r.get("mime_type"),"size_bytes":r.get("size_bytes"),"sha256":r.get("sha256"),"page_or_slide_count":r.get("page_or_slide_count"),"editable_original":"yes" if ext in ("PPTX","PPT") else "no","validation_status":r.get("validation_status"),"rights_status":r.get("rights_status") or "unknown","license_name":r.get("license_name"),"license_url":r.get("license_url"),"rights_evidence":r.get("rights_evidence") or "legacy manifest: public access only; downstream rights unverified"})
  quality_rows.append({"file_id":fid,"review_method":"legacy_manifest_only","classification":"legacy_unclassified","quality_status":"not_reviewed","reviewer":""})
 # Preserve legacy duplicate references and failed entries.
 for r in old_dups: duplicate_rows.append({"duplicate_entry_id":r.get("duplicate_entry_id"),"canonical_file_id":r.get("canonical_download_id"),"sha256":r.get("sha256"),"source_url":r.get("source_url")})
 for r in old_fail:
  e=next((x for x in old_entries if x.get("entry_id")==r.get("entry_id")),{})
  oldid=e.get("collection_id","")
  failure_rows.append({"source_id":COLLECTION_IDS.get(oldid,oldid),"entry_id":r.get("entry_id"),"url_or_file":r.get("url"),"status":r.get("status"),"http_status":r.get("http_status"),"attempts":r.get("attempts"),"reason":r.get("reason"),"next_action":r.get("next_action")})
 # Include the newly discovered direct presentation candidates and their detailed retrieval records.
 direct_sources=rd(NEW/"candidate_sources.csv"); direct_entries=rd(NEW/"candidate_entries.csv"); direct_files=rd(NEW/"candidate_files.csv"); direct_dups=rd(NEW/"candidate_duplicates.csv"); direct_fail=rd(NEW/"candidate_failures.csv")
 for r in direct_sources: source_by_id[r["source_id"]]=r
 for r in direct_entries: entry_rows.append(r)
 for r in direct_files:
  rel=r.get("local_path","")
  if rel:
   p=ROOT/rel
   if p.exists():
    with p.open("rb") as f: first=f.read(2048)
    text=""
    try:
     import fitz
     d=fitz.open(p);text=d[0].get_text() if len(d) else "";d.close()
    except Exception:pass
    sid=r.get("source_id","");year="";ye="not established"
    if sid in ("C05-30JUN","C05-31DEC"):
     year="2025";ye="Date printed on first page"
    elif sid=="C04-META":year="2025";ye="Copyright and conference year printed in slide text"
    elif sid in ("B05","B07","B08","C05-AVIATION"):year="2025";ye="2025 stated in title/first-page text or official event source"
    elif sid in ("C04-PFIZER","C04-HSE","C04-BAKKAVOR"):year="2025";ye="Official 2025 conference page links this PDF; speaker and title checked in PDF"
    lang="ja" if sid=="B03" else "en"
    file_rows.append({"file_id":r.get("file_id"),"source_id":sid,"title":r.get("title"),"firm":r.get("firm"),"attribution_evidence":r.get("attribution_evidence"),"publication_year":year,"year_evidence":ye,"language":lang,"document_type":"presentation","source_page_url":r.get("source_page_url"),"requested_url":r.get("requested_url"),"final_url":r.get("final_url"),"accessed_at_utc":r.get("accessed_at_utc"),"local_path":rel,"format":r.get("format"),"mime_type":r.get("mime_type"),"size_bytes":r.get("size_bytes"),"sha256":r.get("sha256"),"page_or_slide_count":r.get("page_or_slide_count"),"editable_original":"no","validation_status":r.get("validation_status"),"rights_status":r.get("rights_status") or "unknown","rights_evidence":r.get("rights_evidence")})
    quality_rows.append({"file_id":r.get("file_id"),"review_method":"rendered_preview_pending","classification":"presentation","quality_status":"not_reviewed","reviewer":""})
 for r in direct_dups:
  canon=r.get("canonical_file_id") or ""
  if canon=="existing_or_previous":canon=""
  if not canon:
   canon=next((f.get("file_id") for f in file_rows if f.get("sha256")==r.get("sha256")),"")
  duplicate_rows.append({"duplicate_entry_id":r.get("duplicate_entry_id"),"canonical_file_id":canon,"sha256":r.get("sha256"),"source_url":r.get("source_url")})
 for r in direct_fail:failure_rows.append(r)
 # Source pages and discovery gate outcomes.
 extra_sources=[
  ("C01","EY Slideshare profile","public_profile", "https://www.slideshare.net/ernstandyoung","partial","420-slide profile visible; bulk inventory/download unavailable from page review"),
  ("C02","EY webcast library","firm_webcast_library","https://www.ey.com/en_gl/media/webcasts","approval_required","Public catalogue pages link to webcast sessions; slide attachments are available only after webcast registration"),
  ("C03","EY webcast download guidance","access_guidance","https://www.ey.com/en_us/media/webcasts/faq","approval_required","EY FAQ states PDF attachments require registration to access session pages"),
  ("C04","Deloitte Shared Services Conference 2025 materials","conference_collection","https://www.deloitte.co.uk/sharedservicesconference/highlights/","partial","Six public presentation links processed; repeated Deloitte link overlaps B04/B05; other sessions may exist"),
  ("C05","KPMG exact-title presentation discovery","focused_search","https://kpmg.com/","partial","Three decks downloaded; cybersecurity-summary slides not found in the targeted search"),
  ("C06","McKinsey industry-association presentations","focused_search","https://www.mckinsey.com/","permission_required","Two public decks surfaced and require specific McKinsey permission; the brief-specified IGDS retail GenAI exclusion has no documented permission or verified source URL"),
  ("C07","Additional public firm presentation discovery","focused_search","https://www.bcg.com/publications","partial","18 of 20 allowed focused search queries used; only relevant public deck matches added; no exhaustive coverage claim"),
 ]
 for sid,name,cat,url,status,missing in extra_sources:
  source_by_id[sid]={"source_id":sid,"name":name,"category":cat,"seed_url":url,"official_url":url,"accessed_at_utc":now(),"discovered_count":"6" if sid=="C04" else ("4" if sid=="C05" else "3" if sid=="C06" else "18 focused queries" if sid=="C07" else "0"),"pagination_complete":"false","status":status,"missing_components":missing,"rights_status":"unknown"}
 # Entries for C-group discovery (downloads remain linked to their specific source IDs above).
 for eid,sid,title,firm,url,status,reason,fid in [
  ("C04-ECO","C04","Beyond the Headlines from Deloitte's Economists","Deloitte","https://www.deloitte.co.uk/sharedservicesconference/highlights/","duplicate","Same PDF as B05; exact duplicate retained as source reference","B05-512c85114655"),
  ("C04-AI","C04","Unlocking GBS Potential: The Transformative Power of AI","Deloitte","https://www.deloitte.co.uk/sharedservicesconference/highlights/","duplicate","Same PDF as B04; exact duplicate retained as source reference","B04-bf066a2d4aaa"),
  ("C05-CYBER","C05","2025 KPMG Cybersecurity Survey Summary Slides","KPMG","https://kpmg.com/us/en/media/news/kpmg-cyber-security-survey.html","unresolved","Official page exposes the survey report, not the requested summary slide deck" ,""),
  ("C06-LIMRA","C06","2025 McKinsey LIMRA Insurance 360 industry presentation","McKinsey","https://www.limra.com/globalassets/limra-loma/landing/common-assets/mckinsey-webinars/mckinsey-limra-2025-insurance-360-industry-trends_workfoce-benefits-_11112025.pdf","permission_required","First slide says confidential and use without specific permission of McKinsey is prohibited",""),
  ("C06-NATURE","C06","Taking action on nature webinar slides","McKinsey","https://www.mckinsey.com/~/media/mckinsey/industries/agriculture/how%20we%20help%20clients/natural%20capital%20and%20nature/roundtables/webinar%20taking%20action%20on%20nature%20how%20to%20get%20started/taking-action-on-nature-webinar-slides.pdf","permission_required","First slide says confidential and use without specific permission of McKinsey is prohibited",""),
  ("C06-IGDS","C06","IGDS McKinsey retail generative AI presentation","McKinsey","","permission_required","Brief-specified exclusion; no permission is documented and the exact public source URL was not established",""),
 ]:
  entry_rows.append({"entry_id":eid,"source_id":sid,"title":title,"firm":firm,"listed_url":url,"resolved_url":url,"file_id":fid,"status":status,"reason":reason})
  if status=="duplicate" and fid:
   canonical=next((f for f in file_rows if f.get("file_id")==fid),{})
   duplicate_rows.append({"duplicate_entry_id":eid,"canonical_file_id":fid,"sha256":canonical.get("sha256"),"source_url":canonical.get("requested_url") or url})
 # Refine EY and SlideScience blocked outcomes; log a few source-level failures, not every non-link.
 failure_rows += [
  {"source_id":"A02","url_or_file":URLS["A02"],"status":"access_restricted","attempts":"1","reason":"Cloudflare captcha/challenge presented; not bypassed","next_action":"requires accessible public page"},
  {"source_id":"A03","url_or_file":URLS["A03"],"status":"robots_disallowed","attempts":"1","reason":"robots restrictions; bulk archive also first-name/email-gated","next_action":"permission required for gated archive; otherwise await public entries"},
  {"source_id":"A05","url_or_file":URLS["A05"],"status":"robots_disallowed","attempts":"1","reason":"robots restriction; bulk archive gated","next_action":"permission required for archive"},
  {"source_id":"A11","url_or_file":URLS["A11"],"status":"access_restricted","attempts":"1","reason":"LinkedIn post content not fully accessible","next_action":"public un-gated alternative"},
  {"source_id":"C02","url_or_file":URLS.get("C02","https://www.ey.com/en_gl/media/webcasts"),"status":"approval_required","attempts":"0","reason":"EY slide attachments require a registered webcast session","next_action":"user approval for registration"},
  {"source_id":"D04","url_or_file":"https://huggingface.co/datasets/NTT-hil-insight/SlideVQA","status":"approval_required","attempts":"0","reason":"Hub gated terms require accepting NTT evaluation agreement and sharing contact details; GitHub LICENSE also imposes agreement terms","next_action":"explicit user approval to accept terms and share contact details"},
  {"source_id":"D03","url_or_file":"https://huggingface.co/datasets/Yqy6/Slides-Align","status":"metadata_only","attempts":"0","reason":"Hub reports 57,073,806,859 bytes used storage; exceeds 10 GiB budget","next_action":"none under current budget"},
  {"source_id":"D06","url_or_file":"https://huggingface.co/datasets/Wenkaiwang/PPTBench-V3","status":"metadata_only","attempts":"0","reason":"Hub repository 5,820,620,613 bytes; underlying slide assets have no blanket licence and repo card points to separate creator rights","next_action":"rights review before use beyond local research"},
  {"source_id":"C06","entry_id":"C06-IGDS","url_or_file":"IGDS McKinsey retail generative AI presentation (exact URL not established)","status":"permission_required","attempts":"1","reason":"Brief-specified exclusion; specific permission is not documented; no file acquired","next_action":"document permission and source URL before any acquisition"},
 ]
 # Register research dataset sources from verified release metadata.
 releases=json.loads((ROOT/"research_datasets"/"dataset_releases.json").read_text(encoding="utf-8"))
 hf={r["repo"]:r for r in releases.get("huggingface",[])};gh={r["repo"]:r for r in releases.get("github",[])}
 def hfrow(sid,repo,name,status,missing,rights="unknown",rights_ev=""):
  r=hf.get(repo,{})
  source_by_id[sid]={"source_id":sid,"name":name,"category":"research_dataset","seed_url":r.get("url","https://huggingface.co/datasets/"+repo),"official_url":r.get("url","https://huggingface.co/datasets/"+repo),"revision":r.get("revision"),"accessed_at_utc":releases.get("captured_at_utc"),"estimated_size_bytes":r.get("download_size_bytes") or r.get("used_storage_bytes"),"downloaded_size_bytes":"","status":status,"license_name":r.get("license_name"),"license_url":"https://opensource.org/licenses/MIT" if r.get("license_name")=="mit" else ("https://www.apache.org/licenses/LICENSE-2.0" if r.get("license_name")=="apache-2.0" else ""),"rights_status":rights,"rights_evidence":rights_ev or "Dataset card/README checked; underlying document rights recorded separately","missing_components":missing}
 hfrow("D03","Yqy6/Slides-Align","Slides-Align","metadata_only","57.07 GB full repository not downloaded; Hub card count 1,326 rankings differs from viewer's 756 rows","explicit_license","MIT data license; generated source presentations may remain under originating product terms")
 hfrow("D04","NTT-hil-insight/SlideVQA","SlideVQA Hugging Face dataset","approval_required","Gated agreement and contact sharing; repo reports 10.9 GB download and 36.68 GB unpacked dataset","restricted","NTT Software Evaluation License; accept terms required")
 hfrow("D06","Wenkaiwang/PPTBench-V3","PPTBench-V3","metadata_only","Payload not downloaded; 5.82 GB Hub storage, README describes 7.2 GB dataset_final plus 0.50 GB rendering environment; provenance notes third-party template rights","unknown","Hub card uses license=other and does not grant the underlying template rights")
 for k,sid in [("Detection","D05-DET"),("Understanding","D05-UND"),("Modification","D05-MOD"),("Generation","D05-GEN")]:
  repo="tyrionhuu/PPTBench-"+k;r=hf.get(repo,{})
  p=NEW/"pptbench_parquet.csv";assets=[x for x in rd(p) if x.get("source_id")==sid]
  downloaded=sum(int(x.get("size_bytes") or 0) for x in assets)
  status="complete" if assets else "metadata_only"
  license=r.get("license_name") or "unspecified"
  evidence=("Hub dataset card declares Apache-2.0; underlying slide-material rights not separately established" if license=="apache-2.0" else "No explicit dataset license found on Hub; repository MIT code licence does not cover slide/image content")
  source_by_id[sid]={"source_id":sid,"name":"PPTBench "+k,"category":"research_dataset_task","seed_url":r.get("url"),"official_url":r.get("url"),"revision":r.get("revision"),"accessed_at_utc":releases.get("captured_at_utc"),"estimated_size_bytes":r.get("download_size_bytes"),"downloaded_size_bytes":downloaded,"discovered_count":sum(int(x.get("rows") or 0) for x in assets) or (r.get("dataset_splits") or [{}])[0].get("num_examples"),"pagination_complete":"true" if assets else "false","status":status,"license_name":license,"license_url":"https://www.apache.org/licenses/LICENSE-2.0" if license=="apache-2.0" else "","rights_status":"explicit_license" if license=="apache-2.0" else "unknown","rights_evidence":evidence,"missing_components":"All documented train Parquet shards downloaded" if assets else "All shards listed in HF API; no payload downloaded"}
 # Dataset GitHub docs metadata/source records.
 gmeta=[
  ("D01","AutoPresent / SlidesBench","para-lost/AutoPresent","metadata_only","Training/test collections are linked as SlideShare saved lists; no separate data release resolved; example deck assets not acquired","MIT","MIT applies to repository code, not source SlideShare decks"),
  ("D02","SlideAudit","zhuohaouw/SlideAudit","complete","Full repository snapshot includes 2,400 images, annotations, and descriptions","CC BY 4.0","Repository README and LICENSE state dataset CC BY 4.0"),
  ("D05-EVAL","PPTBench Evaluation code and task suite","Gastronomicluna/PPTBench-Eval","partial","Documentation/license captured; code not installed or executed; separate generation image pack not downloaded","MIT","MIT applies to evaluation code; each dataset keeps its own rights"),
 ]
 for sid,name,repo,status,missing,lic,ev in gmeta:
  r=gh.get(repo,{})
  if sid=="D02":
   f=ROOT/"dataset_acquisition"/"manifests"/"slideaudit_release.json"
   if f.exists():
    rel=json.loads(f.read_text());dl=rel.get("expanded_bytes",0)
   else:dl=0
  else:dl=0
  source_by_id[sid]={"source_id":sid,"name":name,"category":"research_dataset","seed_url":"https://github.com/"+repo,"official_url":"https://github.com/"+repo,"revision":r.get("revision"),"accessed_at_utc":releases.get("captured_at_utc"),"estimated_size_bytes":r.get("tree_size_bytes"),"downloaded_size_bytes":dl,"discovered_count":r.get("file_count"),"status":status,"license_name":lic,"license_url":"https://creativecommons.org/licenses/by/4.0/" if lic=="CC BY 4.0" else ("https://opensource.org/licenses/MIT" if lic=="MIT" else ""),"rights_status":"explicit_license" if lic in ("CC BY 4.0","MIT") else "unknown","rights_evidence":ev,"missing_components":missing}
 # Inventory data from local docs/samples; avoid self-referential inventory JSON.
 path_source={"slides_align":"D03","slideaudit":"D02","slidesbench":"D01","pptbench":"D05-EVAL","pptbench_v3":"D06"}
 for p in sorted((ROOT/"research_datasets").rglob("*")):
  if not p.is_file() or p.name in ("dataset_metadata.json","dataset_releases.json"):continue
  if p.name.endswith(".part"):continue
  rel=str(p.relative_to(ROOT));folder=p.relative_to(ROOT/"research_datasets").parts[0];sid=path_source.get(folder,"D05-EVAL")
  digest=sha(p);fid="META-"+digest[:12]
  existing=next((r for r in file_rows if r.get("sha256")==digest),None)
  if existing:
   if sid=="D02" and "full_release" in p.relative_to(ROOT/"research_datasets"/"slideaudit").parts:
    rel_asset=p.relative_to(ROOT/"research_datasets"/"slideaudit"/"full_release").as_posix()
    eid="D02-DUP-"+hashlib.sha256(rel_asset.encode()).hexdigest()[:16]
    url="https://github.com/zhuohaouw/SlideAudit/blob/642d490b7c1d2e78a50a631bfd359433397f3ecf/"+rel_asset
    duplicate_rows.append({"duplicate_entry_id":eid,"canonical_file_id":existing.get("file_id"),"sha256":digest,"source_url":url})
    entry_rows.append({"entry_id":eid,"source_id":"D02","title":p.name,"listed_url":url,"resolved_url":url,"file_id":existing.get("file_id"),"status":"duplicate","reason":"Exact SHA-256 duplicate within the pinned SlideAudit release; original path remains in the extracted release"})
   continue
  low=p.suffix.lower();fmt={".parquet":"Parquet",".json":"JSON",".csv":"CSV",".jpg":"JPEG",".png":"PNG",".md":"Markdown"}.get(low,low.lstrip(".").upper())
  lic="CC BY 4.0" if sid=="D02" else ("MIT" if sid=="D01" else ("Apache-2.0" if sid=="D05-UND" else "unknown"))
  rights="explicit_license" if lic in ("CC BY 4.0","MIT","Apache-2.0") else "unknown"
  evidence=("SlideAudit data CC BY 4.0" if sid=="D02" else ("AutoPresent code/documentation MIT; contained slide material not covered" if sid=="D01" else ("PPTBench evaluation repository documentation/code only" if sid=="D05-EVAL" else "Dataset/document rights not established")))
  if "/raw_parquet/" in rel:
   pr=next((x for x in rd(NEW/"pptbench_parquet.csv") if x.get("local_path")==rel),{})
   sid=pr.get("source_id",sid);fid=pr.get("asset_id",fid);rights=pr.get("rights_status",rights);evidence=pr.get("rights_evidence",evidence)
  file_rows.append({"file_id":fid,"source_id":sid,"title":p.name,"firm":"","attribution_evidence":"Official dataset repository path","publication_year":"","year_evidence":"","language":"unknown","document_type":"research_dataset_asset" if fmt=="Parquet" else "dataset_metadata_or_sample","source_page_url":source_by_id.get(sid,{}).get("official_url"),"requested_url":"","final_url":"","accessed_at_utc":"","local_path":rel,"format":fmt,"mime_type":"","size_bytes":p.stat().st_size,"sha256":digest,"page_or_slide_count":"","editable_original":"","validation_status":"validated" if fmt in ("JSON","CSV","Parquet","JPEG","PNG") else "metadata_only","dataset_split":"train" if fmt=="Parquet" else "","dataset_configuration":"default" if fmt=="Parquet" else "","rights_status":rights,"license_name":lic,"license_url":"https://creativecommons.org/licenses/by/4.0/" if lic=="CC BY 4.0" else ("https://opensource.org/licenses/MIT" if lic=="MIT" else ("https://www.apache.org/licenses/LICENSE-2.0" if lic=="Apache-2.0" else "")),"rights_evidence":evidence})
 # Add each Parquet data shard as a manifest entry pointing at the row in files.csv.
 for r in rd(NEW/"pptbench_parquet.csv"):
  entry_rows.append({"entry_id":r.get("asset_id"),"source_id":r.get("source_id"),"title":Path(r.get("local_path","")).name,"firm":"","listed_url":r.get("requested_url"),"resolved_url":r.get("final_url"),"file_id":r.get("asset_id"),"status":"downloaded","reason":"Complete train shard; Parquet validated"})
 # SlideAudit's extracted repository files are inventoried individually below;
 # the source row records the full expanded size without duplicating it here.
 # Reports, kept separate from consulting presentation files.
 reports=rd(NEW/"reference_reports.csv")
 for r in reports:
  file_rows.append({"file_id":r.get("file_id"),"source_id":r.get("source_id"),"title":r.get("title"),"firm":r.get("firm"),"attribution_evidence":"Publisher title and source URL","publication_year":"2025" if "2025" in r.get("title","") else "","year_evidence":"Title/first-page year only; may be forecast horizon" if "2025" in r.get("title","") else "not established","document_type":"reference_report","source_page_url":r.get("source_page_url"),"requested_url":r.get("requested_url"),"final_url":r.get("final_url"),"accessed_at_utc":r.get("accessed_at_utc"),"local_path":r.get("local_path"),"format":r.get("format"),"mime_type":r.get("mime_type"),"size_bytes":r.get("size_bytes"),"sha256":r.get("sha256"),"page_or_slide_count":r.get("page_count"),"editable_original":"no","validation_status":r.get("validation_status"),"rights_status":r.get("rights_status"),"rights_evidence":r.get("rights_evidence")})
  source_by_id[r.get("source_id")]= {"source_id":r.get("source_id"),"name":r.get("title"),"category":"reference_report","seed_url":r.get("requested_url"),"official_url":r.get("final_url"),"accessed_at_utc":r.get("accessed_at_utc"),"discovered_count":1,"downloaded_size_bytes":r.get("size_bytes"),"status":"downloaded","rights_status":"unknown","rights_evidence":r.get("rights_evidence")}
  entry_rows.append({"entry_id":r.get("source_id")+"-01","source_id":r.get("source_id"),"title":r.get("title"),"firm":r.get("firm"),"listed_url":r.get("requested_url"),"resolved_url":r.get("final_url"),"file_id":r.get("file_id"),"status":"downloaded","reason":"Optional public reference report; separately classified"})
 # D04, SlideVQA, records the precise status and missing asset components even though nothing was downloaded.
 source_by_id["D04"]={"source_id":"D04","name":"SlideVQA dataset","category":"research_dataset","seed_url":"https://github.com/nttmdlab-nlp/SlideVQA","official_url":"https://huggingface.co/datasets/NTT-hil-insight/SlideVQA","revision":hf.get("NTT-hil-insight/SlideVQA",{}).get("revision"),"accessed_at_utc":releases.get("captured_at_utc"),"estimated_size_bytes":hf.get("NTT-hil-insight/SlideVQA",{}).get("download_size_bytes"),"downloaded_size_bytes":0,"discovered_count":14484,"status":"approval_required","rights_status":"restricted","license_name":"NTT Software Evaluation License","license_url":"https://huggingface.co/datasets/NTT-hil-insight/SlideVQA","rights_evidence":"Hub card requires acceptance and contact sharing; GitHub LICENSE binds users on access/use","missing_components":"Images gated; QA/bounding-box annotations require terms acceptance; OCR requires separate extraction/dependency"}
 entry_rows.append({"entry_id":"D04-01","source_id":"D04","title":"SlideVQA images, QA and bounding-box data","firm":"","listed_url":"https://huggingface.co/datasets/NTT-hil-insight/SlideVQA","resolved_url":"https://huggingface.co/datasets/NTT-hil-insight/SlideVQA","status":"approval_required","reason":"Gated evaluation agreement and contact-sharing requirement"})
 # One new discovery failure for the KPMG title with no deck found.
 failure_rows.append({"source_id":"C05","entry_id":"C05-CYBER","url_or_file":"https://kpmg.com/us/en/media/news/kpmg-cyber-security-survey.html","status":"unresolved","attempts":"1","reason":"Official page exposed a survey report but not the requested summary slides","next_action":"no public slide file resolved"})
 # Quality rows for all newly retained presentation PDFs; updated after preview review.
 # De-duplicate duplicate references by entry+hash while preserving every distinct source entry.
 seen=set();clean_dups=[]
 for r in duplicate_rows:
  key=(r.get("duplicate_entry_id"),r.get("sha256"),r.get("source_url"))
  if key not in seen:seen.add(key);clean_dups.append(r)
 # Remove accidental ID collisions only when same entry differs solely in stale empty canonical ID.
 bydup={}
 for r in clean_dups:
  k=(r.get("duplicate_entry_id"),r.get("sha256"),r.get("source_url"))
  if k not in bydup or (not bydup[k].get("canonical_file_id") and r.get("canonical_file_id")):bydup[k]=r
 clean_dups=list(bydup.values())
 # Preserve human visual reviews when regenerating the crosswalk.
 for row in quality_rows:
  previous=prior_quality.get(row.get("file_id"),{})
  if previous.get("quality_status")=="reviewed_provisional":row.update(previous)
 # Current source manifest rows supersede this script's older direct-only snapshot.
 source_rows=list(source_by_id.values())
 # Reflect counts from the complete unified entries list.
 for srow in source_rows:
  sid=srow.get("source_id");related=[e for e in entry_rows if e.get("source_id")==sid]
  if related and not srow.get("discovered_count"):srow["discovered_count"]=len(related)
 # Stable output order and no mutation of the previous corpus manifests.
 wr(SOURCES,SF,source_rows);wr(ENTRIES,EF,entry_rows);wr(FILES,FF,file_rows);wr(NEW/"duplicates.csv",DF,clean_dups);wr(NEW/"failures.csv",FAF,failure_rows)
 # Existing review file gets refreshed only with the same generated records; visual notes are added afterward.
 wr(NEW/"quality_review.csv",QF,quality_rows)

if __name__=="__main__":main()
