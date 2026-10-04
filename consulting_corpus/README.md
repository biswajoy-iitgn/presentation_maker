# Consulting presentation corpus

Publicly linked presentations acquired for design analysis. Public availability does not grant redistribution or training rights; consult `manifests/downloads.csv`.

## Resume

Run `python3 acquire_corpus.py` from the project directory. The process checks robots.txt, serializes requests per host with a two-second interval, keeps an idempotent SHA-256 manifest, and does not submit gated forms. Review `logs/acquisition.log` and `manifests/` for outcomes.
