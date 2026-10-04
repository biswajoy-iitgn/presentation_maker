# DeckForge: Framework and Analysis Library V1

| Field | Value |
|---|---|
| Status | Seed catalogue, 2026-10-04 |
| Used by | Storyline planner, slide planner, chart selection, QA-1 and QA-3 (TRD section 17) |
| Machine form | One YAML file per entry under `deckforge/knowledge/frameworks/` (schema in section 3) |

Consultants do not start from a chart. They start from a question, choose the analysis that answers it, and the analysis dictates the data and the visual. This library encodes that chain so the model can do the same:

```text
Business question -> question type -> candidate analyses -> data needs -> canonical visual -> archetype -> title pattern
```

Knowing framework names is not enough. Each entry therefore records when to use it, what data it needs, what visual expresses it, and how it is commonly misused.

---

## 1. Message types and chart choice

Base mapping, after Zelazny (*Say It With Charts*), extended for consulting-specific forms.

| Message type | The title says | Preferred visuals | Avoid |
|---|---|---|---|
| Component | "X accounts for most of Y" | 100% stacked bar, single stacked bar, Marimekko (two dimensions), composition block | Pie with more than 5 slices, donut sets |
| Item comparison | "A leads B and C on Z" | Horizontal bar sorted, dot plot, lollipop | Unsorted bars, radar |
| Time series | "Z grew/fell over time" | Column (few periods), line (many periods), column with CAGR arrow, indexed line | Area charts with many series |
| Bridge | "Z moved from a to b because of drivers" | Waterfall, price-volume-mix bridge | Stacked bars showing change |
| Frequency distribution | "Most cases fall in range r" | Histogram, box plot | Line through bins |
| Correlation | "Higher A goes with higher B" | Scatter, bubble, paired bars | Dual-axis lines |
| Two-dimension share | "Segment s is large and fragmented" | Marimekko, profit pool | Grouped stacked bars |
| Prioritisation | "Do these first" | 2x2 matrix, bubble matrix, value vs ease | Ranked list without criteria |
| Assessment | "Option A is strongest on criteria" | Harvey-ball table, RAG table, scoring table | Paragraphs |
| Schedule | "We deliver in three waves" | Gantt, milestone timeline, phased waves | Bulleted dates |
| Structure | "Value is driven by these factors" | Driver tree, issue tree, hierarchy | Mind maps |
| Process | "The flow has n steps" | Chevrons, swimlane, value stream | Numbered bullets |
| Geography | "Revenue concentrates in k regions" | Highlight map with callouts, choropleth, ranked bars | 3D globes |
| Magnitude headline | "Three numbers matter" | KPI row, big-number tiles | Tables of one row |

---

## 2. Catalogue

Columns: **Q** = question it answers. **Data** = minimum data. **Visual** = canonical visual (archetype id in brackets). **Pitfalls** = what QA checks for.

### 2.1 Problem structuring

| ID | Framework | Q | Data | Visual | Pitfalls |
|---|---|---|---|---|---|
| F001 | Issue tree (MECE) | How do we break the problem down? | None (logic) | Issue tree [issue_tree] | Overlapping branches, mixed levels, more than 5 branches per node |
| F002 | Hypothesis tree | What must be true for the answer to hold? | None, then tests per leaf | Tree with test status [issue_tree] | Untestable leaves |
| F003 | Value driver tree | Which operational drivers move the target metric? | Metric decomposition, driver values | Driver tree with values and deltas [driver_tree] | Non-multiplicative links shown as multiplicative |
| F004 | Pareto (80/20) | Where is the concentration? | Items with values | Sorted bars plus cumulative line [pareto] | Unsorted, no cumulative share |
| F005 | Pyramid / SCR storyline | How do we sequence the argument? | Storyline | Executive summary [exec_summary] | Topic titles, missing complication |

### 2.2 Market and customer

| ID | Framework | Q | Data | Visual | Pitfalls |
|---|---|---|---|---|---|
| F010 | Market sizing, top-down | How big is the market? | Total market, segment shares | Funnel or stacked bar TAM, SAM, SOM [market_funnel] | Mixing revenue and volume, no year |
| F011 | Market sizing, bottom-up | How big is it from first principles? | Units, penetration, price | Driver tree with assumptions table [driver_tree] | Hidden assumptions |
| F012 | Market growth decomposition | Is growth from market or share? | Market size and share over time | Waterfall: market growth vs share gain [waterfall] | Base period mismatch |
| F013 | Market map | Who holds share in which segment? | Segment sizes, player shares | Marimekko [mekko] | Too many small players unlabelled ("Others" missing) |
| F014 | Profit pool | Where is the profit in the value chain? | Revenue and margin by step | Variable-width bars: width revenue, height margin [profit_pool] | Margin definitions inconsistent |
| F015 | Customer segmentation | Which customer groups behave differently? | Survey or transaction attributes | Segment profile table, bubble by size and value [segment_profiles] | Segments not actionable |
| F016 | Key purchasing criteria | What do customers value and how do we perform? | Importance and performance scores | Importance vs performance scatter, gap bars [kpc_gap] | Stated vs derived importance confused |
| F017 | Customer journey | Where does the experience break? | Stage-wise pain points, drop-off | Journey with emotion curve and pain points [journey] | No quantification |
| F018 | Net Promoter / loyalty | How loyal are customers vs peers? | NPS by player or segment | Ranked bars with promoter/detractor split [ranked_bar] | Small samples without n |
| F019 | Willingness to pay | What price maximises value? | Survey (Van Westendorp, conjoint) | Price acceptance curves, demand curve [line_chart] | Hypothetical bias unstated |
| F020 | Adoption S-curve | Where are we on adoption? | Penetration over time | S-curve with current position [line_chart] | Extrapolating without saturation logic |

### 2.3 Competition and strategy

| ID | Framework | Q | Data | Visual | Pitfalls |
|---|---|---|---|---|---|
| F030 | Five forces (Porter) | How attractive is the industry? | Force assessments with evidence | Five-force diagram with intensity ratings [five_forces] | Ratings without evidence |
| F031 | Competitive benchmarking | How do we compare on key metrics? | Metrics by peer | Small multiples of ranked bars, highlight self [small_multiples] | Peers chosen to flatter |
| F032 | Strategic group map | Who competes with whom? | Two strategic dimensions, size | Bubble chart [bubble] | Axes correlated with each other |
| F033 | Growth-share matrix (BCG) | Where to invest across the portfolio? | Market growth, relative share, revenue | Bubble matrix with quadrant labels [matrix_2x2] | Relative share computed incorrectly |
| F034 | Nine-box (GE-McKinsey) | Which businesses to grow, hold, harvest? | Attractiveness and strength scores | 3x3 matrix with bubbles [matrix_3x3] | Scoring weights unstated |
| F035 | Ansoff matrix | Which growth vectors? | Initiatives by product and market newness | 2x2 with initiatives placed [matrix_2x2] | Everything in "diversification" |
| F036 | Three Horizons | How to balance core and new? | Initiatives, value, timing | Horizons curve with initiatives [three_horizons] | No resource split |
| F037 | Where to play / how to win | What is the strategic choice? | Options and criteria | Choice cascade or options table [options_table] | Options not mutually exclusive |
| F038 | Value chain (Porter) | Where do we create or lose value? | Activities, cost, capability | Chevron chain with metrics [value_chain] | Generic activities without data |
| F039 | Capability assessment | Where are we strong or weak? | Capability scores vs required | Harvey-ball table [harvey_table] | Self-assessment without benchmark |
| F040 | SWOT | What is the situation summary? | Qualitative findings | 2x2 text grid [matrix_2x2_text] | Low analytical value. Use only when asked |
| F041 | PESTEL | Which macro factors matter? | Factor assessments | Table with impact ratings [rag_table] | Laundry lists |
| F042 | Scenario planning | What futures should we prepare for? | Two critical uncertainties | 2x2 scenario matrix with narratives [matrix_2x2] | Uncertainties not independent |

### 2.4 Finance and performance

| ID | Framework | Q | Data | Visual | Pitfalls |
|---|---|---|---|---|---|
| F050 | Revenue bridge (price, volume, mix) | Why did revenue change? | Revenue by product, price, volume, two periods | Waterfall PVM [waterfall] | Mix effect computed inconsistently |
| F051 | EBITDA / profit bridge | Why did profit change? | P&L lines, two periods | Waterfall [waterfall] | Signs and colours inconsistent |
| F052 | Cost structure | Where does the money go? | Cost by category | Waterfall build-up or 100% bar [waterfall] | Mixing fixed and variable without label |
| F053 | ROIC / DuPont tree | What drives returns? | Margin, turnover, capital | Driver tree [driver_tree] | Period mismatch between P&L and balance sheet |
| F054 | Peer performance map | Are we growing profitably vs peers? | Growth and margin by peer | Scatter with quadrant and median lines [scatter_quadrant] | Different fiscal years |
| F055 | TSR decomposition | What drove shareholder returns? | Revenue growth, margin change, multiple change, dividends | Stacked or waterfall decomposition [waterfall] | Non-additive components summed |
| F056 | Valuation football field | What is it worth? | Ranges by method | Floating horizontal bars [football_field] | Ranges without methodology |
| F057 | Sensitivity (tornado) | Which assumptions matter most? | Output change per input swing | Tornado [tornado] | Asymmetric swings unlabelled |
| F058 | Business case (NPV, IRR, payback) | Is the investment worth it? | Cash flows, discount rate | Cash-flow columns with cumulative line, KPI row [business_case] | Discount rate unstated |
| F059 | Unit economics (CAC, LTV) | Does each customer make money? | Acquisition cost, margin, churn | Unit waterfall, LTV/CAC KPI [waterfall] | Gross vs contribution margin confusion |
| F060 | Working capital (DSO, DIO, DPO) | Is cash trapped? | Receivables, inventory, payables | Cash conversion cycle bars vs peers [ranked_bar] | Seasonal distortion |
| F061 | Capital allocation | Where did cash go? | Sources and uses | Sources-and-uses waterfall [waterfall] | Double counting |

### 2.5 Operations and cost

| ID | Framework | Q | Data | Visual | Pitfalls |
|---|---|---|---|---|---|
| F070 | Cost-out levers | How much can we save and where? | Baseline, savings by lever | Savings waterfall with ranges [waterfall] | Overlapping levers double-counted |
| F071 | Spend cube | Where is third-party spend concentrated? | Spend by category and supplier | Marimekko or Pareto [mekko] | Unclassified spend hidden |
| F072 | Zero-based budgeting | What should the cost base be? | Activity-level costs | Baseline vs ZBB waterfall [waterfall] | Baseline not normalised |
| F073 | Spans and layers | Is the organisation efficient? | Headcount by layer, span of control | Org pyramid with spans [org_pyramid] | Mixing FTE and headcount |
| F074 | Process map / value stream | Where is time or cost lost? | Steps, times, wait times | Value stream with timeline [process_chevrons] | Missing wait times |
| F075 | OEE loss tree | Why is equipment output low? | Availability, performance, quality losses | OEE waterfall [waterfall] | Planned downtime treatment unstated |
| F076 | Capacity utilisation | Do we have enough capacity? | Capacity and demand by site and period | Bars with capacity line [column_with_line] | Theoretical vs practical capacity |
| F077 | Make vs buy | Should we outsource? | Internal cost, external price, strategic fit | Cost comparison plus criteria table [options_table] | Ignoring transition cost |
| F078 | Footprint optimisation | Where should facilities be? | Sites, demand, cost | Map with sites and flows [map_callouts] | Static view of dynamic demand |
| F079 | Marginal abatement cost curve | Which abatement levers are cheapest? | Lever cost per tonne and volume | Variable-width bar curve [mac_curve] | Negative-cost levers without evidence |

### 2.6 Organisation and transformation

| ID | Framework | Q | Data | Visual | Pitfalls |
|---|---|---|---|---|---|
| F090 | 7S (McKinsey) | Is the organisation aligned? | Assessments per element | 7S network with ratings [seven_s] | Ratings without evidence |
| F091 | Operating model | How should we organise to deliver the strategy? | Design choices per dimension | Layered operating model canvas [op_model] | Dimensions not linked to strategy |
| F092 | RACI | Who decides and does what? | Roles by activity | RACI matrix [raci_table] | Multiple "A" per row |
| F093 | Stakeholder map | Whom must we manage? | Influence and interest | 2x2 with stakeholders [matrix_2x2] | Missing actions per quadrant |
| F094 | Maturity model | Where are we vs target? | Current and target levels per dimension | Staircase or dot-range table [maturity] | Levels undefined |
| F095 | Transformation roadmap | When does what happen? | Initiatives, durations, dependencies | Gantt with waves and milestones [gantt] | No dependencies or owners |
| F096 | Initiative prioritisation | What do we do first? | Value and ease per initiative | Value vs ease 2x2 with bubbles [matrix_2x2] | Criteria not scored consistently |
| F097 | Benefits tracking (stage gates) | Is value being delivered? | Initiative value by stage | Stage-gate funnel waterfall [waterfall] | Mixing run-rate and in-year |

### 2.7 M&A and deals

| ID | Framework | Q | Data | Visual | Pitfalls |
|---|---|---|---|---|---|
| F100 | Target screening funnel | Which targets fit? | Long list with filter criteria | Funnel with counts per filter [funnel] | Criteria applied out of order |
| F101 | Synergy case | How much value does the deal create and when? | Cost and revenue synergies, phasing, one-off costs | Synergy waterfall plus phasing columns [waterfall] | Revenue synergies not risk-weighted |
| F102 | Due diligence red flags | What could kill the deal? | Findings by area | RAG table [rag_table] | No quantification of impact |
| F103 | 100-day integration plan | What happens first after close? | Workstreams, actions, dates | Gantt by workstream [gantt] | No owners |

### 2.8 Technology, risk and ESG

| ID | Framework | Q | Data | Visual | Pitfalls |
|---|---|---|---|---|---|
| F110 | Use-case prioritisation (digital, AI) | Which use cases first? | Value and feasibility per use case | Bubble matrix [matrix_2x2] | Value not quantified |
| F111 | Value at stake heat map | Where is the value by function and lever? | Value by function and lever | Heat-map table [heatmap_table] | Ranges shown as points |
| F112 | Technology landscape | What systems exist and overlap? | Systems by capability | Capability map with system tiles [capability_map] | Unreadable density |
| F113 | Risk heat map | Which risks matter most? | Likelihood and impact per risk | 5x5 heat map with risk markers [risk_heatmap] | Scales undefined |
| F114 | ESG materiality matrix | Which topics matter to stakeholders and business? | Two importance scores per topic | Scatter with threshold lines [scatter_quadrant] | Unclear scoring method |
| F115 | Emissions trajectory | Are we on track to target? | Baseline, actuals, target path, levers | Line with target path plus lever waterfall [line_with_target] | Scope 1, 2, 3 mixed |

---

## 3. Machine-readable entry schema

```yaml
id: F050
name: Revenue bridge (price, volume, mix)
question_types: [explain_change, performance_review]
triggers:                       # phrases and intents in briefs that suggest this analysis
  - "why did revenue change"
  - "drivers of growth"
inputs:                         # become DataNeed templates (TRD 6)
  - metric: revenue
    dims: [product, period]
    periods: 2
  - metric: volume
    dims: [product, period]
  - metric: price
    dims: [product, period]
    derivable_from: [revenue, volume]
steps:
  - compute price effect: sum over products of (P1 - P0) x V1
  - compute volume effect: (V1_total - V0_total) x average P0
  - compute mix effect: residual, shown separately
calc_engine: pvm_bridge         # deterministic implementation, never the model
visuals:
  primary: waterfall
  alternatives: [bar_pair_with_deltas]
archetypes: [waterfall_bridge, chart_with_takeaway]
title_patterns:
  - "Revenue grew {delta} driven mainly by {largest_driver}"
pitfalls:
  - id: mix_inconsistent
    check: price + volume + mix equals total change within rounding
  - id: sign_colour
    check: positive steps use positive colour, negative steps negative colour
related: [F051, F012]
```

Every entry links to a deterministic calc where numbers are involved, so the analysis is computed by code and only narrated by the model.

---

## 4. How the model learns to use the library

1. **Retrieval.** The storyline planner retrieves candidate analyses from question types and triggers in the brief.
2. **Corpus tagging.** Every corpus slide is tagged with the framework it uses (VLM classification with expert spot-checks). This gives real frequencies of which analysis answers which kind of question in top-firm decks, and exemplars per framework.
3. **Supervised examples.** Reconstructed corpus slides (TRD 11.5) give pairs of (slide message and data) to (framework, visual, layout), used to fine-tune the planner.
4. **QA.** QA-1 checks that the chosen analyses cover the brief's questions without gaps. QA-3 checks visual fit and the pitfalls listed per entry.

## 5. Coverage plan

| Version | Entries | Selection |
|---|---|---|
| V1 (M2) | 30 most frequent in corpus tagging plus all bridge and matrix types | Frequency in corpus and golden briefs |
| V1.1 | Full catalogue above (about 75) | |
| Later | Industry packs (banking, consumer, industrials, healthcare, public sector) with sector KPIs and benchmarks | Customer demand |
