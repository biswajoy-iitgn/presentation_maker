# DeckForge: Build Plan V1

| Field | Value |
|---|---|
| Status | Draft V1.1, 2026-10-04 |
| Scope | `docs/PRD_V2.md` |
| Design | `docs/TRD_V2.md` |

All durations are estimates for the team in section 1. They scale roughly linearly with team size for parallel workstreams, but not for the critical path (M1, then M2, then M3).

---

## 1. Team assumption

| Role | FTE | Owns |
|---|---|---|
| Tech lead / backend | 1 | Architecture, orchestration, API, data contracts |
| Compiler and rendering engineer | 1 | python-pptx compiler, chart engine, template ingestion, render pipeline |
| ML engineer (generation) | 1 | Model serving, prompting, retrieval, research service, generator fine-tuning |
| ML engineer (QA) | 1 | Gates, synthetic negatives, trained judges, eval harness |
| Frontend engineer | 1 (from week 8) | Web app, previews, refine UI, admin console |
| Presentation designer (consulting background) | 1 | Slide grammar, archetypes, component library, typography, gallery reviews, design labels. Visual craft is the product, so this role is full time |
| Ex-consultant annotators | 3 to 5 part-time, about 470 h total | Golden set, labels, audits |
| Product lead (founder) | 1 | Scope, design partners, acceptance |
| IP counsel | On call | Data policy, licences, customer contracts |

Hardware for development: one node with 4 x 80 GB GPUs (owned or rented) from week 4. Rented burst capacity for training in M6.

---

## 2. Workstreams

| WS | Name | Milestones |
|---|---|---|
| WS1 | Compiler, charts, archetypes, templates | M1, M5 |
| WS2 | Generation pipeline and orchestration | M2 |
| WS3 | QA decision models and evaluation | M3, M6 |
| WS4 | Research and grounding | M4 |
| WS5 | Data program and legal | M0, feeds M3 and M6 |
| WS6 | Product, UI and refinement | M7 |
| WS7 | Platform and on-prem packaging | M8 |
| WS8 | Framework library and corpus reconstruction | M2, M6 |

---

## 3. Milestones

### M0 Foundations (weeks 0 to 3)

Scope:
- Close open items O1 to O6 (PRD section 11).
- Counsel review of the clean-room data policy (TRD 11.1). Decide what, if anything, from the current corpus is usable and how.
- Repository skeleton, CI, coding standards, Pydantic schemas v1 for all objects in TRD 4.1.
- Golden set v0: 20 briefs written by you and annotators, with reference storylines.
- Annotator recruitment and labelling guidelines (taxonomy from TRD 10.2).
- Development GPU node running vLLM with the reference model.

Exit criteria:
- Schemas v1 reviewed and frozen (changes go through versioning).
- Data policy signed off.
- 20 golden briefs in the repo.
- Model endpoint serving structured output at measured throughput.

### M1 Compiler and chart engine spike (weeks 2 to 9). Critical path

Scope:
- Starting point: `spikes/visual_proof/` (native charts with computed overlays, font-metric text fitting, geometry lint).
- Slide grammar v0 and constraint layout (TRD 7.2), typography roles and tokens (TRD 7.8).
- think-cell parity checklist (TRD 7.3) and the annotation layer.
- Neutral consulting house template (PRD section 6), designed with the designer.
- Compiler for 15 archetypes first: title, exec summary, chart with takeaway, two charts, waterfall, Marimekko, time series with CAGR, ranked bar, options table, Harvey-ball table, 2x2, chevrons, Gantt, next steps, sources.
- Chart tiers T1 fully, T2 waterfall and CAGR arrow, T3 Marimekko, Gantt, Harvey balls, 2x2.
- Number-token formatter and calc engine.
- Text fitting with font metrics.
- ILLUSTRATIVE marker, data workbook generation and re-binding.
- Render pipeline (LibreOffice to PNG) and geometry lint (QA-5 deterministic, QA-6).
- Corpus statistics pass on the public corpus (internal analysis only, if counsel allows) to calibrate density bands.

Exit criteria:
- 50 hand-written SlideSpecs compile with zero lint criticals.
- Files open in PowerPoint on Windows and Mac without repair prompts.
- Designer rates at least 80% of the 50 slides 4 or 5 out of 5 on "consulting-grade".
- Benchmark recreation: 20 corpus slides from at least 4 firms rebuilt from their data. In a blind side-by-side, the designer rates at least 80% "equal craft" to the original.
- No chart element left at library default (lint).
- Native chart data edits in PowerPoint work for T1 and T2.
- Workbook round trip replaces all dummy values correctly.

Why first: this is the hardest deterministic component and every later stage depends on it. If it cannot reach consulting quality with hand-written specs, no model will.

### M2 Generation pipeline v0 (weeks 6 to 13)

Scope:
- LangGraph graph per TRD 5.1 without research: brief parsing, clarification, storyline, checkpoint, data plan, user-data binding, dummy generation, slide planning, content writing, compile, render.
- Exemplar retrieval (Tier A only. Initially designer-made exemplars).
- Archetype library extended to about 50.
- Framework library v1: 30 entries with YAML schema, retrieval and calc modules (`docs/FRAMEWORK_LIBRARY.md`).
- Corpus reconstruction pipeline v0 run on 500 corpus pages to measure grammar coverage (TRD 11.5).
- Minimal internal UI or CLI for testing.
- Frontier baseline run on golden briefs to measure the on-prem gap.

Exit criteria:
- All 20 golden briefs run end to end without crashes.
- Zero untracked numbers.
- Median time to full draft at most 15 minutes on the reference tier.
- Baseline keep rate and gap to frontier baseline measured and recorded.
- Grammar coverage on the 500-page sample measured. Missing components logged and scheduled.

### M3 QA v1 (weeks 10 to 18)

Scope:
- QA-4, QA-6, QA-8 deterministic. QA-5 geometry lint complete.
- QA-1, QA-2, QA-3, QA-5 (visual), QA-7 as prompted judges.
- Synthetic defect generator (TRD 10.2).
- Evaluation of the visual judge against SlideAudit labels.
- Repair loop and routing (TRD 5.3). QA report output.
- First 1,000 expert defect labels.

Exit criteria:
- Precision and recall per gate published on a held-out labelled set.
- Critical defect escape rate at most 10% (pilot target is 5% after M6).
- Repair loop raises designer score on the golden set by a measurable margin versus no repair.

### M4 Research and citations (weeks 12 to 19)

Scope:
- Search adapter interface with two implementations (customer API, self-hosted metasearch).
- Fetch, extract, verify, tier, cross-check, conflict handling (TRD 9).
- Citation footnotes and sources appendix.
- Egress proxy and air-gapped fallback.

Exit criteria:
- Audit of 200 sourced numbers: at least 95% correct on value, unit, scope and period.
- Zero fabricated URLs or passages.
- Research adds at most 5 minutes to a 20-slide deck with 10 data needs.

### M5 Brand onboarding (weeks 14 to 20)

Scope:
- Template ingestion to `DesignSystem` (TRD 8).
- Archetype-to-layout mapping and synthesis.
- Gallery render and admin approval flow.
- Auto-generated conformance rules.

Exit criteria:
- 5 real corporate templates (from design partners or public templates with suitable licences) onboarded, each in at most 1 working day with at most 2 hours of manual adjustment.
- Gallery passes QA-6 for all 5.

### M6 Trained QA models and generator adaptation (weeks 16 to 30)

Scope:
- Complete annotation program (TRD 11.4).
- Full corpus reconstruction (TRD 11.5) producing planner training pairs and QA-7 preference pairs.
- Train QA-5 defect classifier, QA-2 action-title classifier, QA-1 and QA-7 reward models, QA-4 verifier.
- Calibrate thresholds to the 5% escape target.
- Generator L1 LoRA fine-tuning if M2 and M3 evidence meets the entry condition (TRD 12).

Exit criteria:
- Each trained model beats its prompted predecessor on held-out data, otherwise the prompted version stays.
- Critical defect escape rate at most 5%.
- Keep rate on golden set at least 70%.
- Grammar coverage of corpus content slides at least 70%.

### M7 Product and refinement (weeks 12 to 26)

Scope:
- Web app: brief form, storyline editor, slide preview grid, QA flags, data request list, downloads.
- Chat refine at slide and deck level with partial regeneration.
- Version history and visual diffs.
- SSO, roles, audit log.

Exit criteria:
- Usability test with 5 target users: each produces a 20-slide deck from brief to download without help.
- Refine request to updated slide in at most 60 seconds for slide-level changes.

### M8 On-prem packaging and pilot (weeks 24 to 34)

Scope:
- Helm chart, docker compose single node, offline bundle with model weights.
- Hardware sizing benchmark for economy and reference tiers.
- Security review, penetration test, SBOM.
- Pilots with 2 to 3 design partners.

Exit criteria:
- Install in a customer environment in at most 1 day.
- Pilot keep rate at least 70%, storyline approval at least 60%, zero fabricated sources.
- Signed pilot feedback and go/no-go for GA.

---

## 4. Timeline

```text
Week          0    4    8    12   16   20   24   28   32   36
M0 Found.     ####
M1 Compiler     ########
M2 Gen v0           ########
M3 QA v1                ##########
M4 Research               ########
M5 Brand                    #######
M6 Trained QA                 ###############
M7 Product                ###############
M8 On-prem/pilot                        ###########
```

Pilot start: about week 30. Pilot complete: about week 34 (about 8 months). Estimate.

---

## 5. First four weeks in detail

| Week | Task | Owner | Output |
|---|---|---|---|
| 1 | Answer O1 to O6. Engage IP counsel | Founder | Decisions log in PRD |
| 1 | Repo layout, CI, lint, test scaffolding | Tech lead | `deckforge/` package skeleton |
| 1 | Schemas v1 (DataItem, SlideSpec, ChartSpec, DesignSystem, GateVerdict) | Tech lead | `deckforge/schemas/` with tests |
| 0 | Visual proof spike (done) | Claude Code | `spikes/visual_proof/` |
| 1 to 2 | House template v1, typography tokens, 15 archetype sketches | Designer | `.potx` plus archetype specs |
| 1 to 3 | Compiler core: template loading, text slots, text fitting, token formatter | Compiler engineer | Compiles text archetypes |
| 2 to 4 | Native chart styling and waterfall construction | Compiler engineer | T1 plus waterfall |
| 2 to 3 | Golden briefs v0 (20) and labelling guide | Founder plus annotators | `eval/golden/` |
| 2 to 4 | vLLM serving, model gateway, structured output tests | ML (generation) | Endpoint plus throughput numbers |
| 3 to 4 | Render pipeline and geometry lint | ML (QA) | `deckforge/render/`, `deckforge/qa/lint/` |
| 3 to 4 | Framework library: first 30 YAML entries and calc modules for PVM, CAGR, waterfall, Mekko shares | ML (generation) plus founder | `deckforge/knowledge/` |
| 4 | Corpus page classification and framework tagging | ML (QA) | Style statistics and framework frequency report |

Proposed repository layout:

```text
deckforge/
  schemas/        Pydantic contracts
  compiler/       archetypes, charts (t1, t2, t3), fitting, tokens, workbook
  templates/      house template, DesignSystem ingestion
  graph/          LangGraph nodes and routing
  models/         model gateway, prompts, retrieval
  research/       adapters, extraction, verification
  qa/             lint, gates, judges, calibration
  render/         LibreOffice and rasterisation
  api/            FastAPI
web/              Next.js frontend
training/         data prep, SFT, reward models, evals
eval/             golden set, harness, reports
deploy/           Docker, Helm, compose, offline bundle
docs/             PRD, TRD, plans
```

---

## 6. Risks and decision points

| Checkpoint | Signal | Action |
|---|---|---|
| End of M1 | Designer rates under 60% of hand-written slides consulting-grade | Stop model work. Fix archetypes and compiler first |
| End of M2 | On-prem generator keep rate more than 25 points below frontier baseline | Move to the larger model tier, pull L1 fine-tuning forward, or make private-cloud endpoints the primary mode |
| End of M2 | Grammar coverage of corpus sample under 50% | Add components before scaling generation. Designer and compiler engineer prioritise the most frequent failures |
| End of M3 | Visual judge recall on critical defects under 70% against SlideAudit and expert labels | Rely on deterministic lint for blocking. Prioritise QA-5 training data |
| End of M4 | Citation accuracy under 90% | Restrict research to Tier 1 and 2 domains until fixed |
| Before GA | Counsel review of D9 training-data risk, customer indemnity terms | If customers require clean provenance, retrain shipped models on Tier A data (TRD 11.1). Keep provenance logs from day one so this is possible |
| Annotators unavailable | Fewer than 3 recruited by week 4 | M6 slips one to one with the delay. Prompted judges remain in pilot |

---

## 7. Decisions pending from founder

Copied from PRD section 11 for convenience.

| ID | Question | Default |
|---|---|---|
| O1 | Customer private cloud models acceptable as on-prem, or self-hosted only (possibly air-gapped)? | Both. Self-hosted is reference |
| O7 | Which style families first? | Consulting report, then keynote |
| O8 | "Fonts made by the model" means designed typography, not defaults? | Yes |
| O3 | Team, budget, pilot date | Section 1 team, about 8 months |
| O4 | Can you recruit 3 to 5 ex-consultants for about 470 hours? | Required |
| O5 | First customer segment and design partners | Corporate strategy teams |
| O6 | Typical customer GPU availability | One node, 4 x 80 GB |
