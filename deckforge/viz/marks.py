"""Drawing primitives for shape-built exhibits. Thin marks, no borders, text in ink tokens."""

from __future__ import annotations

from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from deckforge.render.canvas import Canvas, rgb
from deckforge.viz import style as S

GAP = Inches(0.028)      # surface gap between adjacent fills (about 2 px at slide scale)


def bar(c: Canvas, x, y, w, h, color, name=None, register=True):
    """Filled rectangle without border. Negative heights are normalised.
    Registered as a fill so the legibility lint checks text drawn on it."""
    if h < 0:
        y, h = y + h, -h
    if w < 0:
        x, w = x + w, -w
    return c.rect(int(x), int(y), max(1, int(w)), max(1, int(h)), color, name=name, register=register)


def label(c: Canvas, x, y, w, h, s, *, size=S.TYPE.label, bold=False, color=S.INK, align=PP_ALIGN.LEFT,
          anchor=MSO_ANCHOR.TOP, name=None, font=S.FONT):
    return c.text(int(x), int(y), int(w), int(h), s, size=size, bold=bold, color=color, align=align, anchor=anchor,
                  name=name, font=font)


def centered_label(c: Canvas, cx, y, s, *, w=Inches(1.4), h=Inches(0.26), knockout=False, **kw):
    """knockout: white box sized to the text, so lines running behind the label do not cut through it."""
    if knockout and isinstance(s, str):
        from deckforge.render import metrics
        tw = int(metrics.text_width_pt(s, kw.get("font", S.FONT), kw.get("size", S.TYPE.label), kw.get("bold", False))
                 * 12700) + Inches(0.08)
        c.rect(int(cx - tw / 2), int(y + Inches(0.02)), tw, int(h - Inches(0.04)), "#FFFFFF", register=False)
    return label(c, cx - w // 2, y, w, h, s, align=PP_ALIGN.CENTER, **kw)


def hline(c: Canvas, x1, x2, y, color=S.RULE, width=0.75):
    return c.line(int(x1), int(y), int(x2), int(y), color, width)


def vline(c: Canvas, x, y1, y2, color=S.RULE, width=0.75):
    return c.line(int(x), int(y1), int(x), int(y2), color, width)


def dot(c: Canvas, cx, cy, d, color, ring=None, name=None):
    sp = c.rect(int(cx - d / 2), int(cy - d / 2), int(d), int(d), color, shape=MSO_SHAPE.OVAL, name=name,
                register=False, line=(ring, 1.5) if ring else None)
    return sp


def marker(c: Canvas, cx, cy, n: int, d=Inches(0.27), color=S.INK):
    """Numbered callout marker linking a chart element to commentary."""
    sp = dot(c, cx, cy, d, color, ring="#FFFFFF", name=f"callout_{n}")
    tf = sp.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.text = str(n)
    run = tf.paragraphs[0].runs[0]
    run.font.size, run.font.bold, run.font.name = Pt(10.5), True, S.FONT
    run.font.color.rgb = rgb("#FFFFFF")
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    return sp


def bracket_h(c: Canvas, x1, x2, y, label_text, *, up=True, color=S.INK, tick=Inches(0.08), size=S.TYPE.annotation,
              bold=True):
    """Horizontal bracket spanning x1..x2 with a centred label (above if up)."""
    t = -tick if up else tick
    c.line(int(x1), int(y + t), int(x1), int(y), color, 1.0)
    c.line(int(x1), int(y), int(x2), int(y), color, 1.0)
    c.line(int(x2), int(y), int(x2), int(y + t), color, 1.0)
    ly = y - Inches(0.3) if up else y + Inches(0.06)
    from deckforge.render import metrics
    tw = int(metrics.text_width_pt(label_text, S.FONT, size, bold) * 12700) + Inches(0.15)
    return centered_label(c, (x1 + x2) // 2, ly, label_text, w=max(tw, int(x2 - x1)), size=size, bold=bold,
                          color=color)


def arrow(c: Canvas, x1, y1, x2, y2, color=S.INK, width=1.0):
    return c.line(int(x1), int(y1), int(x2), int(y2), color, width, arrow_end=True)


def legend_row(c: Canvas, x, y, items: list[tuple[str, str]], size=S.TYPE.label, gap=Inches(0.25)):
    """Inline legend: small squares with labels, laid out left to right."""
    from deckforge.render import metrics
    cx = x
    for color, text in items:
        bar(c, cx, y + Inches(0.05), Inches(0.13), Inches(0.13), color)
        w = int(metrics.text_width_pt(text, S.FONT, size) * 12700) + Inches(0.1)
        label(c, cx + Inches(0.2), y, w, Inches(0.25), text, size=size, color=S.TEXT2)
        cx += Inches(0.2) + w + gap
    return cx
