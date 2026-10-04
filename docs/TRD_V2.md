# DeckForge: Technical Requirements Document V2

| Field | Value |
|---|---|
| Status | Draft V2.2, 2026-10-04. No human labelling (D13), generated and fetched imagery (D14) |
| Product scope | `docs/PRD_V2.md` |
| Milestones | `docs/BUILD_PLAN.md` |

Conventions: **[F]** fact with source, **[E]** estimate to be validated, **[D]** design decision, **[O]** opinion.

---

## 1. Design principles

1. **Models plan and judge, code renders.** No model writes PPTX XML or pixel positions. Models emit typed specs and a deterministic compiler builds the file. Same spec, same file. [D]
2. **Numbers by reference.** Models never type factual numbers. They cite data item IDs and the compiler renders values. Hallucinated numbers become structurally impossible rather than something we hope to catch. [D]
3. **Closed vocabularies, open composition.** Components, chart types, annotations, frameworks and repair actions are enumerated. Models compose layouts freely from them on a grid, and a constraint solver owns geometry. Outputs stay checkable and failures attributable without forcing every slide into a fixed template. [D]
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

### 7.2 Slide grammar

Generated decks look bland mostly because of rigid templates and default styling, not because of the language model (7.7). DeckForge separates *what the slide says and how it is composed*, which the model decides, from *exact geometry and drawing*, which code decides.

```text
SlideSpec (model output)
  layout          grid composition of regions with relative weights, e.g. [title] / [chart 8 | sidebar 4] / [footnotes]
  components      per region: chart, table, kpi_stack, text_block, framework, map, icon_row, callout, sticker
  emphasis        which data points or elements carry the answer
  annotations     difference_arrow(i,j), cagr(i,j), average_line, period_band, callout(target), total
  typography      roles only (title, statement, big_number, body, label, footnote). Sizes come from tokens
        |
Constraint layout (kiwisolver, Cassowary algorithm)
  grid snapping, margins, gutters, minimum sizes, measured text heights, reserved zones (sticker, tracker, logo)
        |
Renderer: native charts, tables, shapes and text at absolute positions
```

- Archetypes are stored as grammar templates. The planner starts from the best match and may change regions, components, emphasis and annotations.
- The model never emits coordinates. The solver owns positions and reports infeasible specs as repairable defects (for example "region R needs 2 more lines than available").
- Each style family (consulting report, engagement, keynote) has its own tokens and rules over the same grammar.

#### 7.2.1 Seed archetypes (about 50 after corpus review)

Geometry is expressed in grid units so archetypes adapt to any template's margins and columns.

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
| From corpus review | Split statement with table or list grid, chart with aligned table, composition block with callout, map with callouts and ranked list, two-panel chart with panel titles, chart with big-number sidebar, Likert stacked bars, butterfly bars with delta column, small multiples with focus panel, agenda tracker divider, labelled-row executive summary, ranked priorities with icons, KPI row, comparison table with column highlight |

The seed set is designed by the design lead from consulting conventions and the corpus notes in `docs/corpus_notes/`. Corpus mining (11.3) and reconstruction (11.5) validate and extend it.

### 7.3 Chart engine tiers

| Tier | Charts | Construction | Editable data in PowerPoint |
|---|---|---|---|
| T1 Native | Clustered, stacked and 100% bar/column, line, area, pie, doughnut, scatter, bubble | Native chart XML styled from `DesignSystem` | Yes |
| T2 Native plus overlay | Waterfall (stacked column, invisible base series, connector lines), bar with CAGR arrow, bar with totals, line with end labels | Native chart plus positioned shapes computed from the chart's plot area | Data yes. Overlays regenerate on re-import |
| T3 Shape-built | Marimekko, Gantt, Harvey balls, 2x2 matrix, heat-map table, timeline | Grouped shapes computed from data | Shapes yes, no live data link |

Positioning overlays on native charts needs the plot-area geometry. The compiler fixes plot-area layout explicitly (manual layout in chart XML) so overlay positions are computable rather than guessed.

T3 additions from corpus review: isometric bars and composition blocks (keynote family, height-proportional by construction), marginal abatement cost curve (variable-width bars), highlight maps (public-domain Natural Earth boundaries simplified into editable freeform shapes), butterfly bars with delta column, Likert bars with flag markers.

**think-cell parity checklist (M1 scope):** difference arrows (bar to bar and level), CAGR arrows, totals on stacked charts, series connector lines, category gaps, axis breaks, value and average lines, top-tick units, label collision avoidance, same-scale small multiples, number formatting rules, waterfalls with subtotals, Mekko (percentage and unit), Gantt with milestones, Harvey balls, check marks, agenda and tracker.

**Spec persistence:** the SlideSpec and data are stored inside the PPTX (custom XML part plus role-named shapes). On re-import DeckForge rebuilds overlays from edited chart data, so T2 and T3 visuals follow user edits.

**Evidence:** `spikes/visual_proof/` rebuilt Bain and McKinsey benchmark slides as native objects with computed overlays at near-parity, and its geometry lint caught two real layout collisions on first run.

### 7.3a Implementation status

Consulting exhibits are now shape-built by default (`deckforge/viz/exhibits/`), because native chart rendering cannot place labels, brackets, benchmarks and callouts with the control top-firm exhibits need. Native charts remain available (`deckforge/render/charts.py`) where in-PowerPoint data editing matters more than craft. Each exhibit is selected by `deckforge/viz/select.py` from the analysis message type and the data profile, and the plan report records every candidate with its score and reasons.

### 7.4 Chart rules (deterministic, used by compiler and chart gate)

| # | Rule |
|---|---|
| C1 | Bar and column value axes start at zero |
| C2 | No 3D, gradients or shadows in consulting families. Keynote family allows isometric bars and blocks only with direct value labels and proportional geometry |
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

### 7.7 Why generated decks look bland, and the countermeasures

| Cause | Countermeasure |
|---|---|
| Library defaults (Calibri, Office palette, legends, gridlines, borders) | Token-driven styling of every chart element. A lint rule fails any element left at library default |
| One layout repeated (title plus bullets) | Slide grammar with about 50 archetypes and free composition. QA-1 checks layout variety across the deck |
| Text carries the message instead of evidence | Planner must choose an analysis and visual per message from the framework library. Bullet-only slides capped per deck |
| No emphasis | Mandatory `emphasis` field: answer colour, big-number roles, focus panels |
| No annotation | Annotation layer is part of the spec. QA-3 flags change claims without a difference or CAGR marker |
| Decorative visuals | Icons and flags only as category markers. No stock imagery in consulting families |
| Weak typography | Typography roles with contrast ratios (title to body, big number to body) measured from the corpus |

Supporting evidence: DeepSlides [F7] separates slide design from implementation and trains Qwen-based models for design (SlideQwens). The authors report it beats baselines in human preference, which addresses decks that are "visually dull, compositionally weak". The visual ceiling is set by the design layer and its training, not by the LLM family that writes the content.

### 7.8 Typography and fonts

- Roles: title, subtitle, statement, big_number, body, label, footnote, source. Each role has font, size, weight, colour and leading tokens per family.
- Text fitting uses glyph advances from the real font files (7.5). The spike measures with metric-compatible open fonts (Liberation Sans for Arial, Gelasio for Georgia).
- Default consulting family: bold serif titles, sans body. To avoid font substitution on recipients' machines the default uses fonts present on Windows and macOS Office installs (for example Georgia and Arial), or embeds fonts licensed for embedding through custom OOXML, since python-pptx has no embedding API.
- Customer templates bring their own fonts. Onboarding verifies that the font files are available to compiler and render workers.
- Proprietary firm fonts are never shipped.

### 7.9 Asset pipeline (generate or fetch anything a slide needs)

Decision D14: DeckForge acquires every asset a slide needs by itself, by generating, composing or fetching it, so decks reach the visual standard of the samples (Accenture abstract-light cover and architectural backdrops, BCG photo header bands and side panels, Bain photo with message panel, McKinsey flags and icons).

**Asset resolver.** The planner emits an `AssetNeed` per slide element (type, role, subject, style, constraints). The resolver walks a source chain chosen by asset type and deployment mode, treats each candidate, runs QA, picks the best, and records provenance and licence in an `AssetRecord`. Generated assets are flagged as AI-generated in file metadata and alt text, in line with transparency duties for synthetic content.

| Asset type | Generate or compose | Fetch | Never |
|---|---|---|---|
| Backgrounds, textures, abstract art | Procedural (code), text-to-image | Stock APIs | |
| Photos (places, industries, scenes) | Text-to-image | Stock APIs, customer library | Real identifiable people generated |
| Illustrations, spot art | Text-to-image in flat style | Open illustration sets | |
| Icons | Recolour and resize | Open icon sets: Lucide (ISC), Tabler (MIT), bundled offline | Generating lookalikes of branded icons |
| Flags | | flag-icons (MIT), bundled | Generated flags |
| Maps | Native editable shapes composed from boundaries | Natural Earth (public domain), bundled | Generated maps |
| Company logos (competitor, client, partner slides) | | Official site or Wikimedia, user confirmation required | Generated or altered logos |
| People photos (team slides) | | User-supplied only | Generated portraits of real people |
| Data and numbers | Calc engine | Web research with citations (section 9) | Model-typed numbers |
| Charts, diagrams, frameworks | Native composition (sections 7.2, 7.3) | | Raster charts |
| Fonts | | Open fonts (SIL OFL) bundled, customer fonts from template | Proprietary firm fonts |
| Product or web screenshots | | Headless browser capture in connected mode | |
| Quotes, case examples | | Research with citations | Invented quotes |

**Image roles observed in the corpus:** full-bleed cover, section divider, header band, side panel, photo with overlaid message panel, subtle backdrop under content, case-example photo.

**Sources, in order of preference**

| Source | Use | Licence position | Air-gapped |
|---|---|---|---|
| Procedural, generated by code (gradients, light arcs, rays, meshes, contour lines, particle fields, blurred bokeh) | Covers, dividers, backdrops | Owned by construction | Yes |
| Customer image library | When the tenant supplies one | Customer's | Yes |
| Local text-to-image on open weights: FLUX.2 [klein] 4B (Apache 2.0, runs on a 24 GB consumer GPU), FLUX.1 [schnell] (Apache 2.0) [F8] | Topic scenes, architecture, abstract photography | Apache 2.0 weights | Yes, needs GPU |
| Stock APIs in connected mode: Pexels, Unsplash, Openverse filtered to CC0 and public domain | Real-world photos | Commercial use allowed, provider API rules differ (attribution, download tracking, no hotlinking). Licence metadata stored per asset | No |

Excluded: Qwen-Image 2.1 (Qwen Research License, non-commercial, September 2026), FLUX.1 [dev] (non-commercial licence). The original Qwen-Image release was Apache 2.0 and remains an option.

**Image brief.** The planner writes a structured `ImageBrief`: role, subject, mood, style family, composition constraint expressed as a negative-space mask where text will sit ("left 45% calm, low detail"), palette tokens, forbidden content (logos, text, recognisable people, flags unless requested).

**Deterministic treatment.** This step makes any image look like part of one brand family:
1. Saliency-aware crop that keeps salient mass out of text regions.
2. Colour grading: duotone or tint mapping to brand tokens with luminance preserved. This is why BCG's or Accenture's photos read as a family.
3. Legibility: measure WCAG contrast between text colour and the background region (95th-percentile luminance). Below 4.5:1, apply a gradient scrim, darken or blur the region until it passes.
4. Resolution and size budget: 1920 px wide for full-bleed, JPEG quality about 85.

**Image QA (QA-9)**: relevance (CLIP text-image similarity), aesthetic score (open aesthetic predictor), technical (resolution, blur by Laplacian variance), no text or watermark (OCR), no faces unless requested, legibility contrast, palette distance after grading, no near-duplicates in a deck (perceptual hash).

**Editability.** Pictures are native picture shapes. Scrims are separate semi-transparent shapes. Simple gradients are native gradient fills, everything else is a rendered PNG.

**Hardware [E].** FLUX.2 [klein] 4B fits a 24 GB GPU. A 20-slide deck needs 3 to 8 images. Generation runs on the same node as the judges in the economy tier.

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
| QA-9 Assets | Slide | Relevance, aesthetics, technical quality, no text or watermark, no faces unless requested, legibility contrast, palette fit, duplicates (7.9) | Deterministic checks plus pretrained scorers | Same, thresholds calibrated on corpus imagery | Legibility and licence metadata only |

### 10.2 Training recipes

**QA-5 Layout and design defect classifier**
- Labels: SlideAudit, 2,400 slides labelled across 19 deficiency types in 4 categories (composition and layout, typography, colour, imagery), with annotator-agreement flags and bounding boxes, CC BY 4.0 [F6]. Its slides come from three sources and include controlled alterations (layout, alignment, texture, jitter), 600 each, verified locally.
- Synthetic negatives on our own domain: take good compiled slides, including reconstructed corpus slides (11.5), and inject known defects through the compiler (misalign by k grid units, overflow, mixed fonts, palette breach, clutter by adding elements, low contrast). Ground truth is exact because we created the defect.
- Consulting-specific defects (no action title, legend instead of direct labels, unsourced chart, topic title, missing unit) are injected synthetically, so their labels are exact.
- Model: small VLM with LoRA, multi-label head. Metric: per-label precision and recall, with recall prioritised for critical labels.

**QA-1 Storyline and flow model**
- Positives: title sequences and chapter structures of corpus decks (11.2), which passed the publishing firm's own review.
- Synthetic negatives by perturbation: replace action titles with topic titles ("Market overview"), shuffle within a chapter, drop the complication, drop the recommendation, duplicate a message, insert an off-topic slide, contradict an earlier title.
- Hard negatives: chapters spliced across decks on related topics. Masked-slide prediction (hide one slide, predict its title and archetype from neighbours) as an auxiliary task.
- Model: reward model trained with a Bradley-Terry objective, $P(A \succ B) = \sigma\left(r_\theta(A) - r_\theta(B)\right)$, plus a defect-tag head.

**QA-2 Slide message models**
- Action-title classifier: positives from corpus titles, negatives from the same titles rewritten as topic labels, with numbers removed, or with claims that contradict the slide data. Small LM.
- Title-body support: (title, structured body and chart data) pairs labelled supports / partially / contradicts. Negatives created by swapping bodies across slides and perturbing numbers.

**QA-3 Chart fit**
- Chart-type choice conditioned on message type and data shape, learned from reconstructed corpus charts (11.5). Rules (C1 to C16) veto choices the corpus also contains but that mislead (for example the 3D pie in the BCG sample).

**QA-4 Citation verifier**
- Labels generated by perturbation: take verified (need, passage, value) triples and corrupt unit, period, scope or value to create known errors. Verified positives come from passages where exact-match, unit and period checks all pass and an independent source agrees.

**QA-7 Consulting-grade preference**
- Discriminator pairs: corpus slides (positive) vs DeckForge generations for inverted briefs (negative), logos masked, fonts and aspect ratio normalised so the critic cannot use shortcuts. Retrained every self-play round (11.4).
- Corpus pairs (D9): each reconstructed corpus slide (11.5) preferred over its own content rendered in a generic layout. This yields thousands of pairs without labelling.
- Used for best-of-N selection and as a soft flag. Not a hard gate, because taste models are the least reliable component. [O]

### 10.3 Calibration and policy

1. Each gate threshold is set on a held-out labelled set to meet a target critical false-pass rate (PRD target: at most 5% critical defect escape).
2. Gates report precision and recall per defect type in every release. A gate whose recall on critical defects falls below target is downgraded to "advisory" until fixed.
3. Prompted judges are scored on the same held-out sets as trained models, so the trained versions replace them only when they win.
4. Drift monitoring: synthetic defect suites and SlideAudit re-run on every release. Founder spot-check of 20 slides per milestone as the human anchor (11.4).

### 10.4 Judge reliability controls

- Judges see the rendered image and the spec, so they do not have to guess numbers from pixels.
- Pairwise comparisons are run in both orders to cancel position bias, and only consistent verdicts count.
- Judges never grade their own generation in the same call. Generator and judge prompts are separate, and trained judges are separate models.

---

## 11. Corpus and data program

### 11.1 Data-use policy [D]

Founder decision D9 allows training on the public corpus. Residual risk is accepted and recorded in PRD section 9. Not legal advice.

| Tier | Content | Allowed use | Safeguards |
|---|---|---|---|
| A: owned or licensed | SlideAudit (CC BY 4.0, attribution), our own synthetic and procedural data, Apache-2.0 model outputs | Training, exemplars shipped in product | Attribution file |
| B: public corpus | Public firm decks in `consulting_corpus` and similar | Training (D9), statistics, evaluation | Logos and wordmarks masked before training. No verbatim reuse: outputs checked by n-gram and embedding similarity against the corpus. Provenance log per training example. Machine-readable opt-outs honoured. Files marked permission-required stay excluded |
| C: excluded | Confidential, internal-use-only, permission-required, client material | None | |
| T: tenant data | A customer's own decks inside their deployment | Per-tenant adaptation inside that tenant only | Never pooled |

Several API providers' terms restrict using their outputs to train other models. Synthetic training data should therefore come from permissively licensed open models unless counsel clears otherwise.

### 11.2 Corpus processing pipeline

```text
PPTX -> python-pptx object tree: elements, geometry, text runs, styles, chart XML (type, series, data)
PDF  -> PyMuPDF text spans with boxes and fonts + page render
     -> VLM layout parse: element boxes and roles (title, body, chart, table, framework, footnote, source, tracker)
     -> reconcile VLM boxes with PDF text spans
Both -> page classifier: slide vs report page, archetype, chart types (VLM zero-shot, consistency-checked against reconstruction)
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

### 11.4 Self-supervised data engine (no human labelling)

Decision D13: no annotators are hired. Every training signal comes from the corpus itself, from construction (defects injected with exact labels), from verifiable checks, or from public labelled datasets.

| Signal | Self-supervised source | Why it is valid | Weakness and mitigation |
|---|---|---|---|
| Briefs with reference decks (golden set) | **Deck inversion.** For each corpus deck the generator writes the brief a consultant would have received (topic, audience, data available, what to show), from paraphrased titles with numbers masked. The corpus deck is the reference answer | A brief is a lossy summary of its deck, so brief to deck is well posed and gradeable against the original | Leakage of deck wording. Mitigated by paraphrase, number masking and similarity checks between brief and deck |
| Layout and design defects | Defects injected into compiled and reconstructed slides, plus SlideAudit (2,400 human-labelled slides, CC BY 4.0) | Labels exact by construction. SlideAudit covers natural defects | Synthetic defects may differ from natural ones. SlideAudit is the check |
| Storyline quality | Corpus title sequences as positives. Shuffles, dropped complication, topic titles, duplicates, contradictions and cross-deck splices as negatives. Masked-slide prediction | Published decks passed firm review. Perturbations are known-bad | Corpus is report-style. Engagement-style flow under-represented until your own decks arrive |
| Title quality and title-body support | Corpus titles and their own slide bodies as positives. Topic-label rewrites, removed numbers, swapped bodies and perturbed numbers as negatives | Pairing is known | |
| Chart fit | Chart-type frequency by message type and data shape in reconstructed corpus charts | Top-firm choices are a revealed preference | Imitates habits including bad ones. Chart rules veto |
| Consulting-grade preference | (a) Reconstructed corpus slide over its content in a generic layout. (b) Discriminator: corpus vs generated slides, retrained each round | Corpus is the target distribution | Shortcut learning (fonts, logos, aspect ratio). Mask brand marks, normalise fonts and aspect, inspect attributions |
| Citation correctness | Exact-match passage, unit and period rules, independent-source agreement, perturbation-generated negatives | Verifiable | A wrong number repeated by several sources passes. Source-tier policy limits exposure |
| Image quality | Open aesthetic predictor, CLIP relevance, technical checks, legibility contrast (7.9) | Pretrained on public human ratings | Taste bias. Used as a filter, not as the objective |

**Training loop for the generator without humans**

1. Supervised fine-tuning on reconstructed corpus pairs (11.5) and inverted briefs.
2. Reinforcement learning with verifiable rewards (GRPO-style). Reward $R = \mathbb{1}[\text{hard checks pass}] \cdot \left(\alpha \, s_{\text{critic}} + \beta \, s_{\text{story}} + \gamma \, s_{\text{recon}}\right)$. Hard checks are lint, number tokens, schema validity and solver feasibility. Gating by hard checks means the policy can never trade correctness for style.
3. Self-play: generate, judge, keep the best, retrain the discriminator on the new negatives, repeat. Stop when the discriminator can no longer separate corpus from generated slides on held-out data (accuracy near 50%) while hard checks stay at 100%.

**The one human anchor.** Proxy metrics can be gamed (Goodhart's law). The founder reviews 20 slides and 20 blind pairs per milestone, about one hour. This is the calibration anchor and the stop condition for self-play. No hiring is involved. Without it, the system can drift toward what the critics reward rather than what clients value.

### 11.5 Corpus-to-spec reconstruction (inverse rendering)

The most direct way to make the generator think like top firms is to express corpus slides in DeckForge's own output language and train on that.

```text
corpus page -> VLM parse: regions, components, text, chart type, values read from labels
            -> candidate SlideSpec in the slide grammar
            -> compile and render
            -> compare with original: region layout overlap, text match, perceptual similarity
            -> accept above threshold, else review queue
```

Uses:
1. **Training pairs.** Accepted reconstructions give (message, data) to (archetype, layout, components, emphasis, annotations) pairs for the planner. Deck sequences give storyline examples.
2. **Coverage metric.** The share of corpus content slides the grammar can reconstruct measures its expressiveness. Failures point to missing components. Target at least 70% by M6 [E].
3. **Preference pairs** for QA-7 (10.2).
4. **Style statistics** computed in grammar space (region proportions, density, emphasis use) rather than pixels.

Volume [E]: 6,192 pages. Perhaps 60 to 70% are content slides, and 60 to 80% of those reconstruct on first pass, giving roughly 2,200 to 3,500 slide-level pairs from the public corpus before your own decks.

---

## 12. Generator adaptation ladder

| Level | Method | Entry condition | Exit evidence |
|---|---|---|---|
| L0 | Schema-constrained prompting, retrieved Tier A exemplars, style rules in system prompt | Default | Baseline on golden set |
| L1 | LoRA supervised fine-tuning on reconstructed corpus pairs (11.5) and inverted briefs (11.4): brief to storyline, message and data to SlideSpec. About 2k to 3.5k corpus pairs plus teacher-generated data from Apache-2.0 models [E] | L0 keep rate below target, or gap to frontier baseline above 15 points | Significant keep-rate gain on held-out briefs |
| L2 | RL with verifiable rewards and self-play against the discriminator (11.4). DPO on critic-ranked pairs as a cheaper alternative | After L1, once hard checks pass at 100% on held-out briefs | Discriminator confusion rises, founder blind preference improves |
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
| Golden set | Inverted briefs from held-out corpus decks (11.4) across deck types, with the original deck as reference. 50 by M2, 150 by M6. Never used for training |
| Automatic metrics | Gate pass rates, untracked numbers, render integrity, latency, tokens, GPU seconds |
| Self-supervised metrics | Reconstruction similarity to reference decks, discriminator confusion, storyline model score, verifier re-check pass rate, image QA pass rate |
| Human anchor | Founder review of 20 slides and 20 blind pairs per milestone |
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
| PPTX | python-pptx, lxml, fontTools or Pillow for glyph metrics, kiwisolver for constraint layout |
| Workbooks | openpyxl, pandas |
| Rendering | LibreOffice headless, PyMuPDF |
| Research | Pluggable search adapter, httpx, trafilatura |
| Storage | Postgres 16 with pgvector, MinIO |
| Frontend | Next.js, React |
| Observability | OpenTelemetry, self-hosted tracing for model calls |
| Packaging | Docker images, Helm chart, docker compose for single node, offline bundle |

---

## 17. Framework and analysis knowledge base

Content: `docs/FRAMEWORK_LIBRARY.md` (catalogue, message-type mapping, YAML schema).

| Component | Detail |
|---|---|
| Store | YAML entries under `deckforge/knowledge/frameworks/`, versioned, schema-validated in CI |
| Retrieval | Question-type classifier on the brief plus embedding retrieval over triggers and descriptions |
| Planner integration | Storyline writer receives candidate analyses with data needs and visuals. Chosen analyses become `DataNeed`s and `ChartSpec` defaults |
| Calculations | Each numeric analysis binds to a deterministic, unit-tested calc module (`pvm_bridge`, `cagr`, `synergy_phasing`, `npv_irr`, `oee_waterfall`, `mekko_shares`) |
| Corpus link | Corpus slides tagged with framework ids give frequencies, exemplars and training pairs (11.5) |
| QA link | QA-1 coverage (every brief question has an analysis), QA-3 framework pitfalls |

---

## 18. References

- [F1] Qwen3.5 family: open weights, Apache 2.0, sizes 0.8B to 397B-A17B including 122B-A10B, 35B-A3B, 27B, natively multimodal, released February 2026. [DeepLearning.AI, The Batch](https://www.deeplearning.ai/the-batch/alibabas-latest-flagship-models-are-open-weights-moe-performers-in-sizes-from-less-than-1b-parameters), [Hugging Face Qwen org](https://huggingface.co/Qwen)
- [F2] LangGraph overview. [LangChain docs](https://docs.langchain.com/oss/python/langgraph/overview)
- [F3] python-pptx documentation, charts and templates. [python-pptx.readthedocs.io](https://python-pptx.readthedocs.io/en/latest/user/charts.html)
- [F4] PptxGenJS repository. [github.com/gitbrent/PptxGenJS](https://github.com/gitbrent/PptxGenJS)
- [F5] WCAG 2.2, contrast minimum (success criterion 1.4.3). [w3.org](https://www.w3.org/TR/WCAG22/#contrast-minimum)
- [F6] Zhang, Chen, Zhong, Wobbrock. *SlideAudit: A Dataset and Taxonomy for Automated Evaluation of Presentation Slides.* UIST 2025. [doi:10.1145/3746059.3747736](https://doi.org/10.1145/3746059.3747736). Local copy in `research_datasets/slideaudit/`
- Zheng et al. *PPTAgent: Generating and Evaluating Presentations Beyond Text-to-Slides.* [arXiv:2501.03936](https://arxiv.org/abs/2501.03936). Reference-slide analysis and the PPTEval content, design, coherence dimensions inform QA-1, QA-5 and QA-7
- think-cell JSON data automation (`.ppttc`, `ppttc.exe` on Windows with PowerPoint and think-cell installed). [think-cell manual](https://www.think-cell.com/en/resources/manual/jsondataautomation)
- B. Minto, *The Pyramid Principle*, Pearson. G. Zelazny, *Say It With Charts*, McGraw-Hill
- [F8] FLUX.2 [klein] 4B model card (Apache 2.0), as mirrored on [Hugging Face](https://huggingface.co/YuCollection/FLUX.2-klein-4B-bf16/blob/main/README.md). FLUX.1 [schnell] Apache 2.0. Qwen-Image 2.1 licence change: [Hugging Face discussion](https://huggingface.co/Qwen/Qwen-Image-2.1/discussions/6)
- [F7] Cui et al. *Design First, Code Later: Aesthetically Pleasing Template-Free Slides Generation* (DeepSlides). [arXiv:2605.26451](https://arxiv.org/abs/2605.26451)
- Natural Earth public-domain map data. [naturalearthdata.com](https://www.naturalearthdata.com/)
- kiwisolver (Cassowary constraint solver). [github.com/nucleic/kiwi](https://github.com/nucleic/kiwi)
- Gelasio, SIL Open Font Licence, metric-compatible with Georgia. [github.com/google/fonts](https://github.com/google/fonts/tree/main/ofl/gelasio)
