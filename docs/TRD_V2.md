# DeckForge: Technical Requirements Document V2

| Field | Value |
|---|---|
| Status | Draft V2, 2026-10-04 |
| Product scope | `docs/PRD_V2.md` |
| Milestones | `docs/BUILD_PLAN.md` |

Conventions: **[F]** fact with source, **[E]** estimate to be validated, **[D]** design decision, **[O]** opinion.

---

## 1. Design principles

1. **Models plan and judge, code renders.** No model writes PPTX XML or pixel positions. Models emit typed specs and a deterministic compiler builds the file. Same spec, same file. [D]
2. **Numbers by reference.** Models never type factual numbers. They cite data item IDs and the compiler renders values. Hallucinated numbers become structurally impossible rather than something we hope to catch. [D]
3. **Closed vocabularies.** Archetypes, chart types, frameworks and repair actions are enumerated. Models choose within them. This makes outputs checkable and failures attributable. [D]
4. **Cheap checks first.** Deterministic rules run before any model-based judge. Judges run before any regeneration. [D]
5. **Human checkpoint at the cheapest point.** The storyline is approved before slides are built. [D]
6. **Model-agnostic.** Every model sits behind an OpenAI-compatible endpoint, so a customer can run self-hosted weights or a private cloud endpoint without code changes. [D]

---

## 2. System architecture

```text
                        +---------------------------- Customer environment ----------------------------+
                        |                                                                              |
 Browser (Next.js) ---> | API gateway (FastAPI) ---> Orchestrator workers (LangGraph, Postgres checkpoints)|
                        |      |                          |            |              |                |
                        |      |                          v            v              v                |
                        |      |                    Model gateway   Compiler      Research service     |
                        |      |                    (OpenAI API)    (python-pptx) (search, fetch,      |
                        |      |                      |    |            |          extract, verify)    |
                        |      |                      v    v            v                |             |
                        |      |                 vLLM: generator   Render workers         v             |
                        |      |                 vLLM: judges      (LibreOffice ->   Egress proxy        |
                        |      |                 embeddings         PDF -> PNG)      (allow-list,      |
                        |      |                                                      optional)         |
                        |      v                                                                       |
                        |  Postgres + pgvector (state, data items, QA, audit)   MinIO (files, renders)  |
                        +------------------------------------------------------------------------------+
```

Services:

| Service | Responsibility | Scaling |
|---|---|---|
| API gateway | Auth (SSO), tenancy, REST and websocket for progress | Stateless, horizontal |
| Orchestrator workers | Run deck graphs, checkpoints in Postgres, human interrupts | Horizontal, one graph per job |
| Model gateway | Routing, retries, token budgets, structured output enforcement, logging | Stateless |
| Model servers | vLLM serving generator, judges, embeddings | GPU-bound |
| Compiler | SlideSpec to PPTX, workbook generation, data binding | CPU, horizontal |
| Render workers | PPTX to PDF to PNG via LibreOffice headless | CPU, horizontal, sandboxed |
| Research service | Search adapters, fetching, extraction, verification, cache | Network-bound, egress-controlled |
| Postgres + pgvector | Relational state, vectors for exemplar and source retrieval | Single primary plus replica |
| MinIO | S3-compatible object store for uploads, outputs, renders | Standard |

---

## 3. Model stack and hardware

### 3.1 Roles

| Role | Task | Model class | Reference choice (re-benchmark at M2) |
|---|---|---|---|
| Generator | Brief parsing, storyline, slide planning, content, repair | Large instruction model with strong structured output | Qwen3.5-122B-A10B (MoE, 10B active) [F1] |
| Generator, economy tier | Same, smaller hardware | Medium MoE | Qwen3.5-35B-A3B [F1] |
| Visual judge | Rendered slide review, corpus layout parsing | Vision-language model | Same Qwen3.5 model. The family is natively multimodal [F1], so one server can serve text and vision |
| Trained gate models | Design defect classifier, action-title classifier, reward models | Small VLM or LM fine-tuned | Qwen3.5-4B or 9B with LoRA [F1] [E] |
| Embeddings | Exemplar and source retrieval | Open embedding model | Any permissively licensed embedding model, chosen by retrieval eval |
| Teacher for synthetic data | Generate training pairs | Largest permissive open model | Qwen3.5-397B-A17B [F1], run on rented GPUs during training only |

Licence: the Qwen3.5 family is released under Apache 2.0, which permits commercial use and fine-tuning [F1]. Model choice is not locked. Section 1, principle 6 keeps it swappable.

### 3.2 Hardware tiers [E]

Weights in FP8 take about 1 byte per parameter. KV cache and concurrency need headroom on top.

| Tier | Generator | GPUs | Approximate weights | Concurrent decks |
|---|---|---|---|---|
| Economy | 35B-A3B FP8 plus 4B judges | 1 x 80 GB | about 35 GB plus about 8 GB | 2 to 4 |
| Reference | 122B-A10B FP8 plus 9B judges | 4 x 80 GB | about 122 GB plus about 18 GB | 4 to 8 |
| Large | Reference plus best-of-N variants | 8 x 80 GB | as above, replicated | 10+ |

All figures are planning estimates. M8 produces measured sizing.

### 3.3 Token budget per 20-slide deck [E]

| Stage | Calls | Input tokens | Output tokens |
|---|---|---|---|
| Brief and storyline | 3 | 30k | 6k |
| Slide planning and content | 20 x 2 | 300k | 40k |
| Judges (text and vision, 2 passes) | 20 x 4 x 2 | 640k | 50k |
| Repairs (about 30% of slides) | 12 | 90k | 15k |
| Research (10 data needs) | about 40 | 400k | 20k |
| **Total** | | **about 1.5M** | **about 130k** |

Decode dominates wall clock. At an assumed 40 tokens per second per stream and 8 parallel slide streams, 130k output tokens take about 7 minutes, which fits the 15-minute target in PRD section 7. Measure in M2.

---

## 4. Core data contracts

All inter-stage objects are Pydantic v2 models, versioned, stored in Postgres. Model outputs are constrained to these schemas with vLLM structured outputs (JSON schema guided decoding).

### 4.1 Object list

| Object | Produced by | Consumed by |
|---|---|---|
| `DeckBrief` | Brief parser | Storyline, research planner |
| `DataTable` | Upload profiler | Data binder |
| `DataNeed` | Storyline (data plan) | Data binder, research, dummy generator |
| `DataItem` | Binder, research, calc engine, dummy generator | Content writer, compiler, QA |
| `Storyline` | Storyline writer | Human checkpoint, slide planner, flow gate |
| `SlidePlan` | Slide planner | Content writer |
| `SlideSpec` | Content writer | Compiler, QA |
| `ChartSpec`, `FrameworkSpec`, `TableSpec` | Content writer | Compiler, chart gate |
| `DesignSystem` | Template ingestion | Compiler, conformance gate |
| `GateVerdict` | Each gate | Router, QA report |

### 4.2 Key schemas (abridged)

```python
class DataItem(BaseModel):
    id: str                                  # "d_017"
    metric: str
    scope: dict[str, str]                    # {"geography": "India", "segment": "passenger cars"}
    period: str                              # "FY2025"
    unit: str                                # "thousand units"
    value: float | None
    status: Literal["provided", "sourced", "derived", "dummy"]
    provenance: Provided | Sourced | Derived | Dummy
    confidence: float | None

class Sourced(BaseModel):
    url: HttpUrl
    publisher: str
    published: date | None
    retrieved: datetime
    passage: str                             # verbatim text containing the value
    tier: Literal[1, 2, 3, 4]                # section 9.3
    corroborating: list[str] = []            # other DataItem ids from independent sources

class Derived(BaseModel):
    formula: Literal["cagr", "share", "delta", "delta_pct", "bps", "index", "sum", "mean"]
    inputs: list[str]                        # DataItem ids

class SlideSpec(BaseModel):
    slide_id: str
    archetype: ArchetypeId                   # closed enum, section 7.2
    title: str                               # may contain {{d_017}} or {{calc:cagr(d_012,d_017)}}
    slots: dict[str, SlotContent]            # archetype-defined slot names
    footnotes: list[str]
    source_line: str | None                  # generated from provenance, not written by the model
    tracker: str | None
    notes: str | None                        # speaker notes
    data_refs: list[str]                     # every DataItem used

class ChartSpec(BaseModel):
    chart_type: ChartType                    # closed enum, section 7.3
    message_type: Literal["component", "item", "time_series", "frequency",
                          "correlation", "bridge", "schedule", "assessment", "prioritisation"]
    categories: list[str]
    series: list[SeriesRef]                  # each point references a DataItem id
    highlight: list[PointRef]                # points that prove the title
    annotations: list[Annotation]            # CAGR arrows, totals, callouts
    axis: AxisSpec
    number_format: str

class GateVerdict(BaseModel):
    gate: GateId
    scope: Literal["deck", "slide", "element"]
    target_id: str
    passed: bool
    score: float | None
    severity: Literal["critical", "major", "minor"]
    defects: list[Defect]                    # code, message, element ref, evidence
    repair_target: RepairNode | None
```

### 4.3 Number-token mechanism

1. The content writer emits text with tokens: `Passenger EV sales grew {{calc:cagr(d_012,d_017)}} p.a. to {{d_017}}`.
2. The calc engine evaluates derived values. CAGR: $\left(V_{end}/V_{start}\right)^{1/n} - 1$. Basis-point change: $10^4 \times (r_{t} - r_{t-1})$ where rates are fractions.
3. The formatter applies unit, rounding and locale rules from the `DesignSystem` (for example "89k units", "24%").
4. A lint pass scans final text for digits not produced by a token. Allowed exceptions: years 1900 to 2100 in period labels, list numbering, and numbers inside quoted proper names. Anything else is a critical defect.

---

## 5. Orchestration (LangGraph)

LangGraph is chosen for persisted state, human-in-the-loop interrupts, conditional routing and parallel fan-out, and because it is MIT-licensed and runs fully on-prem [F2]. Nodes stay thin. Most logic lives in plain, testable Python functions.

### 5.1 Graph

```text
START
 -> parse_brief -> profile_uploads -> clarify? --(interrupt: user answers)--> plan_storyline
 -> flow_gate --fail--> plan_storyline (max 2)
 -> CHECKPOINT storyline (interrupt: user approves/edits)
 -> plan_data -> [bind_user_data | research | make_dummy] (parallel per DataNeed) -> calc_derived
 -> fan-out per slide (Send):
       plan_slide -> write_content -> compile_slide -> render_slide
       -> slide_gates (lint, data, chart, message, design, conformance)
       -> route: pass -> done | repair(target node, max 2) | flag_for_human
 -> fan-in -> assemble_deck -> deck_gates (flow, consistency, exec-summary alignment)
 -> route: pass -> export | deck_repair (max 1) | flag
 -> export (PPTX, workbook, data request list, sources appendix, QA report)
END
```

### 5.2 Routing and budgets

| Rule | Value [D] |
|---|---|
| Max repair attempts per slide | 2, then flag for human |
| Max storyline regenerations before checkpoint | 2 |
| Deck-level repair passes | 1 (minimal edits, never full regeneration) |
| Best-of-N layout variants | N=1 default, N=3 for exec summary and key chart slides on the Large tier |
| Refine requests | Re-enter the graph at the lowest affected node for affected slides only |

### 5.3 Repair routing

| Defect family | Repair node |
|---|---|
| Title not an action title, too long, unsupported by body | `write_content` (title only) |
| Wrong chart type for message, too many series | `plan_slide` |
| Text overflow | `write_content` with exact character budget, then compiler font step-down within minimum size |
| Untracked number, failed citation, inconsistent value | `plan_data` for that item, then `write_content` |
| Geometry, alignment, conformance | `compile_slide` (deterministic fix) |
| Flow, redundancy, missing step | `deck_repair` (insert, merge, reorder, retitle) |

---

## 6. Brief intake and data binding

1. `parse_brief`: free text to `DeckBrief` (objective, audience, decision sought, scope, constraints, must-show items, length).
2. `profile_uploads`: for each sheet or CSV, detect header rows, units, period columns, granularity, totals rows. Output `DataTable` with column semantics.
3. `plan_data` (inside storyline): every slide lists `DataNeed`s with metric, scope, period, unit, priority, and preferred source (`user`, `research`, `dummy`).
4. `bind_user_data`: match needs to columns by semantic similarity plus unit and period compatibility. Ambiguous matches go to the user as one batched confirmation.
5. `make_dummy`: plausible magnitudes and shapes. Uses researched anchors when available (for example a known market total), otherwise generic priors. Values are rounded to avoid false precision.

---

## 7. Compiler, archetypes and chart engine

### 7.1 Library choice

`python-pptx` plus direct OOXML editing through lxml [D]. Reasons:
- It opens existing `.pptx` and `.potx` files and uses their masters and layouts, which customer templates require [F3].
- It writes native charts with embedded workbooks for bar, column, line, pie, doughnut, area, scatter, bubble and radar types [F3].
- PptxGenJS, recommended in V1, creates presentations from scratch and does not read existing files [F4], so it cannot use customer templates.

Charts no library supports natively (waterfall, Mekko, Gantt, Harvey balls) are built as tiered constructions (7.3).

### 7.2 Archetype library (about 35)

Each archetype is a parametric definition: grid regions, slot schema, per-slot text budgets, allowed chart types, and rendering function. Geometry is expressed in grid units so it adapts to any template's margins and columns.

| Group | Archetypes |
|---|---|
| Structure | Title, Agenda/tracker, Section divider, Executive summary, Key takeaways |
| Single chart | Chart with takeaway box, Full-width chart with callouts, Chart with KPI row |
| Multi chart | Two charts, Three small multiples, Chart plus table |
| Specialised charts | Waterfall bridge, Marimekko market map, Scatter/bubble positioning, Ranked bar with benchmark, Time series with CAGR |
| Tables | Options vs criteria, Harvey-ball assessment, RAG status, Financial summary |
| Frameworks | 2x2 matrix, Process chevrons (3 to 6), Pillars (3 to 5), Issue/driver tree, Value chain, Hierarchy, Hub and spoke |
| Plans | Gantt roadmap, Milestone timeline, Next steps (owner, date), Phased waves |
| Qualitative | Interview insights grid, Case example (situation, action, result), KPI dashboard, Org/governance chart |
| Back matter | Sources and methodology |

The initial set is designed by the design lead from consulting conventions. Corpus mining (11.3) validates and adjusts it.

### 7.3 Chart engine tiers

| Tier | Charts | Construction | Editable data in PowerPoint |
|---|---|---|---|
| T1 Native | Clustered, stacked and 100% bar/column, line, area, pie, doughnut, scatter, bubble | Native chart XML styled from `DesignSystem` | Yes |
| T2 Native plus overlay | Waterfall (stacked column, invisible base series, connector lines), bar with CAGR arrow, bar with totals, line with end labels | Native chart plus positioned shapes computed from the chart's plot area | Data yes. Overlays regenerate on re-import |
| T3 Shape-built | Marimekko, Gantt, Harvey balls, 2x2 matrix, heat-map table, timeline | Grouped shapes computed from data | Shapes yes, no live data link |

Positioning overlays on native charts needs the plot-area geometry. The compiler fixes plot-area layout explicitly (manual layout in chart XML) so overlay positions are computable rather than guessed.

### 7.4 Chart rules (deterministic, used by compiler and chart gate)

| # | Rule |
|---|---|
| C1 | Bar and column value axes start at zero |
| C2 | No 3D, no gradients, no shadows |
| C3 | Item comparisons sorted descending unless order is natural (time, size bands) |
| C4 | Pie only for at most 5 components summing to 100%. Otherwise 100% bar |
| C5 | Line charts at most 5 series. Column time series at most about 12 periods, else line |
| C6 | Direct labels instead of legends when at most 4 series |
| C7 | Long category labels force horizontal bars, never rotated text |
| C8 | Units in chart title or axis. Period labels consistent across the deck |
| C9 | Highlight colour only on points listed in `highlight` |
| C10 | Same series means same colour across the deck |
| C11 | Dual axes only with distinct units, both labelled |
| C12 | Stacked charts at most 5 segments. 100% stacks sum to 100 within rounding |
| C13 | Waterfall start, end and subtotal bars visually distinct. Negative steps labelled with sign |
| C14 | Gridlines none or light grey |
| C15 | Number format consistent within a chart (decimals, units, currency) |
| C16 | Source line present on every chart slide |

### 7.5 Text fitting

Each slot has a box size. The compiler computes wrapped line count and height from font metrics (fontTools) for the template's actual fonts. The planner passes a character budget per slot to the writer up front. On overflow the compiler first steps the font down within the template minimum. If it still overflows, it routes back to the writer with the exact excess. Fonts used by templates must be installed in compiler and render images.

### 7.6 Outputs

| Artefact | Detail |
|---|---|
| PPTX | Native objects. Every generated shape named by role (`DF_title`, `DF_chart_1`, `DF_ILLUSTRATIVE_1`) so re-import can identify them |
| Data workbook | openpyxl. One sheet per chart, named ranges, status column, instructions sheet |
| Data request list | Every dummy item, grouped by owner if given |
| Sources appendix | Generated slides listing all sourced items with publisher, date, URL |
| QA report | JSON plus a readable summary |

---

## 8. Template ingestion (brand onboarding)

1. Parse the template: slide masters, layouts, placeholders (type, index, geometry), theme colours, major and minor fonts, background, footers.
2. Analyse sample slides if present: title size and position, body sizes, margins, recurring elements (logo, confidentiality marker, page number, tracker, source line), and chart XML styling (colours, gridlines, label fonts).
3. Derive grid: columns and gutters estimated from placeholder edges across layouts.
4. Produce `DesignSystem` JSON: tokens, layout map, mandatory elements, chart style.
5. Map archetypes to layouts by placeholder compatibility. Where none fits, synthesise the archetype on a blank layout using grid tokens.
6. Render the full archetype gallery with sample content in the customer template.
7. Admin reviews, adjusts tokens or mappings, approves. Approval freezes a versioned `DesignSystem`.
8. Conformance rules (fonts, palette, positions, mandatory elements) are auto-generated from the frozen `DesignSystem`.

---

## 9. Research and grounding

### 9.1 Flow

```text
DataNeed -> query planner (2 to 4 queries) -> search adapter -> fetch (allow-listed egress)
 -> extract main text (trafilatura) and tables -> candidate values with passage
 -> verifier -> source tier -> cross-check -> DataItem(status="sourced") or fallback to dummy
```

### 9.2 Verifier checks

| Check | Method |
|---|---|
| Value present in passage | Deterministic numeric match after unit normalisation |
| Scope, period and unit match the need | LLM structured comparison with strict schema, then rule checks on extracted fields |
| Passage exists at URL | Stored snapshot hash, re-fetch on audit |
| Date freshness | Flag if older than the need's tolerance (default 3 years for market data) |

### 9.3 Source tiers

| Tier | Examples | Policy |
|---|---|---|
| 1 | Government statistics, central banks, IMF, World Bank, OECD, regulators, audited company filings | Single source acceptable |
| 2 | Industry associations, established research firms, peer-reviewed papers | Single source acceptable, flagged |
| 3 | Reputable press quoting a primary source | Prefer the primary source. Accept only with corroboration |
| 4 | Blogs, aggregators, SEO pages, undated content | Rejected for headline numbers |

### 9.4 Conflicts

If independent sources disagree by more than a tolerance (default 10%), the item carries both values, the slide uses the higher-tier source, and the footnote states the range. The QA report lists the conflict.

### 9.5 Deployment modes

| Mode | Behaviour |
|---|---|
| Connected | Customer-provided search API or self-hosted metasearch, egress through allow-list proxy |
| Restricted | Only allow-listed domains (for example statistics agencies) |
| Air-gapped | Research disabled. Data needs default to dummy. Customer internal document sources only (V1.1) |

---

## 10. QA decision models

This is the subsystem that enforces top-consulting quality. Each gate is a layered stack: deterministic rules first, then a trained or prompted model, then calibrated thresholds.

### 10.1 Gate catalogue

| Gate | Scope | Checks | Method v1 (pilot) | Method v2 (trained) | Blocks final export |
|---|---|---|---|---|---|
| QA-1 Storyline and flow | Deck | Governing thought, SCR completeness, horizontal logic, MECE chapters, redundancy, ordering, exec-summary alignment | Rubric-prompted generator model | Pairwise reward model plus defect classifier | Critical only |
| QA-2 Slide message | Slide | Action-title test, one message, body supports title, title length | Rules plus prompted judge | Action-title classifier, title-body support model (entailment-style) | No (soft) |
| QA-3 Chart integrity and fit | Element | Rules C1 to C16, chart type vs message type, highlight matches title claim | Rules plus prompted judge | Chart-fit classifier | C1, C9, C16 violations |
| QA-4 Factuality and provenance | Element, deck | Untracked numbers, calc correctness, cross-slide consistency, citation verification, unit and period coherence | Deterministic plus verifier | Verifier fine-tuned on audit labels | Yes |
| QA-5 Layout and design | Slide | Overlap, overflow, margins, grid alignment, minimum font size, contrast at least 4.5:1 for body text [F5], density bands, visual hierarchy, balance | Geometry lint on object model plus prompted VLM on render | Multi-label VLM defect classifier | Critical lint defects |
| QA-6 Template conformance | Slide | Fonts, palette, positions, mandatory elements vs `DesignSystem` | Deterministic | Deterministic | Yes |
| QA-7 Consulting-grade preference | Slide, deck | Overall "would a top-firm engagement manager accept this slide" | Prompted pairwise VLM judge against retrieved exemplars | Pairwise reward model on render plus spec | No (ranks variants, flags low scorers) |
| QA-8 Data status | Deck | Remaining dummy data | Deterministic | Deterministic | Yes (final only) |

### 10.2 Training recipes

**QA-5 Layout and design defect classifier**
- Labels: SlideAudit, 2,400 slides labelled across 19 deficiency types in 4 categories (composition and layout, typography, colour, imagery), with annotator-agreement flags and bounding boxes, CC BY 4.0 [F6]. Its slides come from three sources and include controlled alterations (layout, alignment, texture, jitter), 600 each, verified locally.
- Synthetic negatives on our own domain: take good compiled slides and inject known defects through the compiler (misalign by k grid units, overflow, mixed fonts, palette breach, clutter by adding elements, low contrast). Ground truth is exact because we created the defect.
- Expert labels: about 3,000 rendered slides labelled by ex-consultants with the same taxonomy plus consulting-specific defects (no action title, legend instead of direct labels, unsourced chart).
- Model: small VLM with LoRA, multi-label head. Metric: per-label precision and recall, with recall prioritised for critical labels.

**QA-1 Storyline and flow model**
- Positives: storylines (ordered action titles plus chapters) written by contracted ex-consultants for golden-set briefs, plus the system's storylines that experts approved.
- Synthetic negatives by perturbation: replace action titles with topic titles ("Market overview"), shuffle within a chapter, drop the complication, drop the recommendation, duplicate a message, insert an off-topic slide, contradict an earlier title.
- Expert pairwise labels on generated storyline variants.
- Model: reward model trained with a Bradley-Terry objective, $P(A \succ B) = \sigma\left(r_\theta(A) - r_\theta(B)\right)$, plus a defect-tag head.

**QA-2 Slide message models**
- Action-title classifier: positives from expert-written titles, negatives from topic titles and degraded titles. Small LM.
- Title-body support: (title, structured body and chart data) pairs labelled supports / partially / contradicts. Negatives created by swapping bodies across slides and perturbing numbers.

**QA-3 Chart fit**
- Training pairs of (message type, data shape, chart type) labelled appropriate or not. Seeded from Zelazny-style rules, expanded with expert labels on generated charts.

**QA-4 Citation verifier**
- Labels from the citation audit process (PRD metric "citation accuracy"): (need, passage, extracted value) marked correct or with error type (wrong unit, wrong period, wrong scope, value absent).

**QA-7 Consulting-grade preference**
- Expert pairwise comparisons of slide renders for the same message: generated vs generated, generated vs expert-made.
- Weak pairs: expert-made slides preferred over the same content in a generic layout.
- Used for best-of-N selection and as a soft flag. Not a hard gate, because taste models are the least reliable component. [O]

### 10.3 Calibration and policy

1. Each gate threshold is set on a held-out labelled set to meet a target critical false-pass rate (PRD target: at most 5% critical defect escape).
2. Gates report precision and recall per defect type in every release. A gate whose recall on critical defects falls below target is downgraded to "advisory" until fixed.
3. Prompted judges are scored on the same held-out sets as trained models, so the trained versions replace them only when they win.
4. Drift monitoring: weekly sample of production slides re-labelled by experts. Disagreement rate tracked per gate.

### 10.4 Judge reliability controls

- Judges see the rendered image and the spec, so they do not have to guess numbers from pixels.
- Pairwise comparisons are run in both orders to cancel position bias, and only consistent verdicts count.
- Judges never grade their own generation in the same call. Generator and judge prompts are separate, and trained judges are separate models.

---

## 11. Corpus and data program

### 11.1 Clean-room data policy [D]

Not legal advice. To be reviewed by IP counsel before any training run.

| Tier | Content | Allowed use |
|---|---|---|
| A: owned or licensed | Decks and storylines commissioned from contracted ex-consultants on public topics with IP assignment, SlideAudit (CC BY 4.0, attribution required), data generated by our own pipeline or by Apache-2.0 open models, licensed datasets | Training shipped models, exemplars shipped in product |
| B: public, rights unknown | The 144 public firm decks in `consulting_corpus`, PPTBench and similar | Internal analysis and statistics, evaluation, only after counsel review. Never in shipped weights, never shown or copied in output |
| C: excluded | Anything marked confidential or permission-required, client material, former-employer material without written clearance | No use |
| T: tenant data | A customer's own decks inside their deployment | Per-tenant adaptation inside that tenant only. Never pooled |

Several API providers' terms restrict using their outputs to train other models. Synthetic training data should therefore come from permissively licensed open models unless counsel clears otherwise.

### 11.2 Corpus processing pipeline

```text
PPTX -> python-pptx object tree: elements, geometry, text runs, styles, chart XML (type, series, data)
PDF  -> PyMuPDF text spans with boxes and fonts + page render
     -> VLM layout parse: element boxes and roles (title, body, chart, table, framework, footnote, source, tracker)
     -> reconcile VLM boxes with PDF text spans
Both -> page classifier: slide vs report page, archetype, chart types, quality tier (expert-verified sample)
     -> normalised slide records (16:9 coordinates, roles, text stats)
```

Corpus facts today: 144 public files, 6,192 pages, 142 PDF and 2 PPTX, 130 files not yet classified (from `dataset_acquisition/manifests/files.csv`).

### 11.3 What the corpus produces

| Output | Method | Consumer |
|---|---|---|
| Archetype validation | Cluster normalised region layouts, compare clusters with the designed library, add missing archetypes | Archetype library |
| Style statistics | Distributions of title words, body words, element counts, font-size ratios, whitespace share, colour count, series count. P10 to P90 bands | Lint thresholds, density rules |
| Chart usage | Frequency of chart types by message type | Chart-fit priors |
| Exemplar index | Embeddings of Tier A slides by archetype and message type | Retrieval at generation time, QA-7 references |

### 11.4 Annotation program [E]

| Work | Volume | Time per unit | Hours |
|---|---|---|---|
| Golden-set briefs with reference storyline and 5 key slides | 100 briefs | 2.5 h | 250 |
| Slide defect labels | 3,000 slides | 2 min | 100 |
| Pairwise preferences (slides and storylines) | 5,000 pairs | 1 min | 85 |
| Citation audits | 1,000 numbers | 2 min | 35 |
| **Total** | | | **about 470 h** |

Annotators: 3 to 5 ex-consultants. Quality: 15% overlap, target Cohen's kappa at least 0.6 per label family. Labels with lower agreement are merged or dropped.

---

## 12. Generator adaptation ladder

| Level | Method | Entry condition | Exit evidence |
|---|---|---|---|
| L0 | Schema-constrained prompting, retrieved Tier A exemplars, style rules in system prompt | Default | Baseline on golden set |
| L1 | LoRA supervised fine-tuning on Tier A pairs: brief to storyline, slide plan to SlideSpec. 2k to 5k pairs [E] from commissioned work plus teacher-generated and expert-filtered data | L0 keep rate below target, or gap to frontier baseline above 15 points | Significant keep-rate gain on held-out briefs |
| L2 | Preference optimisation (DPO) on expert and pilot-user chosen vs rejected outputs | After pilot, with at least 2k preference pairs | Gain in blind preference win rate |
| L3 | Per-tenant LoRA from the customer's own decks and edits | V1.1, customer opt-in | Tenant keep-rate gain |

Frontier baseline: run a top proprietary model on the non-confidential golden briefs once per milestone to measure the quality gap of the on-prem stack. This uses only Tier A briefs and never customer data.

---

## 13. Rendering and fidelity

- Render: LibreOffice headless converts PPTX to PDF, PyMuPDF rasterises at 150 dpi for judges.
- Geometry checks use the compiled object model, not pixels, so they are exact regardless of renderer.
- Fidelity worker (optional, weekly in CI): Windows VM with PowerPoint exports the same decks. Structural similarity between PowerPoint and LibreOffice renders is tracked. Large divergence blocks a release.
- Open-without-repair test: every CI build opens a sample deck set in PowerPoint (Windows and Mac runners) and fails on repair prompts.

---

## 14. Evaluation harness

| Component | Detail |
|---|---|
| Golden set | 100 briefs across deck types (market entry, growth strategy, cost reduction, due diligence, operating model, board update) with reference storyline and key slides. 20 by M0, 100 by M6 |
| Automatic metrics | Gate pass rates, untracked numbers, render integrity, latency, tokens, GPU seconds |
| Expert metrics | Keep rate, blind pairwise preference, storyline approval, citation audit |
| Regression CI | Every merge runs 20 briefs on the economy tier. Weekly full run on reference tier |
| Dashboards | Per-gate precision and recall, defect distributions, cost per deck |

---

## 15. Security and enterprise

| Area | Requirement |
|---|---|
| Isolation | Per-tenant schemas and buckets. Tenant id on every row and object key |
| Encryption | TLS in transit. At rest via MinIO server-side encryption and encrypted volumes |
| Identity | SAML and OIDC SSO, SCIM provisioning (V1.1), roles: author, reviewer, brand admin, system admin |
| Egress | Default deny. Research through allow-list proxy only. No telemetry leaves the site |
| Supply chain | Signed container images, SBOM, pinned model weight hashes, offline update bundles |
| Audit | Immutable log of prompts, outputs, sources, exports, admin changes, retained per customer policy |
| Sandboxing | Uploaded Office files parsed in isolated workers. LibreOffice runs without network |

---

## 16. Technology stack

| Layer | Choice |
|---|---|
| Language | Python 3.12 (backend, ML), TypeScript (frontend) |
| API | FastAPI, Pydantic v2 |
| Orchestration | LangGraph with Postgres checkpointer |
| Model serving | vLLM with OpenAI-compatible API and JSON-schema guided decoding |
| Training | PyTorch, Hugging Face Transformers, PEFT (LoRA), TRL (SFT, reward modelling, DPO) |
| PPTX | python-pptx, lxml, fontTools |
| Workbooks | openpyxl, pandas |
| Rendering | LibreOffice headless, PyMuPDF |
| Research | Pluggable search adapter, httpx, trafilatura |
| Storage | Postgres 16 with pgvector, MinIO |
| Frontend | Next.js, React |
| Observability | OpenTelemetry, self-hosted tracing for model calls |
| Packaging | Docker images, Helm chart, docker compose for single node, offline bundle |

---

## 17. References

- [F1] Qwen3.5 family: open weights, Apache 2.0, sizes 0.8B to 397B-A17B including 122B-A10B, 35B-A3B, 27B, natively multimodal, released February 2026. [DeepLearning.AI, The Batch](https://www.deeplearning.ai/the-batch/alibabas-latest-flagship-models-are-open-weights-moe-performers-in-sizes-from-less-than-1b-parameters), [Hugging Face Qwen org](https://huggingface.co/Qwen)
- [F2] LangGraph overview. [LangChain docs](https://docs.langchain.com/oss/python/langgraph/overview)
- [F3] python-pptx documentation, charts and templates. [python-pptx.readthedocs.io](https://python-pptx.readthedocs.io/en/latest/user/charts.html)
- [F4] PptxGenJS repository. [github.com/gitbrent/PptxGenJS](https://github.com/gitbrent/PptxGenJS)
- [F5] WCAG 2.2, contrast minimum (success criterion 1.4.3). [w3.org](https://www.w3.org/TR/WCAG22/#contrast-minimum)
- [F6] Zhang, Chen, Zhong, Wobbrock. *SlideAudit: A Dataset and Taxonomy for Automated Evaluation of Presentation Slides.* UIST 2025. [doi:10.1145/3746059.3747736](https://doi.org/10.1145/3746059.3747736). Local copy in `research_datasets/slideaudit/`
- Zheng et al. *PPTAgent: Generating and Evaluating Presentations Beyond Text-to-Slides.* [arXiv:2501.03936](https://arxiv.org/abs/2501.03936). Reference-slide analysis and the PPTEval content, design, coherence dimensions inform QA-1, QA-5 and QA-7
- think-cell JSON data automation (`.ppttc`, `ppttc.exe` on Windows with PowerPoint and think-cell installed). [think-cell manual](https://www.think-cell.com/en/resources/manual/jsondataautomation)
- B. Minto, *The Pyramid Principle*, Pearson. G. Zelazny, *Say It With Charts*, McGraw-Hill
