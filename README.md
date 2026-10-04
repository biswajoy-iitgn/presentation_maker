# presentation_maker

DeckForge: brief in, consulting-grade editable PPTX out, with grounded numbers and QA gates. On-prem, configurable to each customer's template.

## Quick start

```bash
pip install -e ".[dev]"
sudo apt-get install -y libreoffice-impress fonts-liberation   # rendering and metric-compatible fonts
python -m deckforge.demo.build_demo out/demo                    # builds a 10-slide demo deck, lints and repairs it
pytest -q
```

## Package layout

| Path | What it does |
|---|---|
| `deckforge/render/` | Canvas with placement records, font-metric text fitting, native charts with pinned plot areas, annotation overlays, layout furniture |
| `deckforge/assets/` | Asset resolver: procedural backgrounds, open icons and flags, Natural Earth map shapes, stock photo APIs, local text-to-image client and reference GPU server, treatment (crop, grading, scrims) and image QA, provenance records |
| `deckforge/qa/` | Geometry and legibility lint, deterministic repairs (backlights behind low-contrast text) |
| `deckforge/demo/` | Demo deck exercising every capability with illustrative data |

## Documents

| Doc | Purpose |
|---|---|
| [docs/PRD_V2.md](docs/PRD_V2.md) | Product requirements (current) |
| [docs/TRD_V2.md](docs/TRD_V2.md) | Technical design: architecture, schemas, compiler, QA decision models, data program |
| [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md) | Milestones, exit criteria, team, timeline |
| [docs/FRAMEWORK_LIBRARY.md](docs/FRAMEWORK_LIBRARY.md) | Consulting frameworks and analyses: question, data, visual, pitfalls |
| [docs/corpus_notes/](docs/corpus_notes/) | Deconstructions of corpus decks (Accenture, Bain, BCG, McKinsey) |
| [spikes/visual_proof/](spikes/visual_proof/) | Native-chart rebuild of benchmark slides with computed overlays and geometry lint |
| [docs/PRD_V1_review_and_open_questions.md](docs/PRD_V1_review_and_open_questions.md) | Why V1 was revised |
| [Presentation_Maker_PRD_V1.md](Presentation_Maker_PRD_V1.md) | Superseded original PRD |

## Data

Corpus acquisition scripts and manifests live in `consulting_corpus/`, `dataset_acquisition/` and `research_datasets/`. Downloaded files are not committed. See TRD section 11.1 for the data-use policy.
