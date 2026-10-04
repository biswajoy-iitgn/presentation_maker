# DeckForge: Build Plan V2

| Field | Value |
|---|---|
| Status | V2, 2026-10-04. Superseded for implementation by the V3 plan in `docs/build/README.md` (architecture, stack, tickets). Kept for the milestone history and the M1 record |
| Scope | `docs/PRD_V2.md` |
| Design | `docs/TRD_V2.md` |

---

## 1. Operating model

| Who | Does |
|---|---|
| Claude Code | Architecture, all code, tests, CI, data engine, training scripts, evaluation, documentation. Works milestone by milestone on branch `claude/...`, each milestone ending in a demo and a measured exit check |
| Founder | Decisions on open items, GPU access (owned or rented), corpus upload, network allow-list for asset sources and model hubs, one-hour review per milestone (20 slides, 20 blind pairs) |
| Nobody else | No annotators, no designers, no engineers. Design taste comes from the corpus (TRD 11.4, 11.5) |

The constraint is no longer engineering hours. It is (a) GPU access for model serving, image generation and training, and (b) the founder's review cadence. Deterministic components can be built now in this environment.

---

## 2. Environment facts that shape the order

| Resource | Status in the current build environment | Needed for |
|---|---|---|
| CPU, Python, LibreOffice Impress | Available | Compiler, rendering, lint, procedural assets, data engine logic |
| GitHub raw content | Reachable | Open icon sets, flags, Natural Earth boundaries, open fonts |
| Stock image APIs, Openverse, Hugging Face | Blocked by network policy | Photo fetch, model weights. Founder can allow the hosts (O10) |
| GPU | None | Open-weight LLM serving, text-to-image, training (O9) |

---

## 3. Milestones

Order follows dependencies. "Here" means buildable in the current environment. "GPU" means it needs O9.

| # | Milestone | Where | Scope | Exit check (self-supervised unless stated) |
|---|---|---|---|---|
| M1 | Compiler, charts, assets | Here | `deckforge` package: design tokens, font-metric text fitting, slide grammar v0 with constraint layout, chart engine T1 to T3 with annotation layer, asset resolver with procedural backgrounds, icons, flags, maps, treatment (crop, colour grading, scrims) and QA, geometry lint, render pipeline, demo deck | Benchmark rebuilds of 20 corpus slides at near-parity, lint clean, every chart editable in PowerPoint, asset QA passes. Founder review 1 |
| M2 | Framework library and data engine | Here | 30 framework YAML entries and calc modules, corpus classification, deck inversion (brief per corpus deck), synthetic defect generator, storyline perturbations, golden set of 50 inverted briefs | Calc modules unit-tested, defect generator labels verified by lint, golden set frozen |
| M3 | Generation pipeline v0 | GPU (or any OpenAI-compatible endpoint for development) | LangGraph flow: brief, storyline, slide planning, content with number tokens, asset needs, compile, render, gates, repair | 50 golden briefs end to end, zero untracked numbers, reconstruction similarity baseline recorded. Founder review 2 |
| M4 | Corpus reconstruction | GPU for VLM parsing | Inverse rendering of corpus slides into SlideSpecs, coverage metric, training pairs | Coverage of corpus content slides measured, target at least 50% at first pass |
| M5 | Research, citations, stock and generated imagery | Network allow-list, GPU for text-to-image | Web research with verifier, stock adapters live, text-to-image server, asset QA calibrated on corpus imagery | Verifier re-check at least 95%, zero fabricated sources, image QA first-pass at least 80% |
| M6 | Self-supervised training | GPU | QA models (defects, storyline, titles, chart fit, verifier), discriminator, SFT on reconstruction pairs, RL with verifiable rewards and self-play | Each trained model beats its prompted baseline on held-out synthetic and corpus sets. Discriminator confusion rising. Founder review 3 |
| M7 | Brand onboarding and refinement UI | Here plus GPU for refine | Template ingestion to `DesignSystem`, gallery approval, web app, chat refine, versions | 5 public templates onboarded, refine round trip under 60 seconds |
| M8 | On-prem packaging | Here | Docker, Helm, offline bundle with weights, air-gapped mode, sizing benchmark | Clean install on a fresh GPU node in under a day. Founder review 4 |

M1 and M2 do not depend on any open item and start immediately. M3 can start on any OpenAI-compatible endpoint the founder provides, then move to self-hosted weights when GPUs arrive.

---

## 4. M1 detail (current)

Status 2026-10-04: package, chart engine, overlays, asset resolver (procedural, icons, flags, map, stock and text-to-image adapters), treatment, image QA, lint and contrast repair, demo deck and CI are in place. 21 tests pass. Remaining for M1: slide grammar with constraint layout, remaining T3 charts (Mekko, Gantt, Harvey balls), benchmark rebuild set of 20 corpus slides, spec persistence in the PPTX.

| Step | Output |
|---|---|
| Package skeleton, tokens, metrics, primitives (from `spikes/visual_proof/`) | `deckforge/render/` |
| Chart engine: column, stacked, 100% bar, waterfall, overlays (difference arrow, data rows, connectors) | `deckforge/render/charts.py`, `overlays.py` |
| Asset resolver and records | `deckforge/assets/resolver.py`, `needs.py` |
| Procedural backgrounds: light arcs, light planes, motion streaks, gradient mesh, contour lines | `deckforge/assets/sources/procedural.py` |
| Fetch sources: open icons, flags, Natural Earth map shapes, stock and text-to-image adapters | `deckforge/assets/sources/` |
| Treatment and QA: saliency crop, duotone grading, scrims, WCAG contrast, blur, duplicate hash | `deckforge/assets/treatment.py`, `qa.py` |
| Geometry lint | `deckforge/qa/lint.py` |
| Demo deck with imagery, map, icons, flags, charts | `deckforge/demo/` |
| Tests and CI | `tests/`, `.github/workflows/ci.yml` |

---

## 5. Risks and decision points

| Checkpoint | Signal | Action |
|---|---|---|
| End of M1 | Benchmark rebuilds fall short of near-parity | Extend components and tokens before any model work |
| End of M3 | Open-weight generator far below a frontier endpoint on golden briefs | Larger model tier, pull SFT forward, or allow private-cloud endpoints |
| End of M4 | Grammar coverage under 50% | Add the most frequent missing components first |
| M6 | Critic scores rise but founder review does not improve | Goodhart signal. Freeze critic, add hard checks, diversify critics |
| Any time | No GPU access | Deterministic work continues. Model milestones wait |

---

## 6. Open items

| ID | Question | Default |
|---|---|---|
| O1 | Customer private-cloud models acceptable as on-prem, or self-hosted only? | Both, self-hosted is reference |
| O5 | First customer segment | Corporate strategy teams |
| O6 | Typical customer GPU | One node, 4 x 80 GB |
| O7 | Style family priority | Consulting report, then keynote |
| O9 | GPU access and monthly budget | Rented 4 x 80 GB node during M3 to M6 |
| O10 | Allow api.pexels.com, api.unsplash.com, api.openverse.org, huggingface.co in the build environment | Needed for M5 |
