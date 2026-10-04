"""Visual proof spike: consulting-grade slides as native, editable PowerPoint objects.

Recreates two benchmark slides (Bain PE report 2023, McKinsey DACH consumer survey 2020)
and one house-style waterfall with dummy data, to test whether native charts plus
computed overlays reach consulting craft without image-based charts.

Run:  python3 build_deck.py  ->  out/visual_proof.pptx
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path

from lxml import etree
from PIL import ImageFont
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_TICK_LABEL_POSITION, XL_TICK_MARK
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

OUT = Path(__file__).parent / "out"

SLIDE_W, SLIDE_H = Inches(13.333), Inches(7.5)


def rgb(hex_: str) -> RGBColor:
    return RGBColor.from_string(hex_.lstrip("#"))


# --------------------------------------------------------------------------- tokens

@dataclass(frozen=True)
class Style:
    title_font: str
    body_font: str
    ink: str
    muted: str
    rule: str
    neutral: str
    highlight: str
    title_size: int = 26


BAIN_LIKE = Style("Arial", "Arial", "#000000", "#333333", "#333333", "#B5B5B5", "#CC0000", 26)
MCK_LIKE = Style("Georgia", "Arial", "#051C2C", "#333333", "#051C2C", "#E5E5E5", "#00A9F4", 26)
HOUSE = Style("Georgia", "Arial", "#14284B", "#4A4A4A", "#14284B", "#C9CED6", "#1F6FD1", 26)


# --------------------------------------------------------------------------- font metrics

# Real font files drive text fitting. Liberation Sans is metric-compatible with Arial and
# Gelasio with Georgia, so wrapping matches what PowerPoint does with the original fonts.
_LIB = "/usr/share/fonts/truetype/liberation"
FONT_FILES = {
    ("Arial", False): (f"{_LIB}/LiberationSans-Regular.ttf", None),
    ("Arial", True): (f"{_LIB}/LiberationSans-Bold.ttf", None),
    ("Georgia", False): (str(Path.home() / ".fonts/Gelasio.ttf"), b"Regular"),
    ("Georgia", True): (str(Path.home() / ".fonts/Gelasio.ttf"), b"Bold"),
}
_fonts: dict = {}
EMU_PER_PT = 12700


def _font(name, bold):
    key = (name, bold)
    if key not in _fonts:
        path, variation = FONT_FILES[key]
        f = ImageFont.truetype(path, 1000)          # measure at 1000 units per em
        if variation:
            f.set_variation_by_name(variation)
        _fonts[key] = f
    return _fonts[key]


def measure(s, font, size, bold, width_emu, leading=1.2):
    """Greedy word wrap with real glyph advances. Returns (lines, height in EMU)."""
    f = _font(font, bold)
    max_units = width_emu / EMU_PER_PT / size * 1000
    lines = 0
    for para in (s if isinstance(s, list) else [s]):
        words = (para if isinstance(para, str) else "".join(seg for seg, _ in para)).split()
        n, cur = 1, ""
        for wd in words:
            trial = f"{cur} {wd}".strip()
            if f.getlength(trial) <= max_units:
                cur = trial
            else:
                n, cur = n + 1, wd
        lines += n
    return lines, int(lines * size * leading * EMU_PER_PT)


# Placed text extents per slide, used by the geometry lint.
PLACED: dict[int, list[tuple[str, int, int, int, int]]] = {}


def _register(slide, name, x, y, w, h):
    PLACED.setdefault(slide.slide_id, []).append((name, x, y, w, h))


# --------------------------------------------------------------------------- primitives

def text(slide, x, y, w, h, s, *, font="Arial", size=12, bold=False, color="#000000",
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, name=None, wrap=True):
    _, used_h = measure(s, font, size, bold, w)
    _register(slide, name or (s if isinstance(s, str) else "text")[:40], x, y, w,
              used_h if anchor == MSO_ANCHOR.TOP else h)
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.auto_size = None
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    lines = s if isinstance(s, list) else [s]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        runs = line if isinstance(line, list) else [(line, bold)]
        for seg, seg_bold in runs:
            r = p.add_run()
            r.text = seg
            r.font.name = font
            r.font.size = Pt(size)
            r.font.bold = seg_bold
            r.font.color.rgb = rgb(color)
    if name:
        tb.name = name
    return tb


def rect(slide, x, y, w, h, fill, *, line=None, shape=MSO_SHAPE.RECTANGLE, name=None):
    sp = slide.shapes.add_shape(shape, x, y, w, h)
    sp.shadow.inherit = False
    if fill is None:
        sp.fill.background()
    else:
        sp.fill.solid()
        sp.fill.fore_color.rgb = rgb(fill)
    if line is None:
        sp.line.fill.background()
    else:
        sp.line.color.rgb = rgb(line[0])
        sp.line.width = Pt(line[1])
    if name:
        sp.name = name
        if name.startswith("DF_ILLUSTRATIVE"):
            _register(slide, name, x, y, w, h)
    return sp


def hline(slide, x1, x2, y, color, width=0.75):
    return line(slide, x1, y, x2, y, color, width)


def line(slide, x1, y1, x2, y2, color, width=0.75, arrow_end=False):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
    c.line.color.rgb = rgb(color)
    c.line.width = Pt(width)
    if arrow_end:
        ln = c.line._get_or_add_ln()
        tail = etree.SubElement(ln, qn("a:tailEnd"))
        tail.set("type", "triangle")
        tail.set("w", "med")
        tail.set("len", "med")
    return c


# --------------------------------------------------------------------------- chart geometry

@dataclass
class PlotBox:
    """Absolute inner plot rectangle of a chart, fixed via manualLayout so overlays can be computed."""
    x: int
    y: int
    w: int
    h: int
    n: int              # categories
    vmax: float
    vmin: float = 0.0
    horizontal: bool = False

    def cat_center(self, i: int) -> int:
        if self.horizontal:
            return int(self.y + (i + 0.5) * self.h / self.n)
        return int(self.x + (i + 0.5) * self.w / self.n)

    def cat_width(self) -> int:
        return int((self.h if self.horizontal else self.w) / self.n)

    def bar_width(self, gap_pct: int) -> int:
        return int(self.cat_width() / (1 + gap_pct / 100))

    def val(self, v: float) -> int:
        frac = (v - self.vmin) / (self.vmax - self.vmin)
        if self.horizontal:
            return int(self.x + frac * self.w)
        return int(self.y + self.h * (1 - frac))


def fix_plot_area(chart, frame_x, frame_y, frame_w, frame_h, fx, fy, fw, fh, **kw) -> PlotBox:
    """Pin the inner plot area to fractions of the chart frame and return its absolute box."""
    plot_area = chart._chartSpace.find(".//" + qn("c:plotArea"))
    old = plot_area.find(qn("c:layout"))
    if old is not None:
        plot_area.remove(old)
    layout = etree.SubElement(plot_area, qn("c:layout"))
    plot_area.remove(layout)
    plot_area.insert(0, layout)
    ml = etree.SubElement(layout, qn("c:manualLayout"))
    for tag, val in (("layoutTarget", "inner"), ("xMode", "edge"), ("yMode", "edge"),
                     ("x", fx), ("y", fy), ("w", fw), ("h", fh)):
        etree.SubElement(ml, qn(f"c:{tag}")).set("val", str(val))
    return PlotBox(int(frame_x + fx * frame_w), int(frame_y + fy * frame_h),
                   int(fw * frame_w), int(fh * frame_h), **kw)


def style_axes(chart, s: Style, *, vmax, major, num_fmt, show_value_axis=True, size=11):
    chart.font.name = s.body_font
    chart.font.size = Pt(size)
    chart.font.color.rgb = rgb(s.ink)
    va = chart.value_axis
    va.minimum_scale, va.maximum_scale, va.major_unit = 0, vmax, major
    va.has_major_gridlines = False
    va.major_tick_mark = XL_TICK_MARK.NONE
    va.format.line.fill.background()
    va.tick_labels.number_format = num_fmt
    va.tick_labels.number_format_is_linked = False
    if not show_value_axis:
        va.tick_label_position = XL_TICK_LABEL_POSITION.NONE
    ca = chart.category_axis
    ca.major_tick_mark = XL_TICK_MARK.NONE
    ca.format.line.color.rgb = rgb(s.rule)
    ca.format.line.width = Pt(0.75)


def column_chart(slide, x, y, w, h, cats, vals, s: Style, *, vmax, major, num_fmt,
                 gap=60, hero=None, hero_fmt=None, plot=(0.06, 0.04, 0.92, 0.84)):
    cd = CategoryChartData()
    cd.categories = cats
    cd.add_series("Value", vals)
    gf = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, x, y, w, h, cd)
    chart = gf.chart
    chart.has_legend = False
    chart.has_title = False
    p = chart.plots[0]
    p.gap_width = gap
    ser = p.series[0]
    ser.format.fill.solid()
    ser.format.fill.fore_color.rgb = rgb(s.neutral)
    style_axes(chart, s, vmax=vmax, major=major, num_fmt=num_fmt)
    box = fix_plot_area(chart, x, y, w, h, *plot, n=len(cats), vmax=vmax)
    for i in hero or []:
        pt = ser.points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = rgb(s.highlight)
        if hero_fmt:
            dl = pt.data_label
            dl.position = XL_LABEL_POSITION.OUTSIDE_END
            dl.show_value = True
            dl.font.size = Pt(18)
            dl.font.bold = True
            dl.font.color.rgb = rgb(s.highlight)
            set_label_number_format(dl, hero_fmt)
    return chart, box


def set_label_number_format(data_label, fmt):
    """Point-level number format. python-pptx exposes it only at series level, so write the XML."""
    dlbl = data_label._get_or_add_dLbl()
    for old in dlbl.findall(qn("c:numFmt")):
        dlbl.remove(old)
    nf = etree.Element(qn("c:numFmt"))
    nf.set("formatCode", fmt)
    nf.set("sourceLinked", "0")
    for tag in ("c:spPr", "c:txPr", "c:dLblPos", "c:showLegendKey", "c:showVal"):
        anchor = dlbl.find(qn(tag))
        if anchor is not None:
            anchor.addprevious(nf)
            return
    dlbl.append(nf)


def difference_arrow(slide, box: PlotBox, i, j, vi, vj, label, color, gap=0.6):
    """think-cell style difference arrow from the top of bar i to the top of bar j."""
    xi, xj = box.cat_center(i), box.cat_center(j)
    yi, yj = box.val(vi), box.val(vj)
    top = min(yi, yj) - Inches(0.35)
    lift = Inches(0.06)
    line(slide, xi, yi - lift, xi, top, color, 1.25)
    line(slide, xi, top, xj, top, color, 1.25)
    line(slide, xj, top, xj, yj - lift, color, 1.25, arrow_end=True)
    text(slide, int((xi + xj) / 2) - Inches(0.6), top - Inches(0.32), Inches(1.2), Inches(0.28),
         label, size=13, bold=True, color=color, align=PP_ALIGN.CENTER)


def title_block(slide, s: Style, title, *, y=Inches(0.45), sub=None, rule=False, width=Inches(12.4)):
    """Places title (and optional subtitle and rule). Returns the bottom edge so content flows below it."""
    bold = s.title_font != "Arial"
    _, th = measure(title, s.title_font, s.title_size, bold, width)
    text(slide, Inches(0.45), y, width, th, title, font=s.title_font, size=s.title_size, bold=bold,
         color=s.ink, name="DF_title")
    bottom = y + th
    if sub:
        text(slide, Inches(0.45), bottom + Inches(0.06), Inches(9), Inches(0.3), sub, size=15, color=s.muted)
        bottom += Inches(0.42)
    if rule:
        bottom += Inches(0.08)
        hline(slide, Inches(0.45), Inches(12.88), bottom, s.rule, 0.75)
    return bottom


def footer(slide, s: Style, source, page, *, x2=Inches(12.88)):
    text(slide, Inches(0.45), Inches(6.98), Inches(10), Inches(0.25), source, size=9, color=s.muted,
         name="DF_source")
    text(slide, x2 - Inches(0.5), Inches(6.98), Inches(0.5), Inches(0.25), str(page), size=9,
         color=s.muted, align=PP_ALIGN.RIGHT)


# --------------------------------------------------------------------------- calc + format

def pct_change(a, b):
    return (b - a) / a


def fmt_pct_paren(x):
    return f"({x:+.0%})".replace("+", "+")


def short_years(years):
    """2005, 06, 07 ... as used in consulting time axes."""
    return [str(y) if i == 0 else f"{y % 100:02d}" for i, y in enumerate(years)]


# --------------------------------------------------------------------------- slides

def slide_bain_bar(prs):
    s = BAIN_LIKE
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    years = list(range(2005, 2023))
    value = [296, 727, 695, 196, 93, 222, 231, 220, 296, 300, 372, 340, 430, 485, 480, 502, 1012, 654]
    deal = [256, 494, 476, 165, 119, 229, 254, 216, 310, 303, 445, 520, 645, 732, 761, 819, 1245, 964]
    drop = -pct_change(value[-2], value[-1])
    title_block(sl, s, f"Global buyout value dropped by more than a third in 2022 to ${value[-1]:,}B")
    assert drop > 1 / 3, "title claim must follow the data"
    text(sl, Inches(0.95), Inches(1.45), Inches(6), Inches(0.3), "Global buyout deal value (excl. add-ons)",
         size=13, color=s.muted)
    x, y, w, h = Inches(0.45), Inches(1.85), Inches(12.4), Inches(4.25)
    chart, box = column_chart(sl, x, y, w, h, short_years(years), value, s, vmax=1200, major=200,
                              num_fmt='[=1200]"$"#,##0"B";#,##0', hero=[len(value) - 1],
                              hero_fmt='"$"#,##0"B"', plot=(0.10, 0.04, 0.89, 0.86))
    # data row aligned under bars
    row_y = y + h + Inches(0.08)
    text(sl, Inches(0.45), row_y, box.x - Inches(0.5), Inches(0.5), ["Avg. deal size", "$M"], size=12,
         color=s.muted)
    cw = box.cat_width()
    for i, v in enumerate(deal):
        text(sl, box.cat_center(i) - cw // 2, row_y, cw, Inches(0.3), f"{v:,}", size=12, color=s.ink,
             align=PP_ALIGN.CENTER)
    footer(sl, s, "Source: Bain & Company, Global Private Equity Report 2023. Recreated for benchmark", 1)


def slide_bain_two_panel(prs):
    s = BAIN_LIKE
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    top = title_block(sl, s, "Banks pulled back and financing large deals became more challenging and costly")
    dy = max(0, top + Inches(0.2) - Inches(1.45))     # push panels down if the title wraps
    years = list(range(2012, 2023))
    lbo = [90, 172, 175, 150, 177, 255, 313, 240, 183, 410, 203]
    dl = [11, 23, 34, 44, 41, 62, 65, 90, 69, 129, 114]
    panels = [
        (Inches(0.45), "Total LBO loans issued declined across regions",
         "Syndicated LBO loan issuance, US & Europe", lbo, 500, 100, '[=500]"$"#,##0"B";#,##0'),
        (Inches(6.95), "Meanwhile, direct lending has been growing",
         "Global direct lending funds raised", dl, 150, 50, '[=150]"$"#,##0"B";#,##0'),
    ]
    boxes = []
    for px, head, sub, vals, vmax, major, fmt in panels:
        text(sl, px, Inches(1.45) + dy, Inches(6), Inches(0.3), head, size=15, bold=True, color=s.ink)
        text(sl, px, Inches(1.9) + dy, Inches(6), Inches(0.3), sub, size=13, color=s.muted)
        _, box = column_chart(sl, px, Inches(2.3) + dy, Inches(5.9), Inches(4.2) - dy, short_years(years), vals, s,
                              vmax=vmax, major=major, num_fmt=fmt, gap=45, hero=[len(vals) - 1],
                              plot=(0.11, 0.06, 0.87, 0.84))
        boxes.append(box)
    change = pct_change(lbo[-2], lbo[-1])
    difference_arrow(sl, boxes[0], len(lbo) - 2, len(lbo) - 1, lbo[-2], lbo[-1],
                     f"({change:.0%})", s.highlight)
    footer(sl, s, "Note: values approximated from the published chart. Source: Bain & Company, "
                  "Global Private Equity Report 2023. Recreated for benchmark", 2)


def flag(slide, x, y, code, w=Inches(0.42), h=Inches(0.28)):
    if code in ("DE", "AT"):
        cols = {"DE": ["#000000", "#DD0000", "#FFCE00"], "AT": ["#C8102E", "#FFFFFF", "#C8102E"]}[code]
        for k, c in enumerate(cols):
            rect(slide, x, y + int(k * h / 3), w, int(h / 3) + 1, c)
        if code == "AT":
            rect(slide, x, y, w, h, None, line=("#D0D0D0", 0.25))
    else:  # CH
        sq = h
        x0 = x + (w - sq) // 2
        rect(slide, x0, y, sq, sq, "#DA291C")
        arm, long_ = int(sq * 0.2), int(sq * 0.62)
        rect(slide, x0 + (sq - arm) // 2, y + (sq - long_) // 2, arm, long_, "#FFFFFF")
        rect(slide, x0 + (sq - long_) // 2, y + (sq - arm) // 2, long_, arm, "#FFFFFF")


def slide_mck_likert(prs):
    s = MCK_LIKE
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    panel_x = Inches(9.75)
    title = "Consumers show similar sustainable shopping behaviours across DACH countries"
    text(sl, Inches(0.45), Inches(0.45), Inches(9.0), Inches(0.9), title, font=s.title_font, size=24,
         bold=True, color=s.ink, name="DF_title")
    text(sl, Inches(0.45), Inches(1.32), Inches(9), Inches(0.3), "Sustainable shopping behaviour",
         size=14, color=s.muted)
    hline(sl, Inches(0.45), Inches(9.35), Inches(1.68), s.rule, 0.75)
    text(sl, Inches(0.45), Inches(1.82), Inches(8.9), Inches(0.62),
         '"Compared with before the COVID-19 crisis, to what extent do you agree with the following statements?"',
         size=13, bold=True, color=s.ink)
    text(sl, Inches(0.45), Inches(2.42), Inches(3), Inches(0.25), "Percentage of respondents", size=12,
         color=s.muted)

    rows = [("DE", [18, 12, 19, 24, 17, 10]), ("AT", [19, 13, 20, 24, 14, 10]), ("CH", [19, 12, 21, 27, 15, 6]),
            None,
            ("DE", [16, 13, 21, 23, 17, 10]), ("AT", [17, 12, 22, 23, 15, 11]), ("CH", [15, 11, 23, 26, 16, 9])]
    statements = [(0, 3, "In principle, I'm more willing to pay more for sustainable products"),
                  (4, 7, "I choose products more consciously to reduce my impact on the environment and society")]
    levels = ["Fully disagree", "2", "3", "4", "5", "Fully agree"]
    colors = ["#E5E5E5", "#E5E5E5", "#E5E5E5", "#AAE6F0", "#00A9F4", "#00A9F4"]
    cd = CategoryChartData()
    cd.categories = [f"r{i}" for i in range(len(rows))]
    for k, lvl in enumerate(levels):
        cd.add_series(lvl, [r[1][k] if r else None for r in rows])
    x, y, w, h = Inches(3.3), Inches(2.95), Inches(6.05), Inches(3.75)
    gf = sl.shapes.add_chart(XL_CHART_TYPE.BAR_STACKED_100, x, y, w, h, cd)
    ch = gf.chart
    ch.has_legend = False
    ch.has_title = False
    ch.font.name, ch.font.size = s.body_font, Pt(12)
    plot = ch.plots[0]
    plot.gap_width = 28
    plot.overlap = 100
    ca, va = ch.category_axis, ch.value_axis
    ca.reverse_order = True
    ca.tick_label_position = XL_TICK_LABEL_POSITION.NONE
    ca.major_tick_mark = XL_TICK_MARK.NONE
    ca.format.line.color.rgb = rgb("#051C2C")
    va.visible = False
    va.has_major_gridlines = False
    for ser, c in zip(plot.series, colors):
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = rgb(c)
        ser.format.line.color.rgb = rgb("#FFFFFF")
        ser.format.line.width = Pt(1)
        ser.data_labels.show_value = True
        ser.data_labels.position = XL_LABEL_POSITION.CENTER
        ser.data_labels.font.size = Pt(12)
        ser.data_labels.font.color.rgb = rgb("#FFFFFF" if c == "#00A9F4" else "#1A1A1A")
    box = fix_plot_area(ch, x, y, w, h, 0.0, 0.0, 1.0, 1.0, n=len(rows), vmax=100, horizontal=True)
    text(sl, box.x, y - Inches(0.3), Inches(2), Inches(0.25), "Fully disagree", size=12, bold=True, color=s.ink)
    text(sl, box.x + box.w - Inches(2), y - Inches(0.3), Inches(2), Inches(0.25), "Fully agree", size=12,
         bold=True, color=s.ink, align=PP_ALIGN.RIGHT)
    for i, r in enumerate(rows):
        if r:
            flag(sl, Inches(2.72), box.cat_center(i) - Inches(0.14), r[0])
    for a, b, label in statements:
        yc = (box.cat_center(a) + box.cat_center(b - 1)) // 2
        text(sl, Inches(0.45), yc - Inches(0.4), Inches(2.15), Inches(0.8), label, size=12, color=s.ink,
             anchor=MSO_ANCHOR.MIDDLE)
    hline(sl, Inches(0.45), Inches(9.35), Inches(6.85), s.rule, 0.75)

    # takeaway sidebar: the computed headline figure
    gaps = []
    for a, b, _ in statements:
        agree = [sum(rows[i][1][3:]) for i in range(a, b)]
        gaps.append(max(agree) - min(agree))
    rect(sl, panel_x, 0, SLIDE_W - panel_x, SLIDE_H, "#051C2C", name="DF_sidebar")
    hline(sl, panel_x + Inches(0.35), SLIDE_W - Inches(0.35), Inches(1.68), "#6B7A8A", 0.75)
    text(sl, panel_x + Inches(0.35), Inches(2.0), Inches(3.2), Inches(1.4), f"<{max(gaps) + 1} pp difference",
         font="Georgia", size=40, bold=True, color="#00A9F4")
    text(sl, panel_x + Inches(0.35), Inches(3.5), Inches(3.0), Inches(1.2),
         "between DACH countries in agreement on willingness to pay and conscious product choice",
         size=14, bold=True, color="#FFFFFF")
    text(sl, Inches(0.45), Inches(6.98), Inches(9), Inches(0.25),
         "Source: McKinsey consumer survey, DACH, Nov to Dec 2020. Recreated for benchmark", size=9, color=s.muted)


def slide_house_waterfall(prs):
    s = HOUSE
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    steps = [("FY24 EBITDA", 120, "total"), ("Price", 18, "delta"), ("Volume", 9, "delta"), ("Mix", -4, "delta"),
             ("Procurement", 12, "delta"), ("Wage inflation", -15, "delta"), ("Other", -3, "delta"),
             ("FY25 EBITDA", None, "total")]
    run, base, inc, dec, tot, levels = 0, [], [], [], [], []
    for name, v, kind in steps:
        if kind == "total":
            v = run if v is None else v
            run = v
            base.append(0), inc.append(None), dec.append(None), tot.append(v)
        elif v >= 0:
            base.append(run), inc.append(v), dec.append(None), tot.append(None)
            run += v
        else:
            run += v
            base.append(run), inc.append(None), dec.append(-v), tot.append(None)
        levels.append(run)
    start, end = steps[0][1], levels[-1]
    growth = pct_change(start, end)
    # Sticker zone (top right) is reserved, so the title gets the remaining width.
    top = title_block(sl, s, f"EBITDA grows {growth:.0%} to ${end}M as price and procurement more than offset "
                             f"wage inflation", sub="EBITDA bridge, FY24 to FY25, $M", rule=True,
                      width=Inches(10.3))
    cd = CategoryChartData()
    cd.categories = [n for n, _, _ in steps]
    for nm, vals in (("base", base), ("total", tot), ("increase", inc), ("decrease", dec)):
        cd.add_series(nm, vals)
    x, y, w = Inches(0.45), top + Inches(0.3), Inches(12.4)
    h = Inches(6.75) - y
    vmax = 160
    gf = sl.shapes.add_chart(XL_CHART_TYPE.COLUMN_STACKED, x, y, w, h, cd)
    ch = gf.chart
    ch.has_legend = False
    ch.has_title = False
    plot = ch.plots[0]
    plot.gap_width = 55
    plot.overlap = 100
    fills = [None, "#14284B", "#1F6FD1", "#C0392B"]
    for ser, f in zip(plot.series, fills):
        if f is None:
            ser.format.fill.background()
            ser.format.line.fill.background()
        else:
            ser.format.fill.solid()
            ser.format.fill.fore_color.rgb = rgb(f)
    style_axes(ch, s, vmax=vmax, major=40, num_fmt="#,##0", show_value_axis=False, size=12)
    box = fix_plot_area(ch, x, y, w, h, 0.01, 0.08, 0.98, 0.82, n=len(steps), vmax=vmax)
    bw = box.bar_width(55)
    for i, (name, v, kind) in enumerate(steps):
        top_val = levels[i] if kind == "total" or (v or 0) >= 0 else levels[i] - v
        label = f"{levels[i]}" if kind == "total" else f"{v:+d}"
        color = {"total": s.ink, "pos": "#1F6FD1", "neg": "#C0392B"}[
            "total" if kind == "total" else ("pos" if v >= 0 else "neg")]
        text(sl, box.cat_center(i) - Inches(0.6), box.val(top_val) - Inches(0.32), Inches(1.2), Inches(0.28),
             label, size=14, bold=True, color=color, align=PP_ALIGN.CENTER)
        if i < len(steps) - 1:
            yl = box.val(levels[i])
            line(sl, box.cat_center(i) + bw // 2, yl, box.cat_center(i + 1) - bw // 2, yl, "#7F8A99", 0.75)
    sticker = rect(sl, Inches(11.0), Inches(0.5), Inches(1.85), Inches(0.38), "#FFFFFF",
                   line=("#C0392B", 1.25), shape=MSO_SHAPE.RECTANGLE, name="DF_ILLUSTRATIVE_1")
    tf = sticker.text_frame
    tf.text = "ILLUSTRATIVE"
    run_ = tf.paragraphs[0].runs[0]
    run_.font.size, run_.font.bold, run_.font.name = Pt(12), True, "Arial"
    run_.font.color.rgb = rgb("#C0392B")
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    footer(sl, s, "Note: dummy data, replace via the data workbook. Source: DeckForge visual spike", 4)


def lint_overlaps(prs, tol=Inches(0.02)):
    """Geometry lint (QA-5 deterministic): measured text extents and stickers must not intersect."""
    issues = []
    for n, slide in enumerate(prs.slides, 1):
        items = PLACED.get(slide.slide_id, [])
        for i, (na, xa, ya, wa, ha) in enumerate(items):
            if ya + ha > SLIDE_H or xa + wa > SLIDE_W:
                issues.append(f"slide {n}: '{na}' runs off the slide")
            for nb, xb, yb, wb, hb in items[i + 1:]:
                if (xa + tol < xb + wb and xb + tol < xa + wa and ya + tol < yb + hb and yb + tol < ya + ha):
                    issues.append(f"slide {n}: '{na}' overlaps '{nb}'")
    return issues


def main():
    OUT.mkdir(exist_ok=True)
    prs = Presentation()
    prs.slide_width, prs.slide_height = SLIDE_W, SLIDE_H
    slide_bain_bar(prs)
    slide_bain_two_panel(prs)
    slide_mck_likert(prs)
    slide_house_waterfall(prs)
    issues = lint_overlaps(prs)
    print("lint:", "clean" if not issues else "\n  " + "\n  ".join(issues))
    path = OUT / "visual_proof.pptx"
    prs.save(path)
    print(path)


if __name__ == "__main__":
    main()
