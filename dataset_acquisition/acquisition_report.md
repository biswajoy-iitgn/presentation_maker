# Expanded presentation and research dataset acquisition

**Acquisition date:** 2026-10-02 UTC  
**Workspace:** `/Users/dtadmin/Desktop/DevelopmentProjects/Presentation Maker`  
**Scope:** Publicly available presentation PDFs, four optional reference reports, and research datasets. Existing project files and the legacy corpus were preserved.

## Summary

- Added **14 unique, validated presentation PDFs** (39,160,398 bytes; 396 PDF pages). All 14 are PDF-only; no editable PPT/PPTX original was acquired in this expansion. The 14 were visually sampled on the first, middle, and last page and marked `reviewed_provisional`.
- Retained the **130 legacy corpus files** without reclassifying or visually reviewing them. Their existing manifest records list 128 PDFs and 2 PPTX files. The combined corpus inventory therefore has 144 legacy/new presentation-corpus files (142 PDF and 2 PPTX); legacy rows remain `legacy_unclassified`, so the combined count is not a claim that all 144 are decks.
- Added four separately classified reference reports (35,173,015 bytes; 281 pages).
- Acquired all six Parquet train shards exposed for the four documented PPTBench task repositories: **4,240 rows** and 1,916,286,845 bytes total. This means the Hub Parquet train shards are present; it does not mean every upstream task dependency or external asset was acquired.
- Acquired the pinned SlideAudit release: 2,400 metadata rows, 2,400 annotation JSON files, 2,400 description JSON files, and 2,400 image paths. All JSON parsed and all images passed integrity checks. SHA-256 review found **2,311 unique image contents**, with 89 exact duplicate image paths retained in the raw release and cross-referenced in the duplicate manifest.
- New retained data, reports, research assets, rendered previews, scripts, manifests, and logs total approximately **3.26 GB**. The 10 GB limit was not exceeded. At final inventory, approximately **1.29 TB** of disk space remained free, above the 5 GB floor.
- The consolidated manifests contain **50 source records, 656 entries, 7,291 unique file records, 119 exact-duplicate references, and 389 failure/gate records**. The failure log includes historical collection failures as well as this expansion; it is not a count of 389 newly attempted downloads.

## Presentation corpus

### New presentation PDFs

| Attributed firm / speaker | New unique PDFs | Files |
|---|---:|---|
| Deloitte | 4 | 4 |
| KPMG | 3 | 3 |
| Bain | 1 | 1 |
| BCG | 1 | 1 |
| PwC | 1 | 1 |
| Pfizer | 1 | 1 |
| HSE | 1 | 1 |
| Meta | 1 | 1 |
| Bakkavor | 1 | 1 |
| **Total** | **14** | **14** |

The Deloitte conference links include four client/speaker presentations (Pfizer, HSE, Meta, and Bakkavor). Deloitte’s own AI and economics PDFs were already acquired as B04 and B05; the conference page references are exact duplicates. KPMG’s three additions are the 30 June reporting slides, 31 December reporting slides, and Global Aviation Conference 2025 presentation. BCG’s additional deck is the January 2025 *Executive Perspectives: BCG’s Guide to Cost and Growth*.

The direct candidate results are B03 and B04–B08 downloaded, B02 deduplicated against an existing Bain file, and B01 left unacquired because the PDF expressly requires specific McKinsey permission. New files are under `consulting_corpus/files/<firm>/`; exact source URLs, final URLs, page counts, SHA-256 values, and rights evidence are in `manifests/files.csv`.

### Current retained corpus files by attribution and format

Counts below are the legacy 130 files as previously recorded plus the 14 newly confirmed presentations. Historical records have not been reclassified, so some legacy PDFs may be reports or other document types. The four optional reports are excluded here and listed separately below.

| Firm | PDF | PPTX | Legacy status |
|---|---:|---:|---|
| Accenture | 6 | 0 | 6 legacy |
| BCG | 9 | 1 | 8 legacy PDFs, 1 new PDF, 1 legacy PPTX |
| Bain | 6 | 0 | 5 legacy PDFs, 1 new PDF |
| Bakkavor | 1 | 0 | 1 new PDF |
| Deloitte | 6 | 0 | 2 legacy PDFs, 4 new PDFs |
| EY | 8 | 0 | 8 legacy |
| HSE | 1 | 0 | 1 new PDF |
| KPMG | 6 | 0 | 3 legacy PDFs, 3 new PDFs |
| L.E.K. | 4 | 0 | 4 legacy |
| McKinsey | 51 | 0 | 51 legacy |
| Meta | 1 | 0 | 1 new PDF |
| Pfizer | 1 | 0 | 1 new PDF |
| PwC | 30 | 0 | 29 legacy PDFs, 1 new PDF |
| Strategy& | 5 | 0 | 5 legacy |
| Unknown firm | 8 | 1 | 8 legacy PDFs, 1 legacy PPTX |
| **Total** | **142** | **2** | **130 legacy files plus 14 new presentations** |

### Preview and quality triage

The 14 new PDFs have three representative pages rendered apiece (first, middle, last), with 14 contact sheets in `consulting_corpus/previews/<file_id>/`. Sampled pages were legible at slide scale and rendered without obvious clipping or corruption. This is a limited visual review, not a complete slide-by-slide audit. The one Japanese presentation is marked `ja`; the other 13 are marked `en`. No standalone slide images were acquired as corpus examples; preview PNGs are review aids only.

## Reference reports

These reports are stored separately under `reference_reports/files/<firm>/` and are not counted as presentation decks.

| Source | Report | Pages | Bytes | Rights status |
|---|---|---:|---:|---|
| Bain | The Working Future | 76 | 7,172,543 | Unknown |
| PwC | Wealth Management Insights 2025 | 20 | 2,397,021 | Unknown |
| PwC | Global Business Services Study 2025 | 124 | 13,472,047 | Unknown |
| KPMG | 2025 Futures Report | 61 | 12,125,256 | Unknown |
| **Total** | **4 reports** | **281** | **35,173,015** | |

## Research datasets

### Acquired

| Dataset | Local path | Verified contents | Rights and limits |
|---|---|---|---|
| SlideAudit | `research_datasets/slideaudit/full_release/` | Pinned GitHub revision `642d490b7c1d2e78a50a631bfd359433397f3ecf`; 2,400 metadata rows, 2,400 image paths, 2,400 annotation JSON files, and 2,400 description JSON files. Every annotation/description JSON parsed and every image passed PNG integrity validation. 89 duplicate image paths and two repeated repository files remain on disk and are cross-referenced. | Dataset README and LICENSE state CC BY 4.0. Attribute the dataset; that licence does not grant rights to unrelated material. |
| PPTBench Detection | `research_datasets/pptbench/raw_parquet/detection/` | Train: 1,200 rows in 2 shards; 645,286,505 bytes. | No explicit dataset licence found; underlying slide/image rights unknown. |
| PPTBench Understanding | `research_datasets/pptbench/raw_parquet/understanding/` | Train: 1,039 rows in 1 shard; 381,550,842 bytes. | Hub card declares Apache-2.0; rights in embedded slide materials were not separately established. |
| PPTBench Modification | `research_datasets/pptbench/raw_parquet/modification/` | Train: 1,201 rows in 2 shards; 467,169,268 bytes. | No explicit dataset licence found; underlying slide/image rights unknown. |
| PPTBench Generation | `research_datasets/pptbench/raw_parquet/generation/` | Train: 800 rows in 1 shard; 422,280,230 bytes. | No explicit dataset licence found; separate generation image assets were not downloaded. |
| **PPTBench train total** | `research_datasets/pptbench/raw_parquet/` | **4,240 rows; 6 validated Parquet files; 1,916,286,845 bytes.** Each shard was checked for Parquet structure and row count. | The PPTBench-Eval repository’s MIT code licence does not license the benchmark data. |

AutoPresent/SlidesBench documentation and repository licence metadata are saved under `research_datasets/slidesbench/`. The pinned repository is `98e0c012e89469863d9c3c8bc87eac967d82b2e6`; its MIT licence applies to code. The README points to SlideShare collections rather than a separately licensed dataset release, so source decks were not acquired.

### Metadata only, gated, or partial

| Dataset/source | Outcome and missing components |
|---|---|
| Slides-Align | Metadata/docs only at `research_datasets/slides_align/`. Hub storage is 57,073,806,859 bytes, exceeding the 10 GB budget. The local README describes 1,326 rankings, nine generator products, seven scenario categories, 187 topics, and about 15,000 slide images; the Hub viewer showed 756 rows. Rankings, images, extracted content, and layout detections were not downloaded. MIT is stated for the dataset, but originating product terms may still apply to generated slides. |
| SlideVQA | `approval_required`; no gated files acquired. The Hub requires accepting the NTT Software Evaluation License and sharing contact details; the GitHub licence also imposes the agreement. The Hub lists 14,484 QA pairs across train/validation/test and 20 page images per item, while bounding boxes are separate; OCR requires a separate extraction dependency and is not in the Hub feature set. The Hub estimates 10.90 GB to download and 36.68 GB expanded. No agreement was accepted and no contact information was submitted. |
| PPTBench-V3 | Metadata and rights notes only at `research_datasets/pptbench_v3/`. The current Hub API revision is `608f01bf879d6870475f37b370c685a0b8938987` (used storage 5.82 GB); its README describes a 7.2 GB dataset plus a 0.50 GB rendering environment at a different pinned revision. The card uses `other`, and source decks come from third-party template sites. It was not downloaded pending rights review; rights, rather than the 10 GB limit alone, remain unresolved. |
| PPTBench-Eval | README and MIT code licence saved; code was not installed or run. The separate generation image pack was not acquired. |

The raw pinned revisions, Hub counts and sizes, GitHub tree inventories, and access notes are in `research_datasets/dataset_releases.json` and the dataset-specific README files.

## Source outcomes and approvals

The consolidated `sources.csv` has 50 records: 18 `downloaded`, 5 `complete`, 13 `partial`, 3 `robots_disallowed`, 3 `approval_required`, 3 `metadata_only`, 2 `access_restricted`, 2 `permission_required`, and 1 `duplicate`. Eighteen of the default 20 focused search queries were used; collection pages were not exhaustively enumerated and no exhaustive-coverage claim is made.

| Source | Recorded outcome |
|---|---|
| McKinsey/IACPM credit GenAI deck (B01) | `permission_required`: the PDF labels itself internal-use-only and prohibits use without specific McKinsey permission. Not downloaded. |
| McKinsey LIMRA Insurance 360 and Taking Action on Nature decks (C06) | `permission_required`: each surfaced PDF states that specific McKinsey permission is required. Not retained. |
| IGDS McKinsey retail GenAI deck (C06-IGDS) | `permission_required`: explicitly excluded by the brief unless permission is documented. No permission or verified public file URL was established; no file acquired. |
| EY webcast attachments (C02–C03) | `approval_required`: attachment access follows webcast registration. No registration or form submission. |
| EY SlideShare profile (C01) | `partial`: public profile view showed 420 slide shows; no bulk inventory/download was completed. |
| SlideScience and Analyst Academy collections (A02, A03, A05) | `access_restricted` or `robots_disallowed`; CAPTCHA, robots restrictions, and/or first-name/email gate encountered. No challenge bypassed and no forms submitted. |
| LinkedIn post (A11) | `access_restricted`; no comment or registration submitted. |
| KPMG Cybersecurity Survey Summary Slides (C05-CYBER) | `unresolved`: official survey page surfaced a report but no summary-slide deck. |
| PPTBench-V3 | `metadata_only`; data rights need review before acquisition/use. |

Other collection entries include unresolved listings, dead links, historical validation failures, and duplicates. See `manifests/entries.csv` and `manifests/failures.csv`; these preserve source-specific outcomes instead of treating advertised collection counts as downloaded decks.

## Deduplication, validation, and rights

- Exact SHA-256 duplicate references: **119 total**. These include 25 historical duplicate references, B02 matching an existing Bain file (`dl_1b05bc5053002b43`), two Deloitte conference links matching B04/B05, and 91 repeated SlideAudit paths. Duplicate raw SlideAudit paths remain present to preserve the upstream structure.
- The 14 new candidate PDFs were signature-checked, parsed, checked for encryption, page-counted, and SHA-256 hashed before retention. Parquet shards were structurally read and their row counts captured. SlideAudit CSV/JSON/PNG integrity checks are summarized in `manifests/slideaudit_validation.json`.
- Public access is not treated as permission for commercial training, redistribution, or resale. All 14 new presentation PDFs and all four optional reports have `rights_status=unknown`; their publishers did not provide a reuse grant in the inspected download source. Dataset/code rights are recorded separately from rights in embedded slides.
- Current visual review applies to the 14 new PDFs only. The 130 legacy records remain unreviewed in `quality_review.csv`.

## Storage and deliverables

| Directory | Current size |
|---|---:|
| `consulting_corpus/` (legacy corpus, 14 new PDFs, previews, manifests/logs) | about 490 MB |
| `reference_reports/` | about 35.2 MB |
| `research_datasets/` | about 3.16 GB |
| `dataset_acquisition/` | about 3.6 MB |
| **All output directories** | **about 3.69 GB** |

The 3.26 GB new-data budget total excludes the pre-existing legacy files but includes all newly acquired data, research assets, previews, and acquisition files. The temporary SlideAudit archive was removed after validation; peak usage including that temporary archive remained below the 10 GB cap, and no second large cache copy remains. Final free space was approximately 1.28 TB.

Primary outputs:

- Consulting PDFs and preview sheets: `consulting_corpus/files/` and `consulting_corpus/previews/`
- Separate reports: `reference_reports/files/`
- Research assets: `research_datasets/`
- Resumable scripts: `dataset_acquisition/scripts/`
- Consolidated manifests: `dataset_acquisition/manifests/`
- Acquisition events: `dataset_acquisition/logs/acquisition.log`

## Selected upstream references

- [Deloitte Shared Services Conference highlights](https://www.deloitte.co.uk/sharedservicesconference/highlights/)
- [KPMG 30 June reporting presentation page](https://kpmg.com/au/en/insights/financial-reporting/accounting-reporting-webinars/30-june-2025-financial-reporting-guidance.html)
- [KPMG 31 December reporting presentation page](https://kpmg.com/au/en/insights/financial-reporting/accounting-reporting-webinars/financial-reporting-31-december-webinar.html)
- [KPMG Global Aviation Conference 2025](https://kpmg.com/xx/en/what-we-do/industries/infrastructure/global-aviation-conference.html)
- [BCG Executive Perspectives: Guide to Cost and Growth PDF](https://www.bcg.com/assets/2025/executive-perspectives-guide-to-cost-and-growth-15jan.pdf)
- [McKinsey Terms of Use](https://www.mckinsey.com/terms-of-use)
- [SlideAudit repository and licence](https://github.com/zhuohaouw/SlideAudit)
- [Slides-Align Hub card](https://huggingface.co/datasets/Yqy6/Slides-Align)
- [SlideVQA Hub card](https://huggingface.co/datasets/NTT-hil-insight/SlideVQA)
- [PPTBench-Eval documentation](https://github.com/Gastronomicluna/PPTBench-Eval)
- [PPTBench task collection](https://huggingface.co/collections/tyrionhuu/pptbench)
- [PPTBench-V3 Hub card](https://huggingface.co/datasets/Wenkaiwang/PPTBench-V3)
