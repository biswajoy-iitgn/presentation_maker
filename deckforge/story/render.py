"""Plan + data + facts -> deck. Chooses each exhibit with the selector and records why."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches

from deckforge.render import metrics
from deckforge.render.canvas import Canvas, Deck
from deckforge.story.plan import Plan, Slide, resolve, untracked_numbers
from deckforge.viz import frame as F
from deckforge.viz import marks as M
from deckforge.viz import style as S
from deckforge.viz.exhibits import benchmark, bridge, gantt, matrix, pool, table, time
from deckforge.viz.scale import fmt_inr_cr, fmt_num, fmt_pct
from deckforge.viz.select import Candidate, choose, profile_of

FORMATS: dict[str, Callable[[float], str]] = {
    "pct0": lambda v: fmt_pct(v, 0),
    "pct1": lambda v: fmt_pct(v, 1),
    "bps_from_pct": lambda v: fmt_num(v * 100, 0, sign=True),
    "pp1": lambda v: fmt_num(v, 1, suffix=" pp", sign=True),
    "inr_cr": lambda v: fmt_inr_cr(v),
    "num0": lambda v: fmt_num(v, 0),
    "num1": lambda v: fmt_num(v, 1),
    "kt": lambda v: fmt_num(v, 0, suffix=" kt"),
}


@dataclass
class Decision:
    slide: str
    analysis: str | None
    candidates: list[Candidate] = field(default_factory=list)
    chosen: str = ""
    title_warnings: list[str] = field(default_factory=list)


def _fmt(spec: str | None) -> Callable[[float], str]:
    return FORMATS[spec or "num0"]


def render(plan: Plan, data: dict, facts: dict, *, allowed_numbers: set[str]) -> tuple[Deck, list[Decision]]:
    from deckforge.tokens import MERIDIAN
    deck = Deck(MERIDIAN)
    decisions = []
    for s in plan.slides:
        d = Decision(s.id, s.analysis)
        d.title_warnings = untracked_numbers(s.title, allowed_numbers)
        title = resolve(s.title, facts)
        c = deck.new_slide()
        if s.archetype == "cover":
            _cover(c, title, s, facts)
        elif s.archetype == "exec_summary":
            _rows_slide(c, plan, s, title, facts, numbered=False)
        elif s.archetype == "decisions":
            _rows_slide(c, plan, s, title, facts, numbered=True)
        else:
            a = plan.analysis(s.analysis)
            ds = data[a.dataset]
            d.candidates = choose(a.message_type, profile_of(ds))
            d.chosen = s.exhibit if s.exhibit != "auto" else d.candidates[0].exhibit
            _exhibit_slide(c, plan, s, title, ds, d.chosen, facts)
        decisions.append(d)
    return deck, decisions


# ----------------------------------------------------------------------------- archetypes
def _cover(c: Canvas, title: str, s: Slide, facts: dict):
    W, H = c.deck.width, c.deck.height
    c.rect(-Inches(0.05), -Inches(0.05), W + Inches(0.1), H + Inches(0.1), S.INK, name="cover_bg")
    c.rect(Inches(0.9), Inches(2.55), Inches(0.9), Inches(0.06), S.ACCENT, name="cover_rule")
    M.label(c, Inches(0.9), Inches(2.85), Inches(9.5), Inches(1.9), title, size=40, font=S.TITLE_FONT, bold=True,
            color="#FFFFFF", name="DF_title")
    if s.subtitle:
        M.label(c, Inches(0.9), Inches(4.85), Inches(9), Inches(0.4), resolve(s.subtitle, facts), size=16,
                color="#B9C4D6", name="cover_sub")
    for i, line in enumerate(s.notes):
        M.label(c, Inches(0.9), Inches(6.55) + Inches(0.22) * i, Inches(9), Inches(0.22), line, size=10,
                color="#8796AD", name=f"cover_note_{i}")


def _rows_slide(c: Canvas, plan: Plan, s: Slide, title: str, facts: dict, numbered: bool):
    box = F.slide(c, title, sections=plan.sections, active=s.section, source=resolve(s.source, facts),
                  notes=[resolve(n, facts) for n in s.notes])
    n = len(s.rows)
    row_h = box.h / n
    label_w = Inches(2.6)
    for i, row in enumerate(s.rows):
        y = box.y + row_h * i
        if i:
            M.hline(c, box.x, box.r, y, S.RULE, 0.75)
        text_y = y + Inches(0.18)
        if numbered:
            M.label(c, box.x, text_y - Inches(0.08), Inches(0.8), Inches(0.8), str(i + 1), size=40, bold=True,
                    font=S.TITLE_FONT, color=S.ACCENT, name=f"row_num_{i}")
            lx = box.x + Inches(0.9)
        else:
            lx = box.x
        M.label(c, lx, text_y, label_w - (lx - box.x), row_h - Inches(0.3), resolve(row["label"], facts),
                size=14, bold=True, font=S.TITLE_FONT, color=S.INK, name=f"row_label_{i}")
        body_x = box.x + label_w + Inches(0.3)
        body_w = box.r - body_x - (Inches(2.4) if row.get("owner") else 0)
        content = [[(resolve(row["lead"], facts) + " ", True, S.INK), (resolve(row["text"], facts), False, S.TEXT2)]]
        M.label(c, body_x, text_y, body_w, row_h - Inches(0.3), content, size=14, name=f"row_body_{i}")
        if row.get("owner"):
            M.label(c, box.r - Inches(2.3), text_y, Inches(2.3), Inches(0.5),
                    [[(row["owner"], True, S.INK)], [(row.get("when", ""), False, S.MUTED)]], size=11,
                    align=PP_ALIGN.RIGHT, name=f"row_owner_{i}")


def _exhibit_slide(c: Canvas, plan: Plan, s: Slide, title: str, ds: dict, exhibit: str, facts: dict):
    box = F.slide(c, title, sections=plan.sections, active=s.section, source=resolve(s.source, facts),
                  notes=[resolve(n, facts) for n in s.notes])
    if s.points:
        left, right = box.split_x(0.69)
    else:
        left, right = box, None
    F.exhibit_header(c, left, s.exhibit_title or "", s.exhibit_unit, sticker=s.sticker)
    area = F.Box(left.x, left.y + Inches(0.08), left.w, left.h - Inches(0.08))
    anchors = EXHIBITS[exhibit](c, area, ds, s, facts)
    if right is not None:
        markers = []
        for i, p in enumerate(s.points, 1):
            if p.target is not None and anchors and p.target in anchors:
                x, y = anchors[p.target]
                M.marker(c, x, y, i)
                markers.append(i)
            else:
                markers.append(None)
        F.commentary(c, right, s.commentary_head or "Key insights",
                     [(n, resolve(p.lead, facts), resolve(p.text, facts)) for n, p in zip(markers, s.points)])


# ----------------------------------------------------------------------------- exhibit adapters
def _ex_waterfall(c, area, ds, s, facts):
    steps = [bridge.Step(x["label"], x.get("value"), x.get("kind", "delta")) for x in ds["steps"]]
    emph = {int(e) for e in s.emphasis} if s.emphasis else None
    brackets = [(b[0], b[1], resolve(b[2], facts)) for b in ds.get("brackets", [])]
    bench = (ds["benchmark"][0], resolve(ds["benchmark"][1], facts)) if ds.get("benchmark") else None
    a = bridge.waterfall(c, area, steps, fmt_total=_fmt(ds.get("fmt_total")), fmt_delta=_fmt(ds.get("fmt_delta")),
                         higher_is_better=ds.get("higher_is_better", True), floor=ds.get("floor"),
                         brackets=brackets, benchmark=bench, emphasis=emph)
    return {i: b.marker_point() for i, b in a.items()}


def _ex_columns_over_line(c, area, ds, s, facts):
    a = time.columns_over_line(c, area, ds["periods"], ds["columns"]["values"], ds["line"]["values"],
                               col_title=ds["columns"]["title"], line_title=ds["line"]["title"],
                               fmt_col=_fmt(ds["columns"]["fmt"]), fmt_line=_fmt(ds["line"]["fmt"]),
                               growth_label=resolve(ds.get("growth_label", ""), facts) or None,
                               change_label=resolve(ds.get("change_label", ""), facts) or None)
    out = {f"col:{i}": (x + Inches(0.42), y + Inches(0.12)) for i, (x, y) in enumerate(a["columns"])}
    out.update({f"line:{i}": (x + Inches(0.25), y + Inches(0.32)) for i, (x, y) in enumerate(a["line"])})
    return out


def _ex_profit_pool(c, area, ds, s, facts):
    segs = [pool.Segment(x["name"], x["size"], x["rate"]) for x in ds["segments"]]
    avg = (ds["average"][0], resolve(ds["average"][1], facts)) if ds.get("average") else None
    a = pool.profit_pool(c, area, segs, highlight=set(s.emphasis), fmt_rate=_fmt(ds.get("fmt_rate")),
                         fmt_profit=_fmt(ds.get("fmt_profit")), average=avg, x_title=ds.get("x_title", ""),
                         y_title=ds.get("y_title", ""))
    return {k: (x - Inches(0.2), y - Inches(0.14)) for k, (x, y) in a.items()}


def _ex_range_benchmark(c, area, ds, s, facts):
    kpis = [benchmark.KPI(k["name"], k["unit"], k["ours"], k["lo"], k["q1"], k["median"], k["q3"], k["hi"],
                          k["higher_is_better"], _fmt(k["fmt"])) for k in ds["kpis"]]
    a = benchmark.range_benchmark(c, area, kpis, ours_label=ds["ours_label"], peers_label=ds["peers_label"],
                                  fmt_gap=lambda k: _gap_text(k))
    return {k: (x + Inches(0.52), y - Inches(0.26)) for k, (x, y) in a.items()}


def _gap_text(k: benchmark.KPI) -> str:
    pct = k.gap() / k.median * 100
    return fmt_num(pct, 0, suffix="%", sign=True)


def _points(ds):
    return [matrix.Point(p["label"], p["x"], p["y"], p["size"], p.get("highlight", False), p.get("note", ""))
            for p in ds["points"]]


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
    return {k: (x - d / 2 + Inches(0.02), y - d / 2 + Inches(0.02)) for k, (x, y, d) in a.items()}


def _ex_heat(c, area, ds, s, facts):
    outline = {tuple(x) for x in ds.get("outline", [])}
    table.heat_table(c, area, ds["rows"], ds["cols"], ds["values"], fmt=_fmt(ds.get("fmt")),
                     row_head=ds.get("row_head", ""), row_notes=ds.get("row_notes"), outline=outline)
    return {}


def _ex_roadmap(c, area, ds, s, facts):
    tasks = [gantt.Task(t["name"], t["wave"], t["start"], t["end"], resolve(t.get("note", ""), facts))
             for t in ds["tasks"]]
    gantt.roadmap(c, area, tasks, ds["waves"], months=ds.get("months", 24),
                  milestones=[(m[0], resolve(m[1], facts)) for m in ds.get("milestones", [])])
    return {}


EXHIBITS = {
    "waterfall": _ex_waterfall,
    "columns_over_line": _ex_columns_over_line,
    "profit_pool": _ex_profit_pool,
    "range_benchmark": _ex_range_benchmark,
    "bubble_matrix": _ex_bubble,
    "priority_matrix": lambda c, a, ds, s, f: _ex_bubble(
        c, a, ds, s, f, quadrants={"tr": "Quick wins", "tl": "Major projects", "br": "Fill-ins",
                                   "bl": "Deprioritise"}, shade="tr"),
    "heat_table": _ex_heat,
    "roadmap": _ex_roadmap,
}


def report(plan: Plan, decisions: list[Decision], facts: dict) -> str:
    """Markdown trace of the reasoning: problem, issue tree, analyses, and each exhibit decision."""
    out = [f"# Plan report: {plan.brief_id}", "", f"Produced by: {plan.produced_by}", "",
           "## Problem", "", f"**Key question.** {plan.problem.key_question}", "",
           f"**Decision maker.** {plan.problem.decision_maker}", "",
           "**Success criteria.** " + "; ".join(plan.problem.success_criteria).replace(";", ","), "",
           "## Issue tree", ""]

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
    out += ["", "## Exhibit decisions", ""]
    for d in decisions:
        if not d.candidates:
            continue
        out.append(f"### {d.slide}: {d.chosen}")
        out.append("")
        out.append("| Candidate | Score | Reasons |")
        out.append("|---|---|---|")
        for cnd in d.candidates:
            mark = " (chosen)" if cnd.exhibit == d.chosen else ""
            out.append(f"| {cnd.exhibit}{mark} | {cnd.score:.2f} | {' / '.join(cnd.reasons)} |")
        if d.title_warnings:
            out.append(f"\nTitle contains typed numbers not from data: {', '.join(d.title_warnings)}")
        out.append("")
    return "\n".join(out)
