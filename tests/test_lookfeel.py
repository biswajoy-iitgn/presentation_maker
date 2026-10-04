"""Look-and-feel gate, storyline consistency, and the exhibits and primitives added for them."""

import json
import math
from pathlib import Path

import pytest
from pptx.util import Inches

from deckforge.assets.sources import illustration
from deckforge.qa import consistency, lookfeel
from deckforge.qa.lint import lint
from deckforge.render.canvas import Deck
from deckforge.story.render import Decision
from deckforge.tokens import MERIDIAN
from deckforge.viz import frame as F
from deckforge.viz import marks as M
from deckforge.viz import style as S
from deckforge.viz.exhibits import gapbars, geomap, matrix
from deckforge.viz.scale import fmt_num

EXAMPLE = Path(__file__).parent.parent / "examples" / "auto_components_margin"
BOX = F.Box(Inches(0.5), Inches(1.9), Inches(8.4), Inches(4.7))


@pytest.fixture(autouse=True)
def _meridian():
    S.use("meridian")
    yield
    S.use("meridian")


@pytest.fixture
def no_icons(monkeypatch):
    """Icons are fetched from GitHub; record the requested glyph colours instead."""
    seen = []
    monkeypatch.setattr(M, "icon", lambda c, name, x, y, size, color=None, stroke=1.75: seen.append(color))
    return seen


def test_family_switch_changes_tokens():
    S.use("verdant")
    assert S.ACCENT == "#11865A" and S.ACTIVE.header == "band"
    S.use("meridian")
    assert S.ACCENT == "#2251FF" and S.ACTIVE.title_font == "Georgia"


def test_icon_glyph_follows_disc_fill(no_icons):
    c = Deck(MERIDIAN).new_slide()
    M.icon_disc(c, "gauge", Inches(1), Inches(1), Inches(0.4), fill=S.NEUTRAL)
    M.icon_disc(c, "gauge", Inches(2), Inches(1), Inches(0.4), fill=S.ACCENT)
    assert no_icons == [S.INK, "#FFFFFF"]          # a white glyph on light grey would vanish


def test_storyline_flags_quick_win_scheduled_late():
    levers = json.loads((EXAMPLE / "data.json").read_text())["levers"]
    roadmap = json.loads((EXAMPLE / "data.json").read_text())["roadmap"]
    assert consistency.matrix_vs_roadmap(levers, roadmap) == []
    oee = next(p for p in levers["points"] if p["label"] == "OEE uplift")
    oee["x"] = 3.3                                  # the earlier deck: OEE drawn as a quick win, roadmap wave 2
    issues = consistency.matrix_vs_roadmap(levers, roadmap)
    assert len(issues) == 1 and "OEE uplift is a quick win" in issues[0]


def test_lookfeel_fails_a_plain_text_deck():
    deck = Deck(MERIDIAN)
    decisions = []
    for i in range(5):
        c = deck.new_slide()
        M.label(c, Inches(0.5), Inches(0.5), Inches(8), Inches(1), "A plain bulleted slide " * 3, size=14)
        decisions.append(Decision(slide=f"S{i}", analysis=None, archetype="exhibit", layout="text"))
    lf = lookfeel.check(deck, decisions)
    codes = {r.code for r in lf.failures()}
    assert not lf.passed
    assert {"imagery_or_graphics", "cover_imagery", "layout_variety", "layout_repeat", "focal_element"} <= codes


def test_gap_bars_sort_worst_first_and_lint_clean(no_icons):
    deck = Deck(MERIDIAN)
    c = deck.new_slide()
    rows = [{"name": "SG&A", "unit": "%", "icon": "x", "ours": 6.1, "bench": 6.5, "higher_is_better": False, "fmt": "f"},
            {"name": "Cost", "unit": "₹/kg", "icon": "x", "ours": 59, "bench": 50, "higher_is_better": False, "fmt": "f"},
            {"name": "OEE", "unit": "%", "icon": "x", "ours": 61, "bench": 68, "higher_is_better": True, "fmt": "f"}]
    anchors = gapbars.gap_bars(c, BOX, rows, ours_label="Us", fmt={"f": lambda v: fmt_num(v, 1)})
    assert list(anchors) == ["Cost", "OEE", "SG&A"]
    assert lint(deck) == []


def _square_country(_url, _cache):
    ring = [[70, 8], [90, 8], [90, 30], [70, 30], [70, 8]] + [[70 + i * 0.1, 8] for i in range(10)]
    return json.dumps({"features": [{"properties": {"ADM0_A3": "TST"},
                                     "geometry": {"type": "Polygon", "coordinates": [ring]}}]}).encode()


def test_site_map_separates_clustered_sites_and_keeps_labels_clear():
    deck = Deck(MERIDIAN)
    c = deck.new_slide()
    sites = [{"name": "Alpha", "lat": 18.5, "lon": 73.9, "size": 18, "value": 34, "note": "18 kt"},
             {"name": "Beta", "lat": 18.7, "lon": 73.9, "size": 14, "value": 18, "note": "14 kt"},
             {"name": "Gamma", "lat": 26, "lon": 84, "size": 6, "value": -3, "note": "6 kt"}]
    geomap.site_map(c, BOX, country="TST", sites=sites, value_title="Gap", fmt_value=lambda v: fmt_num(v, 0),
                    size_note="Marker area = output", highlight={"Alpha"}, get=_square_country)
    dots = {sh.name: (sh.left, sh.top, sh.width, sh.height) for sh in c.slide.shapes
            if sh.name in ("site_Alpha", "site_Beta", "site_Gamma")}
    (ax, ay, aw, _), (bx, by, bw, _) = dots["site_Alpha"], dots["site_Beta"]
    gap = math.hypot(ax + aw / 2 - bx - bw / 2, ay + aw / 2 - by - bw / 2) - (aw + bw) / 2
    assert gap >= 0                                  # coincident plants pushed apart until they touch
    assert any(p.name == "map_note" for p in c.placed)
    assert lint(deck) == []


def test_matrix_uniform_discs_labels_avoid_reference_lines(no_icons):
    deck = Deck(MERIDIAN)
    c = deck.new_slide()
    pts = [matrix.Point("Right on the line", 3.05, 40, 1, True, "₹40 cr", "x"),
           matrix.Point("Low", 4.6, 10, 1, False, "₹10 cr", "x"), matrix.Point("Lower", 4.3, 14, 1, False, "₹14 cr", "x")]
    a = matrix.bubble_matrix(c, BOX, pts, x_title="Ease", y_title="Value", fmt_x=lambda v: fmt_num(v, 0),
                             fmt_y=lambda v: fmt_num(v, 0), x_ref=(3.0, ""), y_ref=(30, ""),
                             quadrants={"tr": "Quick wins", "br": "Fill-ins"}, shade="tr", domain_x=(1, 5),
                             domain_y=(0, 60))
    assert {v[2] for v in a.values()} == {Inches(0.52)}          # no size encoding: equal discs
    divider = BOX.x + Inches(0.75) + (BOX.w - Inches(0.95)) / 2          # x = 3 on a 1 to 5 axis
    for p in c.placed:
        if p.name.startswith("bubble_label_"):
            x, _, w, _ = p.box
            assert not (x < divider < x + w), p.name           # no label straddles the divider
    assert lint(deck) == []


def test_factory_illustration_size_and_palette():
    im = illustration.factory(400, 300, accent="#11865A", smoke=False)
    assert im.size == (400, 300)
    assert len(im.convert("RGB").getcolors(maxcolors=1 << 20)) > 20
