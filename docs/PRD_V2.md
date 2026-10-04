# DeckForge: Product Requirements Document V2

| Field | Value |
|---|---|
| Status | Draft V2, 2026-10-04. Supersedes `Presentation_Maker_PRD_V1.md` |
| Companion docs | `docs/TRD_V2.md` (technical design), `docs/BUILD_PLAN.md` (milestones), `docs/PRD_V1_review_and_open_questions.md` (rationale for changes) |
| Codename | DeckForge (placeholder) |

---

## 0. Decisions, assumptions, open items

### 0.1 Decisions taken (from founder answers, 2026-10-04)

| ID | Decision |
|---|---|
| D1 | Commercial product, sold to companies. Configurable to each customer's design guidelines |
| D2 | Deployed on-prem. Customer data and documents do not leave the customer environment |
| D3 | Output is an editable PPTX with native PowerPoint charts, finished by the user in PowerPoint |
| D4 | Customer can supply a template presentation and the product adopts its standards. Without one, the product produces decks in a top-tier consulting house style (McKinsey-grade quality) |
| D5 | Input is a brief: topic, requirements, data available, what the user wants to show |
| D6 | User data arrives as Excel or CSV. Where data is missing, the product inserts editable dummy data |
| D7 | Web research with citations is in scope for v1 |
| D8 | Trained QA decision models must check storyline flow, charts, factuality and standards against top-consulting quality |

### 0.2 Working assumptions (change if wrong)

| ID | Assumption | Impact if wrong |
|---|---|---|
| A1 | "On-prem" allows two modes: fully self-hosted open-weight models on customer GPUs (reference mode), and models hosted in the customer's own private cloud tenancy | If only air-gapped is allowed, web research needs a customer-approved egress path or is disabled |
| A2 | Buyers are enterprise strategy, corporate development, finance and transformation teams, plus consulting boutiques | Changes golden-set deck types and onboarding |
| A3 | English only for v1 | Multilingual adds tokenisation, typography and QA work |
| A4 | 16:9 slides, 10 to 40 slides per deck | Long decks (60+) need chapter-level parallelism |
| A5 | think-cell is not required. Native PowerPoint charts are the default. A think-cell adapter is optional later | think-cell automation needs Windows with PowerPoint and think-cell installed on the server |
| A6 | Team of about 5 FTE plus part-time ex-consultant annotators and IP counsel | Timeline in `BUILD_PLAN.md` scales with this |

### 0.3 Open items (need founder input)

See section 11.

---

## 1. Product summary

A user writes a brief. DeckForge drafts a consulting-grade storyline for approval, then builds an editable PPTX in the customer's template, or in the default consulting house style. Charts are native and data-editable. Numbers come from user files or cited web sources, and anything missing is filled with clearly marked, editable dummy data. QA models check the storyline, every slide, every chart and every number before the deck is released. The user refines through chat and then finishes in PowerPoint.

---

## 2. Users and buyers

| Role | Needs | Primary surfaces |
|---|---|---|
| Deck author (analyst, associate, manager) | First draft of a strong deck in minutes, defensible numbers, minimal reformatting | Brief form, storyline review, slide preview, chat refine, download |
| Reviewer (partner, director, CFO) | Fast confidence that numbers are right and the story holds | QA report, sources appendix, comments |
| Brand admin / design ops | Decks follow company template and rules without policing | Template onboarding, archetype gallery approval, rule editor |
| IT / security | On-prem install, SSO, audit, no data egress | Installer, admin console, logs |

---

## 3. Core workflow

```text
1 Brief         user fills topic, objective, audience, requirements, "what I want to show", uploads Excel/CSV
2 Clarify       system asks at most 5 clarifying questions if the brief is ambiguous (skippable)
3 Storyline     system proposes governing thought, SCR, chapters, one action title per slide, data plan
                CHECKPOINT: user approves or edits
4 Build         slides generated in parallel: archetype, content, charts, data binding, research
5 QA            decision models check, repair automatically, flag what they cannot fix
6 Review        user sees slide previews, QA flags, data request list. Refines via chat
7 Data fill     user uploads data or edits charts in PowerPoint. Re-binding regenerates affected slides
8 Release       final QA. Export blocked as "final" while dummy data or critical QA failures remain
```

---

## 4. Functional requirements

Priority: **M** = MVP (pilot), **V1.1** = after pilot, **L** = later.

### 4.1 Brief intake (FR-B)

| ID | Requirement | Pri |
|---|---|---|
| FR-B1 | Structured brief form: topic, objective/decision sought, audience, deck length, requirements, "what I want to show", tone. Free text accepted in every field | M |
| FR-B2 | Upload Excel (.xlsx) and CSV. Each sheet/table is profiled (columns, units, periods, granularity) | M |
| FR-B3 | Upload reference documents (PDF, DOCX, PPTX) as additional sources | V1.1 |
| FR-B4 | Clarification step: at most 5 targeted questions, each with a proposed default | M |

### 4.2 Storyline (FR-S)

| ID | Requirement | Pri |
|---|---|---|
| FR-S1 | Generate governing thought, situation-complication-resolution, chapter structure, and one action title per slide | M |
| FR-S2 | Action titles are full-sentence "so-what" statements, at most 2 lines at template title size | M |
| FR-S3 | Titles read in sequence tell the whole story without the slide bodies (horizontal logic) | M |
| FR-S4 | Storyline includes a data plan: for each slide, the evidence needed and where it will come from (user data, research, dummy) | M |
| FR-S5 | User can edit, reorder, add, delete slides in the storyline before build | M |
| FR-S6 | Optional executive summary and agenda/tracker slides generated from the storyline | M |

### 4.3 Data, research and placeholders (FR-D)

| ID | Requirement | Pri |
|---|---|---|
| FR-D1 | Every number in the deck is a typed data item with one status: `provided` (user file), `sourced` (web, cited), `derived` (computed from other items, formula kept), `dummy` | M |
| FR-D2 | The text generator cannot write factual numbers directly. It references data items, and the compiler renders the values. Any untracked number fails QA | M |
| FR-D3 | Map uploaded columns to chart data needs, with user confirmation when ambiguous | M |
| FR-D4 | Web research for data needs marked "research": search, read, extract, verify, cite. Source tiering and cross-checking (TRD section 9) | M |
| FR-D5 | Dummy data is realistic in shape and magnitude, stored as native chart data so it is editable in PowerPoint, and marked with a removable "ILLUSTRATIVE" sticker | M |
| FR-D6 | Generate a data request list: every dummy item with metric, unit, period, scope, slide reference | M |
| FR-D7 | Generate a data input workbook (one sheet per chart, pre-shaped). Upload it back to replace dummy data across the deck | M |
| FR-D8 | Derived metrics (CAGR, share, delta, bps change, index) are computed by a deterministic engine, never by the model | M |
| FR-D9 | Consistency: the same metric, period and scope shows the same value everywhere in the deck | M |
| FR-D10 | Air-gapped mode: research disabled, data needs default to dummy | M |

### 4.4 Visuals (FR-V)

| ID | Requirement | Pri |
|---|---|---|
| FR-V1 | Closed library of about 35 slide archetypes (TRD 7.2). The model chooses and fills archetypes and cannot invent free-form layouts | M |
| FR-V2 | Chart catalogue with three tiers (native, native plus overlay, shape-built), covering bar/column families, line, area, pie/doughnut, scatter, bubble, waterfall, Marimekko, Gantt, Harvey-ball tables, 2x2 matrices, CAGR annotations | M |
| FR-V3 | Chart type chosen from the message type (component, item, time series, frequency, correlation, bridge, schedule, assessment, prioritisation) | M |
| FR-V4 | Frameworks and diagrams: process chevrons, issue trees, pillars, timelines, org charts, value chains, as editable grouped shapes | M |
| FR-V5 | Icons from a licensed, customer-replaceable icon set | V1.1 |
| FR-V6 | Message emphasis in charts: highlight colour on the data that proves the title, everything else neutral | M |
| FR-V7 | Photos, AI-generated imagery, animations | L |

### 4.5 Template and brand configuration (FR-T)

| ID | Requirement | Pri |
|---|---|---|
| FR-T1 | Ingest a customer template (.potx or .pptx with masters and sample slides) and extract a design system: theme colours, fonts, sizes, margins, grid, title/footer/source/tracker positions, chart styling | M |
| FR-T2 | Map every archetype to a template layout, or synthesise it on the template grid if no layout fits | M |
| FR-T3 | Render an archetype gallery in the customer template for admin approval before use | M |
| FR-T4 | Admin rule editor: word limits, mandatory elements (source line, tracker, confidentiality marker), forbidden elements | V1.1 |
| FR-T5 | Default "consulting house style" theme shipped with the product (section 6) | M |
| FR-T6 | Multiple templates per tenant (e.g. internal vs external) | V1.1 |

### 4.6 QA decision models (FR-Q)

| ID | Requirement | Pri |
|---|---|---|
| FR-Q1 | Gates for storyline flow, slide message, chart integrity and fit, factuality and provenance, layout and design, template conformance, and an overall consulting-grade preference score (TRD section 10) | M |
| FR-Q2 | Each gate returns pass/fail, severity, defects with slide/element reference, and the repair target | M |
| FR-Q3 | Automatic repair loop with a bounded number of attempts. Unresolved defects become visible flags for the user | M |
| FR-Q4 | Hard gates block "final" export: untracked numbers, failed citation verification, critical layout defects, template violations, remaining dummy data | M |
| FR-Q5 | QA report exported with the deck: gate results, sources, data status per number | M |
| FR-Q6 | Models trained and calibrated on labelled data, with published precision/recall per gate on a held-out set | M (prompted) / V1.1 (trained) |

### 4.7 Refinement (FR-R)

| ID | Requirement | Pri |
|---|---|---|
| FR-R1 | Chat instructions at slide level ("make this a waterfall", "shorten title", "split into two slides") and deck level ("add a chapter on risks") | M |
| FR-R2 | Regenerate only affected slides and re-run only affected gates | M |
| FR-R3 | Version history per deck and per slide, with visual diff | M |
| FR-R4 | Re-import a PPTX the user edited in PowerPoint, preserving manual edits, and learn style preferences from them | V1.1 |
| FR-R5 | Comments on slide previews routed to the refine engine | V1.1 |

### 4.8 Export (FR-E)

| ID | Requirement | Pri |
|---|---|---|
| FR-E1 | PPTX that opens in PowerPoint (Windows and Mac) without repair prompts | M |
| FR-E2 | Native text, tables, charts with embedded data, shapes. No images of text or charts | M |
| FR-E3 | Data input workbook, data request list, sources appendix slide(s), QA report | M |
| FR-E4 | PDF export | M |
| FR-E5 | think-cell adapter (requires customer think-cell licence and Windows render worker) | L |

### 4.9 Enterprise and on-prem (FR-A)

| ID | Requirement | Pri |
|---|---|---|
| FR-A1 | Single-node and Kubernetes installs, offline bundle including model weights | M |
| FR-A2 | No outbound network calls except configured research egress | M |
| FR-A3 | SSO (SAML, OIDC), role-based access, per-tenant isolation | M |
| FR-A4 | Audit log of generations, edits, sources and exports | M |
| FR-A5 | Pluggable model endpoints (self-hosted or customer private cloud) behind one interface | M |
| FR-A6 | Per-tenant adaptation (style learning from the customer's own decks) stays inside the tenant | V1.1 |

---

## 5. Placeholder and data contract

```text
DataItem
  id            d_017
  metric        "India passenger EV sales"
  scope         geography=India, segment=passenger cars
  period        FY2025
  unit          thousand units
  value         89.4
  status        provided | sourced | derived | dummy
  provenance    provided: file, sheet, cell range
                sourced:  URL, publisher, publication date, retrieved date, quoted passage, source tier
                derived:  formula and input item ids
                dummy:    generator note, "ILLUSTRATIVE"
  confidence    0..1 (sourced and provided only)
```

Rules:
1. Slide text references items (`{{d_017}}`, `{{calc:cagr(d_012,d_017)}}`). The compiler formats values using unit and rounding rules.
2. Derived values use explicit formulas, for example $\text{CAGR} = \left(V_{end}/V_{start}\right)^{1/n} - 1$ with $n$ the number of years.
3. A chart with any dummy series carries the ILLUSTRATIVE sticker, a named shape the system can find and remove.
4. Replacing dummy data (workbook upload or PowerPoint edit plus re-import) recomputes derived items, re-checks titles whose claim depends on them, and flags titles that the new data no longer supports.
5. Release states: `draft` (dummy allowed, flagged), `final` (no dummy, all hard gates passed).

---

## 6. Default consulting house style

Quality target: indistinguishable in a blind review from slides produced by top-tier strategy firms. The style is defined by principles, not by copying any firm's trade dress. The product ships no firm's logo, proprietary fonts or templates.

Measurable principles (thresholds calibrated from corpus statistics in TRD 11.3, then reviewed by design lead):

| # | Principle | Check |
|---|---|---|
| P1 | Every content slide has an action title that states the insight | Action-title classifier |
| P2 | One message per slide. The body proves the title and nothing else | Title-body support model |
| P3 | Titles in sequence carry the story (horizontal logic). Bodies follow pyramid order (vertical logic) | Storyline model |
| P4 | Chart type follows the comparison being made | Chart fit rules plus classifier |
| P5 | Highlight colour only on the data that proves the title | Chart rules |
| P6 | Every data slide has a source line and units. Footnotes explain definitions | Lint |
| P7 | Sober palette: one primary, one highlight, greys. No 3D, no gradients, no shadows on data | Lint |
| P8 | Strict grid and alignment. Consistent title, body and footnote positions across slides | Geometry lint |
| P9 | Text density inside calibrated bands (title words, body words, bullets) | Lint |
| P10 | Numbers formatted consistently (units, decimals, currency, period labels) | Lint |
| P11 | Tracker/chapter marker on content slides for decks over about 12 slides | Lint |
| P12 | Executive summary that mirrors the storyline | Storyline model |

References for the principles: B. Minto, *The Pyramid Principle* (Pearson), and G. Zelazny, *Say It With Charts* (McGraw-Hill). Both describe methods, which are not protected the way specific decks are.

---

## 7. Quality definition and success metrics

| Metric | Definition | Pilot target | Measured by |
|---|---|---|---|
| Slide keep rate | Share of generated slides kept with no or minor edits | at least 70% | Expert review on golden set and pilot logs |
| Blind preference | Share of pairwise comparisons where experts rate the generated slide at least equal to a human consulting slide on the same brief | at least 40% at pilot, 60% at GA | Blind pairwise study |
| Storyline approval | Storylines approved with at most 2 edits | at least 60% | Pilot logs |
| Untracked numbers | Numbers in output not linked to a data item | 0 | Hard gate |
| Citation accuracy | Sourced numbers that a human auditor confirms match the cited passage (value, unit, scope, period) | at least 95% | Audit of 200 sampled numbers per release |
| Fabricated sources | Citations to URLs or passages that do not exist | 0 | Audit |
| Critical defect escape rate | Slides passing QA that experts mark with a critical defect | at most 5% | Held-out labelled set |
| Render integrity | Files needing PowerPoint repair on open | 0 | Automated plus manual checks |
| Time to first full draft | Brief approved to complete deck, 20 slides, research on | at most 15 min (reference hardware) | Telemetry |
| Template onboarding time | New customer template to approved archetype gallery | at most 1 working day | Onboarding logs |

---

## 8. Non-goals (v1)

- Free-form creative layouts outside the archetype library.
- Animations, transitions, photo selection, AI image generation.
- Real-time co-editing inside the product (PowerPoint remains the finishing tool).
- Languages other than English.
- Training any shipped model on material without clear commercial rights.

---

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Training data rights. Public firm decks have unknown rights and terms of use that restrict commercial reuse | High | High (legal, product cannot ship) | Clean-room data policy (TRD 11.1). Counsel review before any training. Commissioned and licensed data for shipped models |
| Open-weight models on customer hardware trail frontier models on writing and judgement | Medium | High | Early benchmark against a frontier baseline on non-confidential briefs. Fine-tuning and judges sized to close the gap. Private-cloud model mode as fallback |
| Consulting-grade layout is harder than it looks (text fitting, chart overlays, Mekko) | Medium | High | Compiler spike first (BUILD_PLAN M1). Designer in the loop from week 1 |
| Customer templates are messy (broken layouts, hard-coded positions) | High | Medium | Onboarding tool with synthesised layouts and admin approval |
| Research returns wrong or stale numbers | Medium | High | Verifier, source tiers, cross-checks, dates on every citation, conservative fallback to dummy |
| LibreOffice renders differently from PowerPoint, so QA sees a slightly different slide | Medium | Medium | Bundle fonts. Periodic fidelity checks on a Windows PowerPoint worker. Geometry checks run on the object model, not pixels |
| GPU cost of on-prem deployment deters buyers | Medium | Medium | Two hardware tiers, smaller models for judges, measured sizing in M8 |

---

## 10. Release scope summary

| Area | Pilot (M) | V1.1 | Later |
|---|---|---|---|
| Inputs | Brief, Excel/CSV | PDF/DOCX/PPTX sources | Connectors (SharePoint, Drive) |
| Story | Storyline with checkpoint, exec summary | Storyline variants | Audience-specific re-cuts |
| Visuals | 35 archetypes, chart tiers T1 to T3, frameworks | Icons, more archetypes | think-cell adapter |
| Data | Placeholder contract, workbook round trip, web research | Document-grounded extraction | Live data connectors |
| QA | Rule gates, prompted judges, first trained design model | Full trained QA suite | Continuous learning from edits |
| Brand | Template ingestion, gallery approval | Rule editor, multi-template | Auto-learning from customer decks |
| Refine | Chat refine, partial regeneration, versions | PPTX re-import, comments | |
| Platform | On-prem single node and K8s, SSO, audit | Multi-tenant SaaS option | |

---

## 11. Open items

| ID | Question | Default if no answer |
|---|---|---|
| O1 | Is a model hosted in the customer's own cloud tenancy acceptable as "on-prem", or must everything run on customer GPUs, possibly air-gapped? | Support both. Self-hosted open-weight is the reference |
| O2 | Which slides in the corpus are yours, and who owns the IP (you, a former employer, clients)? | Treated as not cleared for training until confirmed |
| O3 | Team size, budget and target pilot date | 5 FTE, about 8 months to pilot |
| O4 | Can you recruit 3 to 5 ex-consultants for about 500 hours of annotation and golden-set authoring over 6 months? | Required for trained QA models. No good substitute |
| O5 | First customer segment and any design partner in sight | Corporate strategy teams |
| O6 | Typical customer GPU availability | Reference tier: one node with 4 x 80 GB GPUs |
