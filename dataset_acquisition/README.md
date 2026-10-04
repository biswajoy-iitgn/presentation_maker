# Dataset acquisition workspace

This folder contains the acquisition scripts, evidence logs, source inventory, and unified manifests for the expanded presentation corpus. The main PDF corpus remains in `../consulting_corpus`; reports and research datasets remain in separate sibling folders.

## Resume and refresh

Run commands from the project root (`/Users/dtadmin/Desktop/DevelopmentProjects/Presentation Maker`). Scripts use paths relative to their own location and refuse to replace verified corpus files.

1. `python3 "dataset_acquisition/scripts/acquire_new_sources.py"` resumes the direct presentation candidate list. It streams to temporary files, applies the 10 GiB new-data limit, validates PDFs, hashes retained files, and records duplicates and blocked sources.
2. `python3 "dataset_acquisition/scripts/inventory_dataset_releases.py"` refreshes the documented Hub/GitHub release inventory.
3. `python3 "dataset_acquisition/scripts/capture_dataset_metadata.py"` captures public docs and the selected small SlideAudit examples. It does not accept gated terms or execute repository code.
4. `python3 "dataset_acquisition/scripts/acquire_pptbench_parquet.py"` acquires and validates the documented PPTBench train Parquet shards.
5. `python3 "dataset_acquisition/scripts/acquire_slideaudit_full.py"` resumes the pinned public SlideAudit archive when needed, inspects archive members before extraction, and verifies its inventory. It only extracts into an empty `research_datasets/slideaudit/full_release/` folder.
6. `python3 "dataset_acquisition/scripts/acquire_reference_reports.py"` acquires the optional reports to `../reference_reports/`.
7. `python3 "dataset_acquisition/scripts/render_deck_previews.py"` renders up to three representative pages per retained candidate PDF into `../consulting_corpus/previews/`.
8. `python3 "dataset_acquisition/scripts/build_master_manifests.py"` rebuilds the unified CSVs after acquisition. It reads the `candidate_*.csv` direct-acquisition records and preserves the recorded provisional visual reviews.
9. `python3 "dataset_acquisition/scripts/validate_slideaudit_release.py"` rechecks all SlideAudit JSON, CSV, and PNG assets and writes `manifests/slideaudit_validation.json`.

The `candidate_sources.csv`, `candidate_entries.csv`, `candidate_files.csv`, `candidate_duplicates.csv`, and `candidate_failures.csv` files are the resumable direct-acquisition records. The similarly named base CSVs are the consolidated crosswalk, including historical collection entries and research assets. The direct PDF and PPTBench downloaders can be rerun; SlideAudit can resume an interrupted archive download but intentionally refuses to overwrite a successful extracted release. Metadata refresh rewrites its own inventory files.

## Manifests and evidence

- `manifests/sources.csv`: source-level status, revision, counts, size, and rights evidence.
- `manifests/entries.csv`: source listings and each entry's resolved outcome.
- `manifests/files.csv`: validated local files and metadata, including separate dataset assets.
- `manifests/duplicates.csv`: exact duplicates and their canonical files.
- `manifests/failures.csv`: blocked, unresolved, or failed acquisition outcomes.
- `manifests/quality_review.csv`: lightweight visual triage; assessments are provisional.
- `logs/acquisition.log`: timestamped download/validation events.

Public access does not establish rights to train, redistribute, or resell branded slide material. Review each row's `rights_status` and `rights_evidence`; repository code licences do not automatically license embedded presentations. Gated and confidential sources were left unacquired.

## Research dataset completeness

`research_datasets/dataset_releases.json` records pinned revisions and upstream size/count claims. PPTBench Parquet is limited to the documented train split. SlideAudit is the full pinned image/annotation/description release. Slides-Align, SlideVQA, and PPTBench-V3 are metadata-only because of budget, gated terms, or unresolved underlying-data rights. AutoPresent/SlidesBench documentation and code metadata are present; separately licensed source decks were not acquired.
