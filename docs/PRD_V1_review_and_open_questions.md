# PRD V1 review and open questions

Status: draft for discussion, 2026-10-04. Input to PRD V2 and the build plan.
Scope of review: `Presentation_Maker_PRD_V1.md`, corpus manifests under `consulting_corpus/` and `dataset_acquisition/`, research dataset notes under `research_datasets/`. Your own consulting decks are not uploaded yet, so every corpus figure below refers to the public corpus only.

---

## 1. What you asked for (restated)

1. You give an outline.
2. The system produces a consulting-grade deck: storyline, action titles, slide layouts, charts, frameworks, graphics.
3. Where data is not supplied, it leaves clearly marked placeholders for you to fill.
4. You refine iteratively.
5. Quality and style are learned from your McKinsey-type decks.

PRD V1 was written for a different primary workflow (enterprise documents in, fully grounded deck out). Most gaps below follow from that mismatch.

---

## 2. Gaps and corrections in PRD V1

| # | Issue in V1 | Why it matters | Proposed correction |
|---|---|---|---|
| 1 | Primary flow is "ingest documents, extract facts, ground everything". | Your flow is "outline in, ghost deck out, fill data, refine". That is how consulting teams actually work (storyline, ghost deck, dummy charts, data requests). | Make **outline to ghost deck** the core loop. Document ingestion and web research become data-filling modes for placeholders, not the entry point. |
| 2 | No placeholder contract. | Your requirement 3 has no design in V1. Without it, the model will invent numbers to make charts look complete. | Every data element carries a status: `provided`, `sourced` (with citation), or `dummy`. Dummy data renders with an "ILLUSTRATIVE, data required" marker and appears in a generated data request list plus an Excel input workbook. Export as "final" is blocked while any `dummy` remains. |
| 3 | Assumes separate fine-tuned models per actor (story, text, chart, diagram, judge). | Public corpus is 144 files, 6,192 pages, only 2 editable PPTX, and all with `rights_status=unknown`. 130 of the 144 are unclassified and include reports. You have slide outputs only, no (outline, deck) pairs, so there is nothing to supervise directly. | "Learning from the corpus" becomes: (a) mine a closed library of slide archetypes, layout grammars, chart conventions and title style, (b) retrieve exemplars at generation time, (c) calibrate judges. Fine-tuning is phase 3 and happens only if evals show a gap that retrieval cannot close. See section 3. |
| 4 | Ten actors and nine gates in the MVP. | Each LLM hop adds latency, cost and failure surface. Most of the 9 gates can be deterministic checks. | MVP: 4 generation stages, 1 deterministic lint gate, 1 VLM review gate, 1 data-status gate. Add actors only when a measured failure demands it. |
| 5 | Recommends PptxGenJS as the compiler. | PptxGenJS builds files from scratch and cannot open an existing `.pptx`/`.potx`. If you want your own master template, or to re-import your edited deck, it does not work. | Use `python-pptx` with direct OOXML (lxml) for what it lacks. It loads templates and their layouts, and supports native bar, line, pie, doughnut, area, scatter, bubble and radar charts. Decision depends on Q3 and Q4. |
| 6 | Chart scope is "whatever the library supports natively". | Consulting decks rely on charts no PPTX library supports natively: waterfall, Marimekko, Gantt, Harvey balls, 2x2 matrices, bar-plus-CAGR arrows. These are the charts that make a deck read as consulting work. | Build a chart engine with three tiers: native charts, native charts with constructed overlays (for example waterfall as stacked column with an invisible base), and grouped shapes (Mekko, Gantt, Harvey balls). An optional think-cell export path if you use think-cell (Q3). |
| 7 | "Laya-style decision models" was interpreted as a guess ("layered judges"). | If you meant a specific method, the gate design should follow it. | Clarify (Q8). |
| 8 | Weak citations: blogs, DeepWiki pages, 47 hidden footnotes not used in the text. | The PRD itself fails the grounding standard it sets. | V2 cites primary docs only (library docs, papers, dataset cards). |
| 9 | No refinement or UI design. | "And refine" is half your requirement. | Define the interaction loop explicitly (Q9, Q12). |
| 10 | No evaluation golden set built from your own taste. | "High quality" is undefined until it is measured against slides you consider good and bad. | Golden set of your outlines plus target decks, and blind pairwise review (Q13). |
| 11 | No render-and-inspect loop details. | VLM review needs rendered images. LibreOffice headless renders charts and fonts slightly differently from PowerPoint. | Render with LibreOffice for automated checks. Ship your fonts in the container. Do periodic fidelity checks in real PowerPoint. |
| 12 | Animations and AI image generation listed as product features. | Consulting decks rarely use either. Building them early diverts effort from charts and layouts. | Drop from v1 unless you say otherwise (Q11). |
| 13 | Rights treated as a footnote. | Using third-party firm decks to train a model, or reproducing a firm's trade dress, is a legal risk if this becomes a product. | Depends on Q1, Q2, Q18. |

---

## 3. Corpus reality check

Facts from `dataset_acquisition/manifests/files.csv` and `acquisition_report.md`:

| Asset | Size | Structure | Rights | Best use |
|---|---|---|---|---|
| Public consulting corpus | 144 files, 6,192 pages (McKinsey 1,958, BCG 1,329, PwC 1,144, rest under 420 each) | 142 PDF, 2 PPTX. No object trees, no chart data. 130 files unclassified, some are reports | All unknown | Pattern mining: archetypes, title style, chart conventions, density norms. Retrieval exemplars for internal use |
| SlideAudit | 2,400 slide images | Per-slide labels across a design-deficiency taxonomy (layout, typography, colour, imagery), annotator agreement flags, bounding boxes | CC BY 4.0 | Calibrating and measuring the design judge. Domain is general slides, not consulting |
| PPTBench (4 tasks) | 4,240 rows | Detection, understanding, modification, generation tasks | Mostly unclear | Evaluating how well a model edits slides. Little style value |
| Your decks | Not uploaded | Unknown (Q2) | Unknown (Q2) | Primary style source. PPTX would give exact layouts, shape geometry, chart types and data |

Reasoning on fine-tuning (estimate, not measured):
- Supervised fine-tuning needs input and target pairs. The corpus has targets only. Inputs (outlines) would have to be reverse-engineered from slides. That is workable, but it is distillation with synthetic inputs, and its benefit over a frontier model with retrieved exemplars is unproven.
- The parts of "consulting quality" that are rule-like (action titles, one message per slide, source lines, chart hygiene, grid alignment) are cheaper to encode as explicit rules and lint checks than to learn from about 6,000 pages.
- The parts that are taste (which archetype fits a message, density, visual balance) are better served by exemplar retrieval and a pairwise judge trained on your preferences.
- PDFs lose structure. To mine layouts from PDFs we need layout detection (element boxes and types) per page, which adds noise. PPTX originals avoid that step entirely.

---

## 4. Draft direction (changes after your answers)

### 4.1 Representation

```text
Outline (free text)
  -> Storyline       governing thought, SCR or pyramid, chapters, one action title per slide
  -> SlidePlan       per slide: message, archetype id, evidence needed, data blocks
  -> SlideSpec       typed JSON: title, body, chart specs, framework specs, footnotes, data status
  -> Compiler        deterministic python-pptx + OOXML, template-driven
  -> Outputs         PPTX, data input workbook (.xlsx), data request list, preview PNGs
```

The human approves the storyline before any slides are built. That is the cheapest point to fix structural errors.

### 4.2 Stages (MVP)

| Stage | Type | Notes |
|---|---|---|
| S1 Storyline writer | LLM | Outline to storyline. Retrieves storyline exemplars by deck type |
| S2 Slide planner | LLM, constrained | Picks archetypes from a closed library (estimate 30 to 40 archetypes mined from the corpus). Cannot invent free-form layouts |
| S3 Content and chart spec writer | LLM, schema-bound | Writes titles, body, chart specs, data blocks with status |
| S4 Compiler | Deterministic code | No LLM. Same SlideSpec always gives the same PPTX |
| G1 Lint gate | Deterministic | Overflow, minimum font size, grid alignment, contrast, title length, source line present, chart rules (zero baseline on bars, no 3D, no dual axis without labels) |
| G2 Data-status gate | Deterministic | Every number is `provided`, `sourced` or `dummy`. No untagged numbers in text |
| G3 Visual review | VLM on rendered PNG | Rubric from SlideAudit taxonomy plus consulting rules. Writes repair directives to S3 or the compiler. Its accuracy is measured against SlideAudit labels before we rely on it |

Orchestration: a plain state machine is sufficient for this. LangGraph is acceptable if you want its checkpointing and human-interrupt support. It is not a requirement.

### 4.3 Chart engine tiers

| Tier | Charts | Method | Editable in PowerPoint |
|---|---|---|---|
| T1 Native | Clustered and stacked bar/column, line, area, pie/doughnut, scatter, bubble | Native chart XML with embedded data | Yes, data editable |
| T2 Native plus overlay | Waterfall, bar with CAGR arrow, bar with totals, indexed line | Native chart plus shapes | Data editable, overlays need regeneration |
| T3 Shape-built | Marimekko, Gantt, Harvey balls, 2x2 matrix, heat-map tables, timelines | Grouped shapes computed from data | Shapes editable, no data link |

### 4.4 How the corpus is used

1. Page classification: slide vs report page, slide archetype, chart type.
2. Archetype library: canonical geometry per archetype, expressed as template layouts.
3. Style rules: title length distribution, words per slide, number of chart series, footnote and source conventions. Measured from the corpus, then reviewed by you.
4. Exemplar index: for each archetype, a few strong examples retrieved at generation time (internal use only, never copied into output).
5. Judge calibration: SlideAudit for flaw detection, your gold and bad slides for preference.

---

## 5. Open questions

Each question has my default in brackets. If the default is fine, answer "default".

### P0: blocks the architecture

**Q1. Who will use this?** (a) only you, (b) your team or firm internally, (c) a commercial product sold to others. This drives rights exposure, security, multi-user design and how much UI to build.
[Default: (a) now, designed so (b) is possible.]

**Q2. Your own decks.** How many, roughly how many slides, what share is PPTX vs PDF? Are they your own work product, client-confidential, or public? May their content be sent to a cloud LLM API under zero-data-retention terms, or must processing stay on your own machine or cloud?
[Default: cloud API with zero retention. PPTX strongly preferred.]

**Q3. Output target.** Native editable PPTX that you finish in PowerPoint? Google Slides? Do you have think-cell, and do you want think-cell-compatible charts?
[Default: PPTX with native charts. think-cell optional later.]

**Q4. Visual identity.** (a) Your own master template (.potx), (b) a neutral consulting-style house template we design, (c) imitate a specific firm's look. Option (c) is a legal risk beyond personal use.
[Default: (b), plus support for loading any .potx.]

**Q5. Outline format.** Please paste one real outline you would give the system. Is it free bullets, a storyline with action titles already written, or a Word document? Typical deck length (slides)? Audience mix (client steerco, board, internal working session)?
[Default: free-text outline. The system proposes the storyline for your approval. 10 to 30 slides.]

**Q6. Placeholders.** How should missing data appear: (a) realistic dummy data with an "ILLUSTRATIVE" marker, (b) empty chart frame with axis labels and "[Data TBD]", (c) bracket tokens such as `[XX]%`? How will you supply the data: one Excel workbook per deck, pasting into chat, or uploading source files?
[Default: (a) plus a generated Excel input workbook. Re-compile on upload.]

**Q7. Web research and citations in v1.** If the outline says "Indian EV market size", should the system research and cite it, or leave a placeholder?
[Default: placeholder in v1 with an optional "research this block" action. Full research agent with citation verification in v2.]

**Q8. "Laya-style decision models".** What exactly do you mean? A paper, framework, product, or link would settle it.
[No default. V1 guessed "layered judges", which may be wrong.]

### P1: shapes scope and priorities

**Q9. Refinement.** How do you want to refine: chat instructions per slide ("make slide 7 a waterfall"), comments on a rendered preview, or editing in PowerPoint and re-importing so the system learns from your edits?
[Default: chat and preview comments in v1. PowerPoint re-import in v2.]

**Q10. Chart and framework must-haves.** From the T1 to T3 table, which are essential for v1? Anything missing (maps, sankey, tornado, football field, funnel, org chart)?
[Default: bar/column family, line, waterfall, Marimekko, scatter/bubble, Gantt/timeline, Harvey-ball table, 2x2 matrix, process chevrons.]

**Q11. Graphics and motion.** Icons (do you have a licensed set?), diagrams and frameworks, photos, AI-generated images, animations?
[Default: icons and diagrams yes. No AI images, no animations in v1.]

**Q12. Interface.** Web app, command line, PowerPoint add-in, or working through Claude chat?
[Default: simple web app: paste outline, approve storyline, preview slides, refine, download.]

**Q13. Quality bar.** Please pick 15 to 20 slides you consider excellent and 10 you consider weak, once your files are uploaded. How will you judge v1? Suggested: at least 70% of slides kept with only minor edits, and first draft in under 15 minutes for a 20-slide deck.
[Default: those two metrics plus blind pairwise comparison against your own slides.]

**Q14. Budget.** Acceptable LLM cost per deck (for example under USD 5, under USD 20)? Monthly infrastructure budget? Any GPU access for later fine-tuning?
[Default: API-only v1, no GPUs, target under USD 10 per 20-slide deck.]

**Q15. Team and timeline.** Is it you plus Claude Code, or are others involved (frontend, design, annotation)? Target date for a first usable version?
[Default: you plus Claude Code, first usable version in about 6 weeks. To be re-estimated after answers.]

**Q16. Tech constraints.** Preferred language and cloud (AWS, GCP, Azure, Vercel plus Supabase)? Any existing accounts we should use?
[Default: Python backend, Next.js front end, Supabase for storage and auth.]

**Q17. Languages.** English only?
[Default: English only. One corpus deck is Japanese and will be excluded.]

**Q18. Public corpus rights.** The 144 public files have unknown rights. Is it acceptable to use them only for internal pattern analysis and retrieval during development, with no verbatim reuse in outputs and no training of a distributed model?
[Default: yes, internal analysis only.]

**Q19. Upload location for your decks.** This cloud container is ephemeral and the repo deliberately ignores corpus files. Options: (a) a private storage bucket, (b) Google Drive, (c) keep files on your Mac and run processing scripts locally, committing only derived and anonymised artefacts.
[Default: (c) for confidential decks, (a) otherwise.]

---

## 6. Next steps after answers

1. PRD V2: product scope, user flow, placeholder contract, quality metrics.
2. TRD V2: SlideSpec schema, archetype library spec, chart engine spec, gate rubrics, orchestration.
3. Build plan: milestones with exit criteria. A likely first milestone, independent of most answers, is a compiler spike: hand-written SlideSpec JSON to PPTX for 10 archetypes including waterfall and Marimekko, rendered and linted. It de-risks the hardest deterministic piece before any model work.
4. Corpus pipeline: classify, mine archetypes and style statistics, build the exemplar index, run once your decks are available.
