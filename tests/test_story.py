import json
from pathlib import Path

import pytest
from pptx.util import Inches

from deckforge.qa.lint import lint
from deckforge.render.canvas import Deck
from deckforge.story.plan import Plan, resolve, untracked_numbers
from deckforge.tokens import MERIDIAN
from deckforge.viz import frame as F
from deckforge.viz.exhibits import benchmark, bridge, gantt, matrix, pool, table
from deckforge.viz.scale import Linear, fmt_num, nice_domain
from deckforge.viz.select import DataProfile, choose, profile_of

EXAMPLE = Path(__file__).parent.parent / "examples" / "auto_components_margin"


def test_selector_never_returns_dual_axis_or_radar():
    best = choose("magnitude_and_rate_over_time", DataProfile(n_periods=4, n_measures=2, mixed_units=True))
    assert best[0].exhibit == "columns_over_line"
    assert next(c for c in best if c.exhibit == "dual_axis_combo").rejected
    profile = DataProfile(n_categories=6, mixed_units=True, has_peer_distribution=True)
    bench = choose("benchmark_vs_peers", profile)
    assert bench[0].exhibit == "gap_bars"                  # a board reads gap bars without decoding
    assert choose("benchmark_vs_peers", profile, audience="analyst")[0].exhibit == "range_benchmark"
    assert all(c.rejected for c in bench if c.exhibit in ("radar", "ranked_bars"))


def test_selector_depends_on_data_shape():
    assert choose("trend", DataProfile(n_periods=12))[0].exhibit == "line"
    assert choose("trend", DataProfile(n_periods=5))[0].exhibit == "columns"
    assert choose("profit_by_segment", DataProfile(has_size=True, has_rate=True))[0].exhibit == "profit_pool"
    assert choose("profit_by_segment", DataProfile())[0].exhibit == "ranked_bars"


def test_profile_inference_and_positive_bridge():
    walk = {"steps": [{"label": "a", "value": 10, "kind": "total"}, {"label": "b", "value": 2},
                      {"label": "c", "value": None, "kind": "total"}]}
    p = profile_of(walk)
    assert p.has_totals and not p.signed_deltas
    assert choose("decomposition", p)[0].exhibit == "waterfall"


def test_tokens_resolve_and_typed_numbers_are_caught():
    assert resolve("Margin fell {d} bps", {"d": 390}) == "Margin fell 390 bps"
    with pytest.raises(KeyError):
        resolve("{missing}", {})
    assert untracked_numbers("Revenue grew {g} since FY22 to 6,000", {"15"}) == ["6,000"]
    assert untracked_numbers("Back to 15% by FY27", {"15"}) == []


def test_scales_and_formats():
    s = Linear(0, 100, 1000, 0)
    assert s(25) == 750 and s.length(10) == 100
    assert nice_domain(3, 47) == (0, 50, 10)
    assert fmt_num(-170, 0) == "−170" and fmt_num(80, 0, sign=True) == "+80"


def test_bridge_levels():
    lv = bridge.levels([bridge.Step("s", 10, "total"), bridge.Step("a", -3), bridge.Step("b", 1),
                        bridge.Step("e", None, "total")])
    assert lv == [(0.0, 10), (10, 7), (7, 8), (0.0, 8)]


def test_every_exhibit_renders_lint_clean():
    deck = Deck(MERIDIAN)
    box = F.Box(Inches(0.5), Inches(1.9), Inches(8.4), Inches(4.7))
    fmt = lambda v: fmt_num(v, 0)
    c = deck.new_slide()
    bridge.waterfall(c, box, [bridge.Step("Start", 20, "total"), bridge.Step("Down", -4), bridge.Step("Up", 2),
                              bridge.Step("End", None, "total")], fmt_total=fmt, fmt_delta=fmt, emphasis={1})
    c = deck.new_slide()
    pool.profit_pool(c, box, [pool.Segment("A", 50, 12), pool.Segment("B", 30, 6)], highlight={"B"}, fmt_rate=fmt,
                     fmt_profit=fmt)
    c = deck.new_slide()
    benchmark.range_benchmark(c, box, [benchmark.KPI("Cost", "₹/kg", 59, 41, 46, 50, 55, 66, False, fmt),
                                       benchmark.KPI("OEE", "%", 61, 55, 63, 68, 74, 81, True, fmt)],
                              ours_label="Us", peers_label="Peers")
    c = deck.new_slide()
    matrix.bubble_matrix(c, box, [matrix.Point("P", 50, 60, 10, True), matrix.Point("Q", 70, 45, 5)],
                         x_title="x", y_title="y", fmt_x=fmt, fmt_y=fmt, x_ref=(60, "ref"), y_ref=(50, "ref"),
                         quadrants={"tr": "Best", "bl": "Fix"}, shade="bl", domain_x=(40, 80), domain_y=(40, 70))
    c = deck.new_slide()
    table.heat_table(c, box, ["r1", "r2"], ["c1", "c2", "c3"], [[1, 5, 9], [2, 4, 8]], fmt=fmt)
    c = deck.new_slide()
    gantt.roadmap(c, box, [gantt.Task("Task one", 0, 0, 6, "₹5 cr"), gantt.Task("Task two", 1, 3, 12)],
                  ["Wave 1", "Wave 2"], months=12, milestones=[(6, "Half")])
    assert lint(deck) == []


def test_example_brief_builds_clean(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("build", EXAMPLE / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    plan = Plan.model_validate_json((EXAMPLE / "plan.json").read_text())
    data = json.loads((EXAMPLE / "data.json").read_text())
    facts = mod.compute_facts(data)                         # reconciliation asserts run here
    assert facts["fy27_margin"] == "14.4%" and facts["kpis_worse"] == "five"
    for family in ("meridian", "verdant"):
        path, issues, lf, story = mod.main(tmp_path, family)
        assert path.name == f"margin_recovery_{family}.pptx" and path.exists()
        assert issues == [], issues                        # geometry and contrast lint clean in both families
        assert lf.passed, [r.detail for r in lf.failures()]
        assert story == []
    report = (tmp_path / "margin_recovery_meridian_plan_report.md").read_text()
    assert "dual_axis_combo" in report and "(chosen)" in report and "Look and feel gate" in report
    assert len(plan.slides) == 14
