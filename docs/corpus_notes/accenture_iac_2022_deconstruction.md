# Deconstruction: Accenture Investor & Analyst Conference 2022 (17 slides)

Source: public corpus file `accenture_accenture_investor_analyst_conference_2022_331ef1c71d.pdf`.
Purpose: first worked example of how a corpus deck is turned into archetypes, components and style rules. This is the annotation format for the corpus program (TRD 11).

## 1. Style family

Corporate keynote / investor relations. Brand-forward, low density, large typography, crafted 3D graphics, photographic background. It is a different family from consulting engagement decks (McKinsey, BCG, Bain working decks), which are denser, sober, chart-led and carry trackers and source lines on every page. Both families are legitimate targets. They need different rules (PRD section 6).

## 2. Slide-by-slide

| # | Title (type) | Archetype | Components | Technique worth learning | Weakness |
|---|---|---|---|---|---|
| 1 | Accenture Investor & Analyst Conference (cover) | Cover, full-bleed image | Image, light-weight display title, date | Very light display weight at large size gives a premium feel | n/a |
| 2 | Delivering shareholder value at scale (topic-ish) | Split statement + metric table | Statement column left, 2x3 metric table, highlight cells | Highlight box on the "so-what" column (the step-up). Superscript footnote discipline | Title states a theme, not the insight ("$18B revenue step-up in two years") |
| 3 | Same title as 2 | Split statement + metric table | As 2, 4 columns | Cumulative column as the highlighted answer | Duplicate title across two slides |
| 4 | Enduring approach to shareholder value creation | Split statement + stacked claims | Statement, 3 claims separated by hairlines, keyword bolding | Mixed weight within a sentence for scanning ("**Grow faster** than the market") | No evidence on slide |
| 5 | Continued to outperform the market and take share (action) | Chart + table | Clustered isometric columns, legend, growth-multiple table below aligned to chart groups | Table columns aligned to chart groups so the eye reads down. Hero series in darkest colour, value labels bold only for hero | 3D bars distort comparison. Mitigated by direct value labels |
| 6 | Our Next Generation Growth Model changed our services to put digital everywhere (action) | Composition block + callout | Isometric stacked block (3 segments), segment labels left, values right, total bar above, icon + KPI callout right | Composition shown as a single object rather than a pie. Total stated first | Block heights not proportional to values ($9B segment looks similar to $15B) |
| 7 | Positioned for double digit growth across all our Strategic Growth Priorities (action) | Split statement + list grid | 2x5 grid of items with left rules | Vertical hairline as item marker instead of bullets | List without data |
| 8 | Highlights of Strategic Growth Priorities (topic) | Split statement + metric rows | 4 rows: name, FY19, FY22, CAGR. Purple row headers, rule lines | Repeated small-multiple row pattern, numbers in heavy weight | Title could carry the insight ("Cloud tripled to $26B") |
| 9 | Our Next Generation Growth Model has allowed us to scale... (action) | Map + ranked list | World map with highlighted countries and value callouts with leader lines, 10-item two-column list with values | Map highlight plus direct labels instead of a choropleth legend | Values on map not sorted. Two banner headers repeat the same wording |
| 10 | Stepping up our Investments in acquisitions... (action) | Isometric bars + metrics table | 3 isometric bars, large value labels, 3-row table aligned to bars | Big value labels above bars carry the message. Table rows aligned under bars | 3D. FY22 bar ($4B) looks similar to FY21 ($4.2B), fine, but the scale is not shown |
| 11 | Significant step up in P&L investments at scale while delivering modest margin expansion and strong EPS growth (action) | Financial table | Multi-level table, coloured section header row, highlight cells, indented sub-rows | Hierarchy through indentation, colour and weight, no grid lines | Highlight cells lack an explanation of why they matter |
| 12 | Profit levers creating incremental capacity to invest at scale (action) | Split statement + 2x2 list | 4 levers with left rules | Clean | No quantification of levers |
| 13 | Delivering strong cash flow, maintained all aspects of capital allocation framework... (action) | Framework (3 nodes) + callouts | 3 cubes in triangle, leader lines to three text blocks, accent-coloured numbers | Framework as an object with data attached to each node | Cubes are decorative, carry no data |
| 14 | Highlights of our 360° value for all our stakeholders (topic) | KPI row | Section label, 4 big numbers with descriptors, hairline separators | Big-number typography, descriptor with bolded keyword | Title repeated across 14 to 16 |
| 15 | Same (topic) | KPI row | 3 big numbers | As 14 | As 14 |
| 16 | Same (topic) | KPI row | 3 big numbers, "Targeting" pre-label | Pre-label above number to qualify it | As 14 |
| 17 | Continued Strong Momentum (topic) | Comparison table with column highlight | 2 guidance columns, shaded band on "current" column, small "to" connectors | Column highlight band to direct attention. Small-size connective words between numbers | Title gives no insight |

## 3. What makes it look crafted rather than bland

1. **One hue family used semantically.** Purple ramp: darkest for the hero series, lighter tints for comparators, a lilac fill for highlighted answers.
2. **Typographic contrast.** Light weight for titles and statements, heavy weight for numbers, numbers 3 to 4 times body size on KPI slides.
3. **Emphasis on the answer.** Every data slide highlights one thing (step-up cell, hero series, current-guidance column).
4. **Alignment between chart and table.** Tables placed under charts with columns aligned to chart groups.
5. **Bespoke data graphics.** Isometric bars and blocks, map with leader-line callouts. All are simple geometric constructions that can be generated from data.
6. **Whitespace.** Low element count, large margins, no boxes around text.
7. **Footnote rigour.** Superscripts, short rule above footnotes, "Illustrative" qualifiers.
8. **Two layout systems used consistently.** Left statement column for thematic slides, top title for evidence slides.

## 4. What DeckForge should take, and what it should not

| Take (as generic techniques) | Do not take |
|---|---|
| Highlight-the-answer rule, hero-series colouring | Accenture logo, chevron mark, wordmark |
| Chart-plus-aligned-table archetype | Graphik font (commercial licence) |
| Split statement archetype | The exact purple palette as a default |
| KPI row with big-number typography and qualifiers | Background photography |
| Isometric bar and block constructions (keynote family only) | Verbatim text or numbers |
| Map with highlighted regions and leader-line callouts | |
| Footnote and qualifier conventions | |

## 5. Rules this deck adds or modifies

| Rule | Family | Note |
|---|---|---|
| Isometric (3D-styled) bars allowed only with direct value labels and a single series per group or clearly separated groups | Keynote | Consulting family keeps "no 3D" (TRD C2) |
| Composition blocks must be height-proportional | Both | Slide 6 violates this. Our renderer computes heights from data, so it cannot |
| A title may not repeat across consecutive slides unless the slides form a declared sequence with a sub-label | Both | Slides 2 and 3, 14 to 16 |
| KPI slides need a title that states the overall point | Both | Slides 14 to 16 use a topic title |

## 6. Archetypes added to the library from this deck

`split_statement_table`, `split_statement_list_grid`, `chart_with_aligned_table`, `composition_block_with_callout`, `map_with_callouts_and_ranked_list`, `isometric_bars_with_metrics_table`, `financial_table_hierarchical`, `framework_nodes_with_callouts`, `kpi_row`, `comparison_table_column_highlight`.
