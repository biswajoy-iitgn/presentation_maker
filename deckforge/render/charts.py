"""Native PowerPoint charts styled from tokens, with pinned plot areas so overlays are computable."""

from __future__ import annotations

from dataclasses import dataclass

from lxml import etree
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_TICK_LABEL_POSITION, XL_TICK_MARK
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from deckforge.render.canvas import Canvas, rgb


@dataclass
class PlotBox:
    """Absolute inner plot rectangle. Fixed through manualLayout, so bar positions are known."""
    x: int
    y: int
    w: int
    h: int
    n: int
    vmax: float
    vmin: float = 0.0
    horizontal: bool = False

    def cat_width(self) -> int:
        return int((self.h if self.horizontal else self.w) / self.n)

    def cat_center(self, i: int) -> int:
        origin = self.y if self.horizontal else self.x
        return int(origin + (i + 0.5) * self.cat_width())

    def bar_width(self, gap_pct: int) -> int:
        return int(self.cat_width() / (1 + gap_pct / 100))

    def val(self, v: float) -> int:
        frac = (v - self.vmin) / (self.vmax - self.vmin)
        return int(self.x + frac * self.w) if self.horizontal else int(self.y + self.h * (1 - frac))


def pin_plot_area(chart, frame, fx, fy, fw, fh, **kw) -> PlotBox:
    x, y, w, h = frame
    plot_area = chart._chartSpace.find(".//" + qn("c:plotArea"))
    old = plot_area.find(qn("c:layout"))
    if old is not None:
        plot_area.remove(old)
    layout = etree.Element(qn("c:layout"))
    plot_area.insert(0, layout)
    ml = etree.SubElement(layout, qn("c:manualLayout"))
    for tag, val in (("layoutTarget", "inner"), ("xMode", "edge"), ("yMode", "edge"),
                     ("x", fx), ("y", fy), ("w", fw), ("h", fh)):
        etree.SubElement(ml, qn(f"c:{tag}")).set("val", str(val))
    return PlotBox(int(x + fx * w), int(y + fy * h), int(fw * w), int(fh * h), **kw)


def _base(c: Canvas, kind, frame, cats, series: dict[str, list], size=12):
    cd = CategoryChartData()
    cd.categories = cats
    for name, vals in series.items():
        cd.add_series(name, vals)
    chart = c.slide.shapes.add_chart(kind, *frame, cd).chart
    chart.has_legend = False
    chart.has_title = False
    chart.font.name = c.theme.body_font
    chart.font.size = Pt(size)
    chart.font.color.rgb = rgb(c.theme.ink)
    return chart


def _value_axis(chart, c: Canvas, vmax, major, num_fmt, visible=True):
    va = chart.value_axis
    va.minimum_scale, va.maximum_scale, va.major_unit = 0, vmax, major
    va.has_major_gridlines = False
    va.major_tick_mark = XL_TICK_MARK.NONE
    va.format.line.fill.background()
    va.tick_labels.number_format = num_fmt
    va.tick_labels.number_format_is_linked = False
    if not visible:
        va.tick_label_position = XL_TICK_LABEL_POSITION.NONE


def _category_axis(chart, c: Canvas, labels=True):
    ca = chart.category_axis
    ca.major_tick_mark = XL_TICK_MARK.NONE
    ca.format.line.color.rgb = rgb(c.theme.rule)
    ca.format.line.width = Pt(0.75)
    if not labels:
        ca.tick_label_position = XL_TICK_LABEL_POSITION.NONE
    return ca


def label_number_format(data_label, fmt):
    """Point-level number format, which python-pptx only exposes per series."""
    dlbl = data_label._get_or_add_dLbl()
    for old in dlbl.findall(qn("c:numFmt")):
        dlbl.remove(old)
    nf = etree.Element(qn("c:numFmt"), formatCode=fmt, sourceLinked="0")
    for tag in ("c:spPr", "c:txPr", "c:dLblPos", "c:showLegendKey", "c:showVal"):
        anchor = dlbl.find(qn(tag))
        if anchor is not None:
            anchor.addprevious(nf)
            return
    dlbl.append(nf)


def top_tick_format(vmax, prefix="", suffix="") -> str:
    """Unit shown once on the top tick, the consulting convention ('$1,200B', then bare numbers)."""
    return f'[={vmax}]"{prefix}"#,##0"{suffix}";#,##0'


def short_years(years) -> list[str]:
    return [str(y) if i == 0 else f"{y % 100:02d}" for i, y in enumerate(years)]


def column_chart(c: Canvas, frame, cats, values, *, vmax, major, num_fmt, gap=60, hero=(),
                 hero_fmt=None, plot=(0.08, 0.05, 0.9, 0.85), axis=True) -> PlotBox:
    chart = _base(c, XL_CHART_TYPE.COLUMN_CLUSTERED, frame, cats, {"Value": values})
    p = chart.plots[0]
    p.gap_width = gap
    ser = p.series[0]
    ser.format.fill.solid()
    ser.format.fill.fore_color.rgb = rgb(c.theme.neutral)
    _value_axis(chart, c, vmax, major, num_fmt, visible=axis)
    _category_axis(chart, c)
    for i in hero:
        pt = ser.points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = rgb(c.theme.accent)
        if hero_fmt:
            dl = pt.data_label
            dl.position = XL_LABEL_POSITION.OUTSIDE_END
            dl.show_value = True
            dl.font.size = Pt(18)
            dl.font.bold = True
            dl.font.color.rgb = rgb(c.theme.accent)
            label_number_format(dl, hero_fmt)
    return pin_plot_area(chart, frame, *plot, n=len(cats), vmax=vmax)


def stacked_bar_100(c: Canvas, frame, rows: list[list[float] | None], series_names, colors, *,
                    label_colors, gap=30) -> PlotBox:
    """Horizontal 100% stacked bars (Likert style). None rows become category gaps."""
    cats = [f"r{i}" for i in range(len(rows))]
    series = {name: [r[k] if r else None for r in rows] for k, name in enumerate(series_names)}
    chart = _base(c, XL_CHART_TYPE.BAR_STACKED_100, frame, cats, series)
    plot = chart.plots[0]
    plot.gap_width = gap
    plot.overlap = 100
    ca = _category_axis(chart, c, labels=False)
    ca.reverse_order = True
    chart.value_axis.visible = False
    chart.value_axis.has_major_gridlines = False
    for ser, col, lc in zip(plot.series, colors, label_colors):
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = rgb(col)
        ser.format.line.color.rgb = rgb(c.theme.paper)
        ser.format.line.width = Pt(1)
        ser.data_labels.show_value = True
        ser.data_labels.position = XL_LABEL_POSITION.CENTER
        ser.data_labels.font.size = Pt(12)
        ser.data_labels.font.color.rgb = rgb(lc)
    return pin_plot_area(chart, frame, 0.0, 0.0, 1.0, 1.0, n=len(rows), vmax=100, horizontal=True)


def waterfall(c: Canvas, frame, steps: list[tuple[str, float | None, str]], *, vmax, gap=55,
              label_size=14, higher_is_better=True) -> tuple[PlotBox, list[float]]:
    """Bridge as a native stacked column with an invisible base series.

    steps: (label, value, kind) with kind 'total' or 'delta'. A total with value None closes the bridge.
    higher_is_better: False for cost bridges, so reductions take the favourable colour.
    Returns the plot box and the running level after each step.
    """
    good, bad = c.theme.accent, c.theme.negative
    up, down = (good, bad) if higher_is_better else (bad, good)
    run, base, inc, dec, tot, levels = 0.0, [], [], [], [], []
    for _, v, kind in steps:
        if kind == "total":
            run = run if v is None else v
            base.append(0), inc.append(None), dec.append(None), tot.append(run)
        elif v >= 0:
            base.append(run), inc.append(v), dec.append(None), tot.append(None)
            run += v
        else:
            run += v
            base.append(run), inc.append(None), dec.append(-v), tot.append(None)
        levels.append(run)
    chart = _base(c, XL_CHART_TYPE.COLUMN_STACKED, frame, [s[0] for s in steps],
                  {"base": base, "total": tot, "increase": inc, "decrease": dec})
    plot = chart.plots[0]
    plot.gap_width = gap
    plot.overlap = 100
    for ser, fill in zip(plot.series, (None, c.theme.ink, up, down)):
        if fill is None:
            ser.format.fill.background()
            ser.format.line.fill.background()
        else:
            ser.format.fill.solid()
            ser.format.fill.fore_color.rgb = rgb(fill)
    _value_axis(chart, c, vmax, vmax / 4, "#,##0", visible=False)
    _category_axis(chart, c)
    box = pin_plot_area(chart, frame, 0.01, 0.1, 0.98, 0.8, n=len(steps), vmax=vmax)
    bw = box.bar_width(gap)
    for i, (_, v, kind) in enumerate(steps):
        is_total = kind == "total"
        top = levels[i] if is_total or v >= 0 else levels[i] - v
        label = f"{levels[i]:,.0f}" if is_total else f"{v:+,.0f}"
        color = c.theme.ink if is_total else (up if v >= 0 else down)
        c.text(box.cat_center(i) - Inches(0.6), box.val(top) - Inches(0.32), Inches(1.2), Inches(0.28),
               label, size=label_size, bold=True, color=color, align=PP_ALIGN.CENTER, name=f"wf_label_{i}")
        if i < len(steps) - 1:
            yl = box.val(levels[i])
            c.line(box.cat_center(i) + bw // 2, yl, box.cat_center(i + 1) - bw // 2, yl, c.theme.muted, 0.75)
    return box, levels
