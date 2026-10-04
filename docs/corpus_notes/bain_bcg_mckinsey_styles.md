# Style analysis: Bain, BCG, McKinsey sample decks

Sources (public corpus): Bain *Global Private Equity Report 2023* roadshow deck (17 pp, pages 2 to 9 reviewed), BCG *Executive Perspectives: Guide to Cost and Growth* (Jan 2025, 24 pp, pages 3 to 12 reviewed), McKinsey *Consumers' sustainability sentiment and behavior before, during and after COVID-19* (DACH survey, 2020, 26 pp, pages 2 to 12 reviewed). Companion to `accenture_iac_2022_deconstruction.md`.

## 1. Firm style systems

| Dimension | Bain (PE report) | BCG (Executive Perspectives) | McKinsey (consumer survey) |
|---|---|---|---|
| Aspect | 16:9 | 16:9 | 4:3 |
| Title | Sans, regular weight, black, sentence case, 1 to 2 lines, action title | Bold sans, white on dark photo band, action title, green rule below | Bold serif, navy, action title that leads with the number ("> 1/4 of consumers…"), grey sans topic line below, rule under |
| Palette | Greys plus one red for the answer. Navy-grey ramp for secondary series | Semantic: red pessimist, grey neutral, green optimist. Region colours, faded when not in focus | Navy, light cyan, cyan, bright blue, light grey |
| Emphasis device | Red hero bar plus large red value label | Highlight panel behind the focal small multiple, other panels faded | Dark navy sidebar with big serif cyan numbers and white bold descriptors |
| Charts | Columns, stacked columns, line with light area fill, long time series with period-average lines and band overlays | 100% stacked columns with series connector lines, grouped bars in small multiples, donut, one 3D pie | 100% stacked horizontal Likert bars, butterfly bars with difference column, small multiples with icons, mini column charts |
| Annotation | Difference arrow with bracket "(−50%)", top-tick unit "$1,200B", end value inside plot ("11.9x"), average lines with labels | Callout box with pin markers pointing to bars, arrows from donut segments to lists | Flags as row labels, "Fully disagree / Fully agree" end labels, n counts at bar end, "XX focused on next slides" key |
| Sub-structure | Bold panel headers that are themselves mini action titles | Question as green bold subheading ("How do executives view…?"), right takeaway panel with bold phrases | Quoted survey question in bold above chart, "Percentage" unit line |
| Navigation | None visible | Agenda with check-circle tracker repeated as section dividers, active item green | "Chapter › Topic" tracker on some pages |
| Sources | Absent on reviewed pages | Every page, with sample size and date | Footnotes only on some pages |
| Text density | Very low | Medium to high (exec summary dense) | Medium, exec summary dense (9 numbered takeaways) |
| Notable defects | No sources | 3D pie, long sidebar paragraphs | Typos ("divers sample", "shoppingtypes"), 4:3 format |

## 2. The shared craft grammar (what "McKinsey-grade" means operationally)

These are the transferable techniques common to all three firms. They are encoding and annotation decisions, not chart-library features, and every one of them can be produced from data by a rendering engine.

1. **One answer colour.** Everything is grey or muted except the data that proves the title.
2. **Quantified action titles.** The title states the insight, often leading with the number.
3. **Chart header = metric definition plus unit**, small and muted, above the plot. Unit placed once (top tick or header), not on every label.
4. **Minimal chrome.** No gridlines, no chart borders, baseline only, no tick marks.
5. **Abbreviated time axes.** "2005, 06, 07 …".
6. **Annotation layer.** Difference arrows, CAGR arrows, totals, end values, average lines, period bands, callouts with pins.
7. **Aligned data rows and tables** under charts, column-aligned to categories.
8. **Takeaway device.** Sidebar with big numbers (McKinsey) or bold-phrase panel (BCG) that restates the so-what.
9. **Series consistency.** The same chart repeated across consecutive slides with a different focus (BCG pages 7 and 8, McKinsey pages 4 to 8).
10. **Small multiples on equal scales.**
11. **Semantic colour** where categories have meaning (pessimist red, optimist green).
12. **Thin outline icons and flags as category markers**, never as decoration.
13. **Tracker and agenda** with active-state highlighting for longer decks.
14. **Source line with sample size and date.**

## 3. Corpus composition caveat

All four reviewed decks are published material (research reports, roadshows, investor decks). Client engagement decks (steerco packs, ghost decks, working sessions) are denser, carry "Preliminary" and "Draft for discussion" markers, trackers on every page and more frameworks. They are rarely public. If the product targets engagement-style decks, the public corpus under-represents that style. Your own slides and commissioned examples should fill the gap.

## 4. Visual proof

`spikes/visual_proof/` rebuilds Bain pages 5 and 6 and McKinsey page 4 as native, data-editable PowerPoint charts plus computed overlays (difference arrow, aligned data row, flags, sidebar), and adds a house-style waterfall with dummy data. Side-by-side renders show near-parity. Remaining gaps: tick-label size calibration and title wrapping width. See `spikes/visual_proof/README.md`.

## 5. Archetypes and components added

Archetypes: `two_panel_chart_with_panel_titles`, `chart_with_takeaway_sidebar_bignumbers`, `likert_stacked_bars`, `butterfly_bars_with_delta_column`, `small_multiples_with_focus_panel`, `agenda_tracker_divider`, `exec_summary_labelled_rows`, `ranked_priorities_with_icons`, `survey_sample_profile`.

Components: `difference_arrow`, `top_tick_unit`, `end_value_label`, `average_line_with_label`, `period_band_overlay`, `series_connector_lines`, `callout_with_pins`, `flag_marker`, `focus_panel`, `big_number_stack`, `question_subhead`, `n_count_label`.
