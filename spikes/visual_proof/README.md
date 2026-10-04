# Visual proof spike

Question tested: can a deterministic renderer produce consulting-grade slides as **native, editable PowerPoint objects**, with no image-based or default-styled charts?

## What it builds

| Slide | Benchmark | Techniques exercised |
|---|---|---|
| 1 | Bain PE report 2023, p5 | Native column chart, grey plus one highlight, point-level label format, top-tick unit via conditional number format, abbreviated year axis, data row aligned to bars from computed plot geometry |
| 2 | Bain PE report 2023, p6 | Two native charts, panel action titles, think-cell style difference arrow computed from bar tops, change label computed from data, layout shift when the title wraps |
| 3 | McKinsey DACH survey 2020, p4 | Native 100% stacked bar (Likert), category gap row, flags drawn as shapes, takeaway sidebar whose headline number is computed from the data |
| 4 | House style | Native waterfall (stacked column with invisible base), connectors and labels from computed geometry, ILLUSTRATIVE sticker, title computed from data |

All numbers in titles and labels are computed from the series data, never typed. The geometry lint checks measured text extents and stickers for overlaps. On the first run it caught a title colliding with the sticker and a subtitle crammed under a wrapped title. Both are fixed.

## Results

- Side-by-side renders (`out/comparison.png`, generated locally, not committed) show near-parity with the originals.
- Every chart opens as a native PowerPoint chart with an embedded workbook ("Edit Data" works).
- Remaining gaps: tick-label size calibration, title width rules, group-gap sizing.

## Known limits (expected, documented in TRD 7.3)

- Overlays (difference arrow, waterfall labels and connectors, data rows) are positioned from data at build time. If a user edits chart data in PowerPoint, overlays do not move until DeckForge re-imports and recompiles. The spec is meant to be stored in the file for that purpose. This spike does not do that yet.
- Rendering uses LibreOffice. Fidelity in PowerPoint itself was not checked in this spike.
- Benchmark slides use public figures (values on slide 2 are approximated from the published chart) for internal comparison only.

## Run

```bash
pip install python-pptx pillow
# rendering needs LibreOffice Impress and metric-compatible fonts
apt-get install -y --no-install-recommends libreoffice-impress
# Gelasio (OFL) is metric-compatible with Georgia. Alias Georgia -> Gelasio in fontconfig
python3 build_deck.py                      # writes out/visual_proof.pptx and prints lint results
cd out && soffice --headless --convert-to pdf visual_proof.pptx && pdftoppm -r 60 -png visual_proof.pdf slide
```
