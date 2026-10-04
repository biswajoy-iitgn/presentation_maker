# presentation_maker

DeckForge: brief in, consulting-grade editable PPTX out, with grounded numbers and QA gates. On-prem, configurable to each customer's template.

## Quick start

```bash
pip install -e ".[dev]"
sudo apt-get install -y libreoffice-impress fonts-liberation   # rendering and metric-compatible fonts
python examples/auto_components_margin/build.py out/margin_recovery   # brief -> plan -> exhibits -> 13-slide board deck + plan report
python -m deckforge.demo.build_demo out/demo                    # asset pipeline demo (backgrounds, icons, flags, map)
pytest -q
```

## Package layout

| Path | What it does |
|---|---|
| `deckforge/render/` | Canvas with placement records, font-metric text fitting, native charts with pinned plot areas, annotation overlays, layout furniture |
| `deckforge/assets/` | Asset resolver: procedural backgrounds, open icons and flags, Natural Earth map shapes, stock photo APIs, local text-to-image client and reference GPU server, treatment (crop, grading, scrims) and image QA, provenance records |
| `deckforge/story/` | Plan schema (problem, issue tree, analyses, storyline, slides), fact tokens, plan-to-deck renderer, plan report |
| `deckforge/viz/` | Exhibit selector (message type + data shape, scored with reasons) and shape-built consulting exhibits: bridge, columns over line, profit pool, peer range benchmark, bubble and priority matrix, heat table, wave roadmap, numbered callouts and commentary |
| `deckforge/qa/` | Geometry and legibility lint, deterministic repairs (backlights behind low-contrast text) |
| `examples/` | Briefs run end to end. `auto_components_margin`: margin recovery board deck for a forging and machining company |
| `deckforge/demo/` | Demo deck exercising every capability with illustrative data |

## Documents

| Doc | Purpose |
|---|---|
| [docs/PRD_V2.md](docs/PRD_V2.md) | Product requirements (current) |
| [docs/TRD_V2.md](docs/TRD_V2.md) | Technical design: architecture, schemas, compiler, QA decision models, data program |
| [docs/build/README.md](docs/build/README.md) | Build plan V3: architecture, tech stack, LangGraph orchestration, LLM and Laya layers, caching, deployment with nginx, and 100 implementation tickets |
| [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md) | Build plan V2 (superseded, kept for history) |
| [docs/FRAMEWORK_LIBRARY.md](docs/FRAMEWORK_LIBRARY.md) | Consulting frameworks and analyses: question, data, visual, pitfalls |
| [docs/corpus_notes/](docs/corpus_notes/) | Deconstructions of corpus decks (Accenture, Bain, BCG, McKinsey) |
| [spikes/visual_proof/](spikes/visual_proof/) | Native-chart rebuild of benchmark slides with computed overlays and geometry lint |
| [docs/PRD_V1_review_and_open_questions.md](docs/PRD_V1_review_and_open_questions.md) | Why V1 was revised |
| [Presentation_Maker_PRD_V1.md](Presentation_Maker_PRD_V1.md) | Superseded original PRD |

## Data

Corpus acquisition scripts and manifests live in `consulting_corpus/`, `dataset_acquisition/` and `research_datasets/`. Downloaded files are not committed. See TRD section 11.1 for the data-use policy.
