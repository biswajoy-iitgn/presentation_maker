"""Plan + data + facts -> deck in a style family. Chooses each exhibit with the selector and records why."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from PIL import Image
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches

from deckforge.assets.sources import illustration, procedural
from deckforge.render import metrics
from deckforge.render.canvas import Canvas, Deck
from deckforge.story.plan import Plan, Slide, resolve, untracked_numbers
from deckforge.viz import frame as F
from deckforge.viz import marks as M
from deckforge.viz import style as S
from deckforge.viz.exhibits import benchmark, bridge, gantt, gapbars, geomap, matrix, pool, table, time
from deckforge.viz.scale import fmt_inr_cr, fmt_num, fmt_pct
from deckforge.viz.select import Candidate, choose, profile_of

FORMATS: dict[str, Callable[[float], str]] = {
    "pct0": lambda v: fmt_pct(v, 0),
    "pct1": lambda v: fmt_pct(v, 1),
    "bps_from_pct": lambda v: fmt_num(v * 100, 0, sign=True),
    "pp1": lambda v: fmt_num(v, 1, suffix=" pp", sign=True),
    "inr_cr": lambda v: fmt_inr_cr(v),
    "inr_cr_signed": lambda v: fmt_inr_cr(v, sign=True),
    "num0": lambda v: fmt_num(v, 0),
    "num1": lambda v: fmt_num(v, 1),
    "kt": lambda v: fmt_num(v, 0, suffix=" kt"),
}


@dataclass
class Decision:
    slide: str
    analysis: str | None
    archetype: str = ""
    layout: str = ""
    candidates: list[Candidate] = field(default_factory=list)
    chosen: str = ""
    title_warnings: list[str] = field(default_factory=list)


def _fmt(spec: str | None) -> Callable[[float], str]:
    return FORMATS[spec or "num0"]


# ----------------------------------------------------------------------------- family imagery
def family_image(style: str, w: int, h: int, seed: int = 0) -> Image.Image:
    f = S.ACTIVE
    if style == "factory":
        return illustration.factory(w, h, base="#EEF2F8", accent=f.accent, accent2=f.accent2, glass=f.accent_light,
                                    ground=f.glow[1], tree=f.accent2 if f.name == "verdant" else "#5CC896")
    palettes = {
        "motion_streaks": (f.glow[0], f.glow[2], "#EEF4FF"),
        "light_arcs": f.glow,
        "aurora": (f.glow[0], f.glow[1], f.accent2),
        "light_planes": ("#C9CEDB", "#DDE1EA", "#F7F8FB"),
        "contours": ("#FFFFFF", "#DCE1EA"),
    }
    return procedural.STYLES[style](w=w, h=h, palette=palettes[style], seed=seed)


class Imagery:
    """One band image per section, so a chapter shares its imagery as firm decks do."""

    def __init__(self):
        self._bands: dict[int, Image.Image] = {}

    def band(self, section: int) -> Image.Image:
        if section not in self._bands:
            self._bands[section] = family_image(S.ACTIVE.band_style, 1920, 210, seed=11 + section * 7)
        return self._bands[section]


def render(plan: Plan, data: dict, facts: dict, *, allowed_numbers: set[str],
           family: str | None = None) -> tuple[Deck, list[Decision]]:
    from deckforge.tokens import MERIDIAN
    S.use(family or plan.family)
    deck = Deck(MERIDIAN)
    imagery = Imagery()
    decisions = []
    for s in plan.slides:
        d = Decision(s.id, s.analysis, archetype=s.archetype)
        d.title_warnings = untracked_numbers(s.title, allowed_numbers)
        title = resolve(s.title, facts)
        c = deck.new_slide()
        if s.archetype == "cover":
            _cover(c, title, s, facts)
            d.layout = "cover"
        elif s.archetype == "agenda":
            _agenda(c, plan, s, title)
            d.layout = "agenda"
        elif s.archetype == "exec_summary":
            _exec_summary(c, plan, s, title, facts, imagery)
            d.layout = "exec_summary"
        elif s.archetype == "decisions":
            _decision_cards(c, plan, s, title, facts, imagery)
            d.layout = "cards"
        else:
            a = plan.analysis(s.analysis)
            ds = data[a.dataset]
            d.candidates = choose(a.message_type, profile_of(ds), audience=plan.audience)
            d.chosen = s.exhibit if s.exhibit != "auto" else d.candidates[0].exhibit
            side = "kpis" if s.kpis else ("commentary" if s.points else "full")
            d.layout = f"{d.chosen}+{side}"
            _exhibit_slide(c, plan, s, title, ds, d.chosen, facts, imagery)
        decisions.append(d)
    return deck, decisions


def _band_for(s: Slide, imagery: Imagery):
    use = s.header == "band" or (s.header == "auto" and S.ACTIVE.header == "band")
    return imagery.band(s.section or 0) if use else None


def _frame(c: Canvas, plan: Plan, s: Slide, title: str, facts: dict, imagery: Imagery) -> F.Box:
    return F.slide(c, title, sections=plan.sections, active=s.section, source=resolve(s.source, facts),
                   notes=[resolve(n, facts) for n in s.notes], band=_band_for(s, imagery))


# ----------------------------------------------------------------------------- archetypes
def _cover(c: Canvas, title: str, s: Slide, facts: dict):
    f = S.ACTIVE
    W, H = c.deck.width, c.deck.height
    c.rect(-Inches(0.05), -Inches(0.05), W + Inches(0.1), H + Inches(0.1), f.glow[0], name="cover_bg")
    art = family_image(f.cover_style, 1600, 1200)
    c.picture(art, Inches(5.6), Inches(0.9), Inches(8.0), Inches(6.0), name="cover_art", fmt="PNG")
    c.rect(Inches(0.75), Inches(2.35), Inches(0.9), Inches(0.07), f.accent2, name="cover_rule")
    M.label(c, Inches(0.75), Inches(2.65), Inches(5.6), Inches(2.4), title, size=40, font=S.TITLE_FONT, bold=True,
            color="#FFFFFF", name="DF_title")
    if s.subtitle:
        M.label(c, Inches(0.75), Inches(5.0), Inches(5.6), Inches(0.4), resolve(s.subtitle, facts), size=15,
                color="#C9D3E0", name="cover_sub")
    for i, line in enumerate(s.notes):
        M.label(c, Inches(0.75), Inches(6.6) + Inches(0.22) * i, Inches(6), Inches(0.22), line, size=10,
                color="#9AA8BC", name=f"cover_note_{i}")


def _agenda(c: Canvas, plan: Plan, s: Slide, title: str):
    f = S.ACTIVE
    H = c.deck.height
    pw = Inches(4.9)
    c.picture(family_image("aurora", 700, 1080, seed=5), 0, 0, pw, H, name="agenda_panel")
    c.rect(Inches(0.5), Inches(0.8), pw - Inches(1.0), Inches(2.4), f.glow[0], alpha=0.78, name="agenda_box")
    M.label(c, Inches(0.85), Inches(1.15), pw - Inches(1.7), Inches(1.2), title, size=26, font=S.TITLE_FONT,
            bold=True, color="#FFFFFF", name="agenda_title")
    M.label(c, Inches(0.85), Inches(2.5), pw - Inches(1.7), Inches(0.35), "AGENDA", size=13, bold=True,
            color="#9EE6C1" if f.name == "verdant" else "#7DD3FC", name="agenda_label")
    questions = [ch.question for ch in plan.issue_tree.children]
    x0, y0, step = pw + Inches(0.8), Inches(1.35), Inches(1.32)
    M.vline(c, x0 + Inches(0.3), y0 + Inches(0.3), y0 + step * (len(plan.sections) - 1) + Inches(0.3), S.RULE, 1.25)
    for i, sec in enumerate(plan.sections):
        y = y0 + step * i
        on = i == s.section
        M.dot(c, x0 + Inches(0.3), y + Inches(0.3), Inches(0.6), S.ACCENT if on else "#FFFFFF",
              ring=None if on else S.NEUTRAL, register=True)
        M.label(c, x0, y + Inches(0.06), Inches(0.6), Inches(0.5), str(i + 1), size=18, bold=True,
                color="#FFFFFF" if on else S.MUTED, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
                name=f"agenda_num_{i}")
        M.label(c, x0 + Inches(0.85), y + Inches(0.02), Inches(6.2), Inches(0.36), sec, size=20, bold=True,
                color=S.ACCENT if on else S.INK, name=f"agenda_item_{i}")
        if i < len(questions):
            M.label(c, x0 + Inches(0.85), y + Inches(0.42), Inches(6.2), Inches(0.5), questions[i], size=13,
                    color=S.TEXT2, name=f"agenda_q_{i}")


def _exec_summary(c: Canvas, plan: Plan, s: Slide, title: str, facts: dict, imagery: Imagery):
    box = _frame(c, plan, s, title, facts, imagery)
    n = len(s.rows)
    gap = Inches(0.12)
    row_h = (box.h - gap * (n - 1)) / n
    block_w, kpi_w = Inches(2.35), Inches(2.4)
    for i, row in enumerate(s.rows):
        y = box.y + (row_h + gap) * i
        c.rect(box.x, int(y), block_w, int(row_h), S.ACCENT_LIGHT, name=f"es_block_{i}")
        M.icon_disc(c, row.get("icon", "circle-check"), box.x + Inches(0.42), y + row_h / 2, Inches(0.5))
        M.label(c, box.x + Inches(0.8), y, block_w - Inches(0.9), row_h, resolve(row["label"], facts), size=15,
                bold=True, color=S.ACCENT_DARK, anchor=MSO_ANCHOR.MIDDLE, name=f"es_label_{i}")
        body_x = box.x + block_w + Inches(0.3)
        body_w = box.r - body_x - kpi_w - Inches(0.2)
        content = [[(resolve(row["lead"], facts) + " ", True, S.INK), (resolve(row["text"], facts), False, S.TEXT2)]]
        M.label(c, body_x, y, body_w, row_h, content, size=13.5, anchor=MSO_ANCHOR.MIDDLE, name=f"es_body_{i}")
        if row.get("kpi"):
            kx = box.r - kpi_w
            M.vline(c, kx - Inches(0.1), y + Inches(0.12), y + row_h - Inches(0.12), S.RULE, 0.75)
            M.kpi(c, kx + Inches(0.1), y + row_h / 2 - Inches(0.48), kpi_w - Inches(0.1), resolve(row["kpi"], facts),
                  resolve(row.get("kpi_caption", ""), facts), size=28,
                  color=S.NEGATIVE if row.get("kpi_bad") else S.ACCENT, name=f"es_kpi_{i}")


def _decision_cards(c: Canvas, plan: Plan, s: Slide, title: str, facts: dict, imagery: Imagery):
    box = _frame(c, plan, s, title, facts, imagery)
    n = len(s.rows)
    gap = Inches(0.3)
    w = (box.w - gap * (n - 1)) / n
    head_h, pad = Inches(1.15), Inches(0.3)
    for i, row in enumerate(s.rows):
        x = box.x + (w + gap) * i
        c.rect(int(x), box.y, int(w), int(head_h), S.ACCENT_DARK, name=f"card_head_{i}")
        c.rect(int(x), box.y + head_h, int(w), int(box.h - head_h), S.PANEL, name=f"card_body_{i}")
        M.icon_disc(c, row.get("icon", "circle-check"), x + Inches(0.55), box.y + head_h / 2, Inches(0.62),
                    fill="#FFFFFF", color=S.ACCENT_DARK)
        M.label(c, x + Inches(1.05), box.y, w - Inches(1.2), head_h,
                [[(f"{i + 1}  ", True, "#FFFFFF"), (resolve(row["label"], facts), True, "#FFFFFF")]], size=20,
                anchor=MSO_ANCHOR.MIDDLE, name=f"card_label_{i}")
        body = [[(resolve(row["lead"], facts), True, S.INK)], [(resolve(row["text"], facts), False, S.TEXT2)]]
        fy = box.b - Inches(0.85)
        text_b = fy
        if row.get("kpi"):                    # what the decision unlocks: the number the board weighs
            cap = resolve(row.get("kpi_caption", ""), facts)
            kh = int(30 * 1.15 * 12700) + Inches(0.02) + metrics.text_height(cap, S.FONT, S.TYPE.label, False,
                                                                              int(w - 2 * pad))
            ky = fy - kh - Inches(0.3)
            M.hline(c, x + pad, x + w - pad, ky, S.RULE, 0.75)
            M.kpi(c, x + pad, ky + Inches(0.15), w - 2 * pad, resolve(row["kpi"], facts), cap, size=30,
                  name=f"card_kpi_{i}")
            text_b = ky
        M.label(c, x + pad, box.y + head_h + pad, w - 2 * pad, text_b - box.y - head_h - pad - Inches(0.1), body,
                size=15, name=f"card_text_{i}")
        M.hline(c, x + pad, x + w - pad, fy, S.RULE, 0.75)
        M.icon(c, "users", x + pad, fy + Inches(0.15), Inches(0.26), color=S.MUTED)
        M.label(c, x + pad + Inches(0.36), fy + Inches(0.1), w - 2 * pad, Inches(0.3), row.get("owner", ""), size=12,
                bold=True, name=f"card_owner_{i}")
        M.icon(c, "flag", x + pad, fy + Inches(0.47), Inches(0.26), color=S.MUTED)
        M.label(c, x + pad + Inches(0.36), fy + Inches(0.42), w - 2 * pad, Inches(0.3), row.get("when", ""), size=12,
                color=S.TEXT2, name=f"card_when_{i}")


def _exhibit_slide(c: Canvas, plan: Plan, s: Slide, title: str, ds: dict, exhibit: str, facts: dict,
                   imagery: Imagery):
    box = _frame(c, plan, s, title, facts, imagery)
    if s.points or s.kpis:
        left, right = box.split_x(0.7 if s.points else 0.74)
    else:
        left, right = box, None
    F.exhibit_header(c, left, s.exhibit_title or "", s.exhibit_unit, sticker=s.sticker)
    area = F.Box(left.x, left.y + Inches(0.1), left.w, left.h - Inches(0.1))
    anchors = EXHIBITS[exhibit](c, area, ds, s, facts)
    if right is None:
        return
    if s.kpis:
        F.kpi_sidebar(c, F.Box(right.x, box.y - Inches(0.43), right.w, box.h + Inches(0.43)),
                      [(resolve(k.value, facts), resolve(k.caption, facts)) for k in s.kpis])
        return
    marks, n = [], 0
    for p in s.points:
        if p.target is not None and anchors and p.target in anchors:
            n += 1
            x, y = anchors[p.target]
            M.marker(c, x, y, n)
            marks.append(n)
        else:
            marks.append(p.icon)
    F.commentary(c, right, s.commentary_head or "Key insights",
                 [(m, resolve(p.lead, facts), resolve(p.text, facts)) for m, p in zip(marks, s.points)])


# ----------------------------------------------------------------------------- exhibit adapters
def _ex_waterfall(c, area, ds, s, facts):
    steps = [bridge.Step(x["label"], x.get("value"), x.get("kind", "delta")) for x in ds["steps"]]
    emph = {int(e) for e in s.emphasis} if s.emphasis else None
    brackets = [(b[0], b[1], resolve(b[2], facts)) for b in ds.get("brackets", [])]
    bench = (ds["benchmark"][0], resolve(ds["benchmark"][1], facts)) if ds.get("benchmark") else None
    icons = {int(k): v for k, v in ds.get("icons", {}).items()} or None
    a = bridge.waterfall(c, area, steps, fmt_total=_fmt(ds.get("fmt_total")), fmt_delta=_fmt(ds.get("fmt_delta")),
                         higher_is_better=ds.get("higher_is_better", True), floor=ds.get("floor"),
                         brackets=brackets, benchmark=bench, emphasis=emph, icons=icons)
    return {i: b.marker_point() for i, b in a.items()}


def _ex_columns_over_line(c, area, ds, s, facts):
    a = time.columns_over_line(c, area, ds["periods"], ds["columns"]["values"], ds["line"]["values"],
                               col_title=ds["columns"]["title"], line_title=ds["line"]["title"],
                               fmt_col=_fmt(ds["columns"]["fmt"]), fmt_line=_fmt(ds["line"]["fmt"]),
                               growth_label=resolve(ds.get("growth_label", ""), facts) or None,
                               change_label=resolve(ds.get("change_label", ""), facts) or None)
    out = {f"col:{i}": (x + Inches(0.45), y + Inches(0.12)) for i, (x, y) in enumerate(a["columns"])}
    out.update({f"line:{i}": (x + Inches(0.25), y + Inches(0.32)) for i, (x, y) in enumerate(a["line"])})
    return out


def _ex_profit_pool(c, area, ds, s, facts):
    segs = [pool.Segment(x["name"], x["size"], x["rate"]) for x in ds["segments"]]
    avg = (ds["average"][0], resolve(ds["average"][1], facts)) if ds.get("average") else None
    a = pool.profit_pool(c, area, segs, highlight=set(s.emphasis), fmt_rate=_fmt(ds.get("fmt_rate")),
                         fmt_profit=_fmt(ds.get("fmt_profit")), average=avg, x_title=ds.get("x_title", ""),
                         y_title=ds.get("y_title", ""), icons=ds.get("icons"))
    return {k: (x - Inches(0.2), y - Inches(0.14)) for k, (x, y) in a.items()}


def _ex_range_benchmark(c, area, ds, s, facts):
    kpis = [benchmark.KPI(k["name"], k["unit"], k["ours"], k["lo"], k["q1"], k["median"], k["q3"], k["hi"],
                          k["higher_is_better"], _fmt(k["fmt"])) for k in ds["kpis"]]
    a = benchmark.range_benchmark(c, area, kpis, ours_label=ds["ours_label"], peers_label=ds["peers_label"],
                                  fmt_gap=lambda k: fmt_num(k.gap() / k.median * 100, 0, suffix="%", sign=True))
    return {k: (x + Inches(0.52), y - Inches(0.26)) for k, (x, y) in a.items()}


def _ex_gap_bars(c, area, ds, s, facts):
    rows = [{"name": k["name"], "unit": k["unit"], "icon": k.get("icon", "gauge"), "ours": k["ours"],
             "bench": k["median"], "higher_is_better": k["higher_is_better"], "fmt": k["fmt"]} for k in ds["kpis"]]
    return gapbars.gap_bars(c, area, rows, ours_label=ds["ours_label"], fmt=FORMATS)


def _ex_site_map(c, area, ds, s, facts):
    med = ds["y_ref"][0]
    sites = [{"name": p["label"], "lat": p["lat"], "lon": p["lon"], "size": p["size"],
              "value": (p["y"] - med) * p["size"] / 10, "note": p.get("map_note", p.get("note", ""))}
             for p in ds["points"]]
    return geomap.site_map(c, area, country=ds["country"], sites=sites, value_title=ds["gap_title"],
                           fmt_value=FORMATS["inr_cr_signed"], size_note=ds.get("map_size_note", ""),
                           highlight=set(s.emphasis), label_side=ds.get("map_label_side"),
                           hot_color={"negative": S.NEGATIVE}.get(ds.get("emphasis_color", ""), S.ACCENT))


def _points(ds):
    return [matrix.Point(p["label"], p["x"], p["y"], p["size"], p.get("highlight", False), p.get("note", ""),
                         p.get("icon", "")) for p in ds["points"]]


def _ex_bubble(c, area, ds, s, facts, quadrants=None, shade=None):
    pts = _points(ds)
    for p in pts:
        p.highlight = p.highlight or p.label in s.emphasis
    xr = (ds["x_ref"][0], resolve(ds["x_ref"][1], facts)) if ds.get("x_ref") else None
    yr = (ds["y_ref"][0], resolve(ds["y_ref"][1], facts)) if ds.get("y_ref") else None
    a = matrix.bubble_matrix(c, area, pts, x_title=ds["x_title"], y_title=ds["y_title"], fmt_x=_fmt(ds["fmt_x"]),
                             fmt_y=_fmt(ds["fmt_y"]), x_ref=xr, y_ref=yr,
                             quadrants=quadrants or ds.get("quadrants"), shade=shade or ds.get("shade"),
                             invert_y=ds.get("invert_y", False),
                             domain_x=tuple(ds["domain_x"]) if ds.get("domain_x") else None,
                             domain_y=tuple(ds["domain_y"]) if ds.get("domain_y") else None,
                             size_note=ds.get("size_note", ""), label_side=ds.get("label_side"))
    return {k: v[3] for k, v in a.items()}


def _ex_heat(c, area, ds, s, facts):
    outline = {tuple(x) for x in ds.get("outline", [])}
    table.heat_table(c, area, ds["rows"], ds["cols"], ds["values"], fmt=_fmt(ds.get("fmt")),
                     row_head=ds.get("row_head", ""), row_notes=ds.get("row_notes"), outline=outline,
                     row_icons=ds.get("row_icons"))
    return {}


def _ex_roadmap(c, area, ds, s, facts):
    tasks = [gantt.Task(t["name"], t["wave"], t["start"], t["end"], resolve(t.get("note", ""), facts))
             for t in ds["tasks"]]
    gantt.roadmap(c, area, tasks, ds["waves"], months=ds.get("months", 24),
                  milestones=[(m[0], resolve(m[1], facts)) for m in ds.get("milestones", [])],
                  wave_icons=ds.get("wave_icons"))
    return {}


EXHIBITS = {
    "waterfall": _ex_waterfall,
    "columns_over_line": _ex_columns_over_line,
    "profit_pool": _ex_profit_pool,
    "range_benchmark": _ex_range_benchmark,
    "gap_bars": _ex_gap_bars,
    "site_map": _ex_site_map,
    "bubble_matrix": _ex_bubble,
    "priority_matrix": lambda c, a, ds, s, f: _ex_bubble(
        c, a, ds, s, f, quadrants={"tr": "Quick wins", "tl": "Major projects", "br": "Fill-ins",
                                   "bl": "Deprioritise"}, shade="tr"),
    "heat_table": _ex_heat,
    "roadmap": _ex_roadmap,
}


def report(plan: Plan, decisions: list[Decision], facts: dict, lookfeel=None, consistency=None) -> str:
    """Markdown trace of the reasoning: problem, issue tree, analyses, each exhibit decision, look and feel."""
    out = [f"# Plan report: {plan.brief_id}", "", f"Produced by: {plan.produced_by}", "",
           f"Audience: {plan.audience}. Style family: {S.ACTIVE.name} ({S.ACTIVE.inspired_by}).", "",
           "## Problem", "", f"**Key question.** {plan.problem.key_question}", "",
           f"**Decision maker.** {plan.problem.decision_maker}", "",
           "**Success criteria.** " + ", ".join(plan.problem.success_criteria), "", "## Issue tree", ""]

    def walk(node, depth=0):
        hyp = f" *Hypothesis: {node.hypothesis}*" if node.hypothesis else ""
        out.append(f"{'  ' * depth}- **{node.id}** {node.question}{hyp}")
        for ch in node.children:
            walk(ch, depth + 1)
    walk(plan.issue_tree)
    out += ["", "## Storyline", "", f"**Governing thought.** {resolve(plan.governing_thought, facts)}", "",
            f"- Situation: {resolve(plan.situation, facts)}", f"- Complication: {resolve(plan.complication, facts)}",
            f"- Resolution: {resolve(plan.resolution, facts)}", "", "## Analyses", "",
            "| Analysis | Answers | Framework | Message type | Data | Why this framework |", "|---|---|---|---|---|---|"]
    for a in plan.analyses:
        out.append(f"| {a.name} | {a.issue} | {a.framework} | {a.message_type} | {a.data_status} | {a.why} |")
    out += ["", "## Slide layouts", "", "| Slide | Archetype | Layout |", "|---|---|---|"]
    for d in decisions:
        out.append(f"| {d.slide} | {d.archetype} | {d.layout} |")
    out += ["", "## Exhibit decisions", ""]
    for d in decisions:
        if not d.candidates:
            continue
        out += [f"### {d.slide}: {d.chosen}", "", "| Candidate | Score | Reasons |", "|---|---|---|"]
        for cnd in d.candidates:
            mark = " (chosen)" if cnd.exhibit == d.chosen else ""
            out.append(f"| {cnd.exhibit}{mark} | {cnd.score:.2f} | {' / '.join(cnd.reasons)} |")
        if d.title_warnings:
            out.append(f"\nTitle contains typed numbers not from data: {', '.join(d.title_warnings)}")
        out.append("")
    if lookfeel is not None:
        out += ["## Look and feel gate", "", lookfeel.markdown()]
    if consistency is not None:
        out += ["", "## Storyline consistency across exhibits", ""]
        out += [f"- {x}" for x in consistency] or ["- no contradictions between the prioritisation matrix and the roadmap"]
    return "\n".join(out)
