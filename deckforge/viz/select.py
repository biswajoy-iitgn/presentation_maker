"""Visual form selection: message type plus data shape decides the exhibit, with reasons.

Every candidate exhibit declares when it fits and when it must not be used. The selector scores
all of them, so the plan report can show why the winner won and why the others lost.
Rules follow Zelazny's comparison types, extended with consulting forms (bridges, profit pools,
peer ranges, portfolio and priority matrices) and the dataviz non-negotiables (no dual axes,
no radar for comparison, pies only for few parts).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

MessageType = Literal[
    "magnitude_and_rate_over_time",   # e.g. revenue grew while margin fell
    "trend",                          # one measure over time
    "decomposition",                  # change explained by additive drivers
    "profit_by_segment",              # where profit sits: size x rate
    "composition",                    # part-to-whole
    "benchmark_vs_peers",             # our KPIs against a peer distribution
    "ranking",                        # order items on one measure
    "portfolio",                      # units placed on two measures, sized by a third
    "value_by_two_dimensions",        # a value across rows x columns
    "prioritisation",                 # value vs ease
    "schedule",                       # what happens when
    "headline_numbers",               # a few numbers carry the message
]


@dataclass
class DataProfile:
    n_categories: int = 0
    n_periods: int = 0
    n_measures: int = 1
    mixed_units: bool = False
    signed_deltas: bool = False
    has_totals: bool = False
    has_size: bool = False
    has_rate: bool = False
    has_peer_distribution: bool = False
    rows: int = 0
    cols: int = 0
    has_dates: bool = False
    has_geo: bool = False


@dataclass
class Candidate:
    exhibit: str
    score: float
    reasons: list[str] = field(default_factory=list)

    @property
    def rejected(self) -> bool:
        return self.score <= 0


def _rules(m: MessageType, p: DataProfile) -> list[Candidate]:
    C = Candidate
    out: list[Candidate] = []

    # time
    if m == "magnitude_and_rate_over_time":
        out.append(C("columns_over_line", 0.93, ["two measures in different units share one period axis",
                                                 "magnitude as columns, rate as a line, read top to bottom"]))
        out.append(C("dual_axis_combo", 0.0, ["rejected: two y-scales on one plot imply a correlation the data "
                                              "does not show"]))
        out.append(C("indexed_lines", 0.55, ["possible, but indexing hides the absolute margin level the "
                                             "board cares about"]))
    if m == "trend":
        if p.n_periods > 8:
            out.append(C("line", 0.85, [f"{p.n_periods} periods: a line shows the shape better than columns"]))
        else:
            out.append(C("columns", 0.85, [f"{p.n_periods} periods: columns with value labels read precisely"]))
            out.append(C("line", 0.6, ["acceptable, but few points make a sparse line"]))

    # decomposition and composition
    if m == "decomposition":
        out.append(C("waterfall", 0.95 if (p.signed_deltas or p.has_totals) else 0.5,
                     ["start, additive drivers, end: a bridge shows the size and direction of each step"]))
        out.append(C("stacked_columns", 0.25 if p.signed_deltas else 0.6,
                     ["cannot show negative drivers cleanly" if p.signed_deltas else
                      "all steps positive: a stacked build-up works but loses the start-to-end story"]))
    if m == "profit_by_segment":
        if p.has_size and p.has_rate:
            out.append(C("profit_pool", 0.93, ["width = revenue share, height = margin, so area = profit",
                                               "shows at once where revenue and where profit sit"]))
        out.append(C("ranked_bars", 0.55, ["shows margin by segment but loses segment size"]))
        out.append(C("pie", 0.0, ["rejected: shows share only, and angles compare poorly"]))
    if m == "composition":
        out.append(C("stacked_100", 0.8 if p.n_categories <= 6 else 0.5, ["part-to-whole with labelled segments"]))
        out.append(C("pie", 0.6 if p.n_categories <= 4 else 0.0,
                     ["acceptable for 4 or fewer parts" if p.n_categories <= 4 else "rejected: more than 4 parts"]))

    # comparison
    if m == "benchmark_vs_peers":
        if p.has_peer_distribution:
            out.append(C("range_benchmark", 0.94 if p.mixed_units else 0.8,
                         ["each KPI on its own scale, so mixed units sit side by side",
                          "rows oriented so right is better: position reads as performance",
                          "peer range, middle 50% and median give the context a single bar cannot"]))
        out.append(C("ranked_bars", 0.0 if p.mixed_units else 0.75,
                     ["rejected: one axis cannot hold mixed units" if p.mixed_units else
                      "single KPI ranked against named peers"]))
        out.append(C("radar", 0.0, ["rejected: angles and areas distort comparison, order changes the shape"]))
        out.append(C("gap_bars", 0.88, ["every KPI reduced to one signed % gap to the peer median, worst first",
                                         "our value and the median stay visible as columns"]))
    if m == "ranking":
        out.append(C("ranked_bars", 0.9, ["sorted horizontal bars, long labels stay horizontal"]))

    # two measures
    if m == "portfolio" and p.has_geo:
        out.append(C("site_map", 0.9, ["units have locations: a map shows where, a ranked bar shows how much",
                                       "avoids a two-axis scatter the reader has to decode"]))
    if m == "portfolio":
        out.append(C("bubble_matrix", 0.92 if p.has_size else 0.0,
                     ["two performance measures on the axes, scale as bubble area",
                      "reference lines turn positions into a verdict"]))
        out.append(C("scatter", 0.85 if not p.has_size else 0.7, ["two measures, no size dimension needed"]))
        out.append(C("paired_bars", 0.45, ["two bar charts side by side lose the joint position"]))
    if m == "value_by_two_dimensions":
        ok = p.rows <= 10 and p.cols <= 8
        out.append(C("heat_table", 0.9 if ok else 0.5, ["exact values plus a colour ramp for where value "
                                                        "concentrates", "totals per row and column"]))
        out.append(C("stacked_bars", 0.5, ["harder to compare individual cells"]))
    if m == "prioritisation":
        out.append(C("priority_matrix", 0.93, ["value against ease of capture, bubble size = value",
                                               "quadrants name the action: quick wins, major projects"]))
        out.append(C("ranked_bars", 0.55, ["ranks on value only, ignores ease"]))

    # time plans and headlines
    if m == "schedule":
        out.append(C("roadmap", 0.95, ["initiatives grouped by wave on a month axis with value milestones"]))
    if m == "headline_numbers":
        out.append(C("kpi_row", 0.9 if p.n_categories <= 4 else 0.4, ["a few numbers: the number is the chart"]))
        out.append(C("columns", 0.2, ["one bar per number adds no information"]))
    return out


# How quickly a non-specialist reader decodes each form. Boards get the familiar form when fit is close.
FAMILIARITY = {
    "columns": 0.08, "line": 0.08, "ranked_bars": 0.08, "kpi_row": 0.08, "gap_bars": 0.07, "waterfall": 0.06,
    "columns_over_line": 0.06, "roadmap": 0.06, "site_map": 0.06, "stacked_100": 0.04, "heat_table": 0.04,
    "priority_matrix": 0.03, "scatter": 0.0, "profit_pool": -0.02, "bubble_matrix": -0.03, "indexed_lines": -0.03,
    "range_benchmark": -0.06,
}


def choose(message: MessageType, profile: DataProfile, audience: str = "board") -> list[Candidate]:
    """All candidates, best first. The first non-rejected candidate is the choice.

    For board and executive audiences, familiarity breaks near-ties toward forms read without decoding.
    """
    cands = _rules(message, profile)
    if audience in ("board", "executive"):
        for cd in cands:
            if cd.score > 0:
                bonus = FAMILIARITY.get(cd.exhibit, 0.0)
                cd.score = round(cd.score + bonus, 3)
                if bonus:
                    cd.reasons.append(f"familiarity for a {audience} audience {bonus:+.2f}")
    ranked = sorted(cands, key=lambda c: -c.score)
    if not ranked or ranked[0].rejected:
        raise ValueError(f"no admissible exhibit for message '{message}'")
    return ranked


def profile_of(exhibit_data: dict) -> DataProfile:
    """Infer the data shape from a dataset in canonical form."""
    p = DataProfile()
    if "steps" in exhibit_data:
        p.n_categories = len(exhibit_data["steps"])
        p.signed_deltas = any(s.get("kind", "delta") == "delta" and s["value"] < 0 for s in exhibit_data["steps"])
        p.has_totals = any(s.get("kind") == "total" for s in exhibit_data["steps"])
    if "periods" in exhibit_data:
        p.n_periods = len(exhibit_data["periods"])
        p.n_measures = sum(k in exhibit_data for k in ("columns", "line"))
        p.mixed_units = p.n_measures > 1
    if "segments" in exhibit_data:
        segs = exhibit_data["segments"]
        p.n_categories = len(segs)
        p.has_size = all("size" in s for s in segs)
        p.has_rate = all("rate" in s for s in segs)
    if "kpis" in exhibit_data:
        k = exhibit_data["kpis"]
        p.n_categories = len(k)
        p.has_peer_distribution = all({"q1", "median", "q3"} <= set(x) for x in k)
        p.mixed_units = len({x["unit"] for x in k}) > 1
    if "points" in exhibit_data:
        p.n_categories = len(exhibit_data["points"])
        p.has_size = all("size" in x for x in exhibit_data["points"])
        p.has_geo = all("lat" in x and "lon" in x for x in exhibit_data["points"])
    if "values" in exhibit_data:
        p.rows, p.cols = len(exhibit_data["values"]), len(exhibit_data["values"][0])
    if "tasks" in exhibit_data:
        p.has_dates = True
        p.n_categories = len(exhibit_data["tasks"])
    return p
