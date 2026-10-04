from pptx.util import Inches

from deckforge.render import charts, metrics, overlays
from deckforge.render.canvas import Deck
from deckforge.tokens import MERIDIAN


def test_wrap_breaks_long_text_and_height_scales():
    s = "Global buyout value dropped by more than a third in 2022 to $654B"
    one = metrics.wrap(s, "Arial", 12, False, Inches(10))
    many = metrics.wrap(s, "Arial", 12, False, Inches(1.5))
    assert len(one) == 1 and len(many) > 3
    assert metrics.text_height(s, "Arial", 12, False, Inches(1.5)) > metrics.text_height(s, "Arial", 12, False,
                                                                                          Inches(10))


def test_bold_is_wider_and_fit_size_respects_box():
    assert metrics.text_width_pt("Revenue", "Arial", 20, True) > metrics.text_width_pt("Revenue", "Arial", 20)
    size = metrics.fit_size("A fairly long action title that must fit", "Georgia", True, Inches(4), Inches(0.9),
                            max_size=32, min_size=12)
    assert size is not None and size < 32
    assert metrics.fit_size("x " * 400, "Arial", False, Inches(1), Inches(0.3), 12, 10) is None


def test_plotbox_geometry():
    box = charts.PlotBox(x=1000, y=2000, w=10000, h=5000, n=10, vmax=100)
    assert box.cat_center(0) == 1500 and box.cat_center(9) == 10500
    assert box.val(0) == 7000 and box.val(100) == 2000
    assert box.bar_width(100) == 500


def test_formatters_and_calcs():
    assert charts.top_tick_format(1200, "$", "B") == '[=1200]"$"#,##0"B";#,##0'
    assert charts.short_years([2005, 2006, 2010]) == ["2005", "06", "10"]
    assert round(overlays.pct_change(410, 203), 3) == -0.505
    assert abs(overlays.cagr(100, 121, 2) - 0.10) < 1e-9


def test_waterfall_levels_and_cost_colours():
    deck = Deck(MERIDIAN)
    c = deck.new_slide()
    steps = [("Start", 100, "total"), ("Up", 20, "delta"), ("Down", -30, "delta"), ("End", None, "total")]
    _, levels = charts.waterfall(c, (0, 0, Inches(10), Inches(5)), steps, vmax=150, higher_is_better=False)
    assert levels == [100, 120, 90, 90]
    labels = {p.name: p.color for p in c.placed if p.name.startswith("wf_label")}
    assert labels["wf_label_1"] == MERIDIAN.negative      # cost increase is unfavourable
    assert labels["wf_label_2"] == MERIDIAN.accent        # cost decrease is favourable
