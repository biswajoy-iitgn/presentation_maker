"""Demo deck: every visual capability in one board document, all data illustrative.

Every number in a title or text block is computed from the data dictionaries below.

Run:  python -m deckforge.demo.build_demo [out_dir]
"""

from __future__ import annotations

import sys
from pathlib import Path

from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches

from deckforge.assets.needs import AssetNeed
from deckforge.assets.resolver import AssetResolver
from deckforge.assets.sources.generate import ImageBrief
from deckforge.assets.sources.geo import draw_world
from deckforge.qa.repair import lint_and_repair
from deckforge.render import charts, layout, overlays
from deckforge.render.canvas import Deck
from deckforge.render.layout import MARGIN
from deckforge.tokens import MERIDIAN

# ----------------------------------------------------------------------------- illustrative data
SPEND_SHARE = {"CHN": 31, "USA": 14, "DEU": 9, "IND": 8, "MEX": 7, "VNM": 5, "JPN": 4, "POL": 3}
COUNTRY_NAMES = {"CHN": "China", "USA": "United States", "DEU": "Germany", "IND": "India", "MEX": "Mexico",
                 "VNM": "Vietnam", "JPN": "Japan", "POL": "Poland"}
DISRUPTION = dict(zip(range(2016, 2026), [12, 14, 13, 17, 41, 38, 33, 29, 34, 39]))
DELAYED_ORDERS = [2.1, 2.4, 2.2, 2.9, 7.8, 6.9, 5.7, 4.8, 5.6, 6.4]
LEVERS = [("truck", "Dual-source critical lanes", 34), ("warehouse", "Regional buffer hubs", 22),
          ("handshake", "Strategic supplier contracts", 14), ("shield-check", "Control tower and early warning", 10)]
COST_BRIDGE = [("FY25 cost to serve", 420, "total"), ("Network redesign", -38, "delta"), ("Procurement", -21, "delta"),
               ("Inventory policy", -12, "delta"), ("Tariffs", 18, "delta"), ("Wage inflation", 11, "delta"),
               ("FY28 cost to serve", None, "total")]
CONFIDENCE = {"cn": [9, 14, 21, 30, 18, 8], "us": [8, 12, 22, 31, 19, 8], "de": [10, 13, 20, 29, 20, 8]}
PROGRAMME_INVESTMENT = 64   # $M one-off
RISK_INDEX_CUT = sum(v for *_, v in LEVERS) / 160          # share of exposure removed (illustrative model)

SOURCE = "Source: illustrative data generated for the DeckForge demo"


def growth_phrase(ratio: float) -> str:
    if ratio >= 3:
        return "more than tripled"
    if ratio >= 2:
        return "more than doubled"
    return f"risen {ratio:.1f} times"


# ----------------------------------------------------------------------------- slides
def cover(deck: Deck, assets: AssetResolver):
    c, t = deck.new_slide(), deck.theme
    bg = assets.background(AssetNeed(kind="background", role="cover", seed=7))
    c.picture(bg, 0, 0, deck.width, deck.height, name="DF_cover_bg")
    c.text(Inches(1.0), Inches(2.25), Inches(7), Inches(0.35), "BOARD DISCUSSION DOCUMENT", size=13, bold=True,
           color="#BFDBFE", name="overline")
    c.text(Inches(1.0), Inches(2.75), Inches(7.6), Inches(2.4), "Building a resilient supply network for 2030",
           font=t.title_font, size=46, color="#FFFFFF", name="DF_title")
    c.text(Inches(1.0), Inches(5.05), Inches(7), Inches(0.4), "Strategy refresh  |  October 2026", size=16,
           color="#C7D2E6", name="cover_sub")
    c.text(Inches(1.0), Inches(6.85), Inches(6), Inches(0.3), "Illustrative demo built with DeckForge", size=10,
           color="#8EA0BF", name="cover_note")


def agenda(deck: Deck, assets: AssetResolver, active: int):
    c, t = deck.new_slide(), deck.theme
    pw = Inches(5.2)
    panel = assets.background(AssetNeed(kind="background", role="panel", width_px=750, height_px=1080, seed=11,
                                        style="motion_streaks"))
    c.picture(panel, 0, 0, pw, deck.height, name="agenda_panel")
    c.rect(Inches(0.45), Inches(0.9), pw - Inches(0.9), Inches(2.3), t.panel, alpha=0.82, name="agenda_box")
    c.text(Inches(0.85), Inches(1.25), pw - Inches(1.7), Inches(0.9), "Supply network strategy",
           font=t.title_font, size=28, bold=True, color="#FFFFFF", name="agenda_title")
    c.text(Inches(0.85), Inches(2.45), pw - Inches(1.7), Inches(0.4), "AGENDA", size=14, color=t.panel_number,
           name="agenda_label")
    items = ["Where we stand today", "Where the network is exposed", "What we recommend", "How we get there"]
    x0, y0, step = pw + Inches(0.9), Inches(2.0), Inches(1.0)
    c.line(x0 + Inches(0.2), y0 + Inches(0.2), x0 + Inches(0.2), y0 + step * (len(items) - 1) + Inches(0.2),
           "#B8C0CC", 1.0)
    for i, item in enumerate(items):
        on = i == active
        y = y0 + step * i
        c.rect(x0, y, Inches(0.4), Inches(0.4), t.accent if on else "#C9CFD8", shape=MSO_SHAPE.OVAL,
               name=f"tracker_{i}")
        c.text(x0 + Inches(0.6), y + Inches(0.02), Inches(6), Inches(0.4), item, size=20, bold=on,
               color=t.accent if on else t.ink, name=f"agenda_item_{i}")


def exec_summary(deck: Deck, assets: AssetResolver, facts: dict):
    c, t = deck.new_slide(), deck.theme
    bg = assets.background(AssetNeed(kind="background", role="backdrop", seed=5))
    c.picture(bg, 0, 0, deck.width, deck.height, name="exec_bg")
    c.text(Inches(1.3), Inches(2.3), Inches(4.2), Inches(2.8),
           f"Three moves cut supply risk by {facts['risk_cut']:.0%} and lower cost to serve by "
           f"{facts['cost_cut']:.0%}", font=t.title_font, size=30, color=t.ink, name="DF_title")
    rows = [
        [("Concentrated exposure: ", True), (f"five countries hold {facts['top5']}% of supplier spend and "
                                              f"disruption days have {facts['disruption_phrase']} since 2016", False)],
        [("Four levers ", True), (f"address {facts['lever_share']}% of the exposure, led by dual-sourcing "
                                  f"critical lanes", False)],
        [("Self-funding: ", True), (f"${facts['savings']}M annual savings repay the ${PROGRAMME_INVESTMENT}M "
                                    f"programme in {facts['payback']:.1f} years", False)],
    ]
    y = Inches(1.9)
    for i, runs in enumerate(rows):
        c.text(Inches(6.3), y, Inches(6.2), Inches(1.0), [runs], size=17, color=t.ink, name=f"exec_row_{i}")
        if i < len(rows) - 1:
            c.line(Inches(6.3), y + Inches(1.15), Inches(12.5), y + Inches(1.15), "#FFFFFF", 1.0)
        y += Inches(1.4)
    layout.footer(c, SOURCE)


def network_map(deck: Deck, assets: AssetResolver, facts: dict):
    c, t = deck.new_slide(), deck.theme
    c.sticker("ILLUSTRATIVE", Inches(11.2), Inches(0.42), Inches(1.68), Inches(0.36), t.negative)
    top = layout.title_block(c, f"Five countries hold {facts['top5']}% of supplier spend",
                             sub="Share of third-party supplier spend by country, %", rule=True,
                             width=Inches(10.5))
    box = (MARGIN, top + Inches(0.25), Inches(8.1), Inches(6.7) - top - Inches(0.25))
    ranked = sorted(SPEND_SHARE.items(), key=lambda kv: -kv[1])
    top5 = dict(ranked[:5])
    shades = ["#1E40AF", "#2563EB", "#3B82F6", "#60A5FA", "#93C5FD"]
    anchors = draw_world(c, box, {k: shades[i] for i, k in enumerate(top5)}, "#E3E7EE",
                         countries=assets.countries(), outline=("#FFFFFF", 0.25))
    offsets = {"CHN": (0.55, -0.55), "USA": (-0.3, -0.75), "DEU": (-0.35, -0.8), "IND": (0.25, 0.55),
               "MEX": (-0.65, 0.45)}
    for iso, (ax, ay) in anchors.items():
        dx, dy = offsets.get(iso, (0.4, -0.4))
        lx, ly = ax + Inches(dx), ay + Inches(dy)
        c.line(ax, ay, lx, ly, t.ink, 0.75)
        c.text(lx - Inches(0.6), ly - (Inches(0.42) if dy < 0 else 0), Inches(1.2), Inches(0.42),
               [[(f"{top5[iso]}%", True)], [(COUNTRY_NAMES[iso], False)]], size=10, color=t.ink,
               align=PP_ALIGN.CENTER, name=f"callout_{iso}")
    # ranked list with inline bars
    lx, ly = Inches(9.0), top + Inches(0.45)
    c.text(lx, ly - Inches(0.35), Inches(3.8), Inches(0.3), "Top sourcing countries", size=12, bold=True,
           color=t.ink, name="rank_head")
    vmax = ranked[0][1]
    for i, (iso, share) in enumerate(ranked):
        y = ly + Inches(0.5) * i
        c.text(lx, y, Inches(1.5), Inches(0.3), COUNTRY_NAMES[iso], size=12, name=f"rank_name_{i}")
        bw = int(Inches(1.8) * share / vmax)
        c.rect(lx + Inches(1.55), y + Inches(0.04), bw, Inches(0.22), t.accent if iso in top5 else t.neutral,
               name=f"rank_bar_{i}")
        c.text(lx + Inches(1.6) + bw, y, Inches(0.6), Inches(0.3), f"{share}%", size=12, bold=iso in top5,
               name=f"rank_val_{i}")
    layout.footer(c, SOURCE + ". Boundaries: Natural Earth")


def disruption_band(deck: Deck, assets: AssetResolver, facts: dict):
    c, t = deck.new_slide(), deck.theme
    band_h = Inches(1.6)
    need = AssetNeed(kind="photo", role="band", width_px=1920, height_px=230, seed=3, style="motion_streaks",
                     text_zone=(0.0, 0.1, 0.75, 0.8))
    band = assets.photo(need, ImageBrief("highway at night with light trails", style="motion",
                                         negative_space="left"), query="highway night light trails")
    c.picture(band, 0, 0, deck.width, band_h, name="band")
    c.scrim(0, 0, Inches(12.0), band_h, t.glow[0], 0.88, 0.15, angle_deg=0)
    c.rect(0, band_h, deck.width, Inches(0.06), t.accent, name="band_rule")
    years = list(DISRUPTION)
    vals = list(DISRUPTION.values())
    title = f"Disruption days have {facts['disruption_phrase']} since 2016, reaching {vals[-1]} in 2025"
    c.text(MARGIN, Inches(0.38), Inches(10.5), Inches(1.0), title, font=t.title_font, size=26, bold=True,
           color="#FFFFFF", name="DF_title")
    c.sticker("ILLUSTRATIVE", Inches(11.2), band_h + Inches(0.25), Inches(1.68), Inches(0.36), t.negative)
    c.text(MARGIN, band_h + Inches(0.35), Inches(8), Inches(0.3), "Days per year with a tier-1 supply disruption",
           size=13, color=t.muted, name="chart_header")
    frame = (MARGIN, band_h + Inches(0.75), Inches(12.4), Inches(3.7))
    box = charts.column_chart(c, frame, charts.short_years(years), vals, vmax=50, major=10,
                              num_fmt=charts.top_tick_format(50, suffix=" days"), hero=[len(vals) - 1],
                              hero_fmt='#,##0" days"', plot=(0.11, 0.06, 0.88, 0.84))
    overlays.difference_arrow(c, box, 0, len(vals) - 1, vals[0], vals[-1],
                              f"{vals[-1] / vals[0]:.1f}x", t.accent, clear_j=Inches(0.4))
    overlays.data_row(c, box, frame[1] + frame[3] + Inches(0.08), [f"{v:.1f}" for v in DELAYED_ORDERS],
                      ["Orders delayed", "%"])
    layout.footer(c, SOURCE)


def levers(deck: Deck, assets: AssetResolver, facts: dict):
    c, t = deck.new_slide(), deck.theme
    side_x = Inches(9.4)
    c.rect(side_x, 0, deck.width - side_x, deck.height, "#F1F4F8", name="side_panel")
    c.sticker("ILLUSTRATIVE", Inches(7.45), Inches(0.42), Inches(1.68), Inches(0.36), t.negative)
    layout.title_block(c, f"Four levers address {facts['lever_share']}% of supply exposure", width=Inches(6.8),
                       sub="Share of modelled exposure removed by each lever, %")
    col_w = Inches(2.15)
    for i, (icon_name, label, share) in enumerate(LEVERS):
        x = MARGIN + col_w * i
        c.text(x, Inches(2.15), col_w, Inches(0.5), f"#{i + 1}", font=t.title_font, size=26, bold=True,
               color=t.accent, align=PP_ALIGN.CENTER, name=f"lever_rank_{i}")
        icon = assets.icon(icon_name, t.ink, px=256)
        c.picture(icon, x + (col_w - Inches(0.8)) // 2, Inches(2.85), Inches(0.8), Inches(0.8),
                  name=f"lever_icon_{i}", fmt="PNG")
        c.text(x + Inches(0.1), Inches(3.85), col_w - Inches(0.2), Inches(0.8), label, size=14, bold=True,
               align=PP_ALIGN.CENTER, name=f"lever_label_{i}")
        bar_h = int(Inches(1.6) * share / LEVERS[0][2])
        base_y = Inches(6.45)
        c.rect(x + (col_w - Inches(0.7)) // 2, base_y - bar_h, Inches(0.7), bar_h, t.accent, name=f"lever_bar_{i}")
        c.text(x, base_y - bar_h - Inches(0.38), col_w, Inches(0.3), f"{share}%", size=16, bold=True,
               color=t.accent, align=PP_ALIGN.CENTER, name=f"lever_val_{i}")
    c.line(MARGIN, Inches(6.45), MARGIN + col_w * 4, Inches(6.45), t.rule, 0.75)
    c.text(side_x + Inches(0.45), Inches(2.2), deck.width - side_x - Inches(0.9), Inches(3.5),
           [[("Dual-sourcing critical lanes ", True), ("removes the largest single block of exposure and is "
                                                       "the precondition for the regional hubs.", False)],
            [("Contracts and the control tower ", True), ("are cheaper, but act only once the physical network "
                                                          "has alternatives.", False)]],
           size=15, color=t.ink, name="side_text", leading=1.15)
    layout.footer(c, SOURCE, right=side_x - Inches(0.3))


def cost_bridge(deck: Deck, facts: dict):
    c, t = deck.new_slide(), deck.theme
    c.sticker("ILLUSTRATIVE", Inches(11.2), Inches(0.42), Inches(1.68), Inches(0.36), t.negative)
    top = layout.title_block(c, f"Cost to serve falls {facts['cost_cut']:.0%} as network moves outweigh tariff "
                                f"and wage headwinds", sub="Cost to serve bridge, FY25 to FY28, $M", rule=True,
                             width=Inches(10.5))
    frame = (MARGIN, top + Inches(0.3), Inches(12.4), Inches(6.75) - top - Inches(0.3))
    charts.waterfall(c, frame, COST_BRIDGE, vmax=480, higher_is_better=False)
    layout.footer(c, SOURCE)


def confidence(deck: Deck, assets: AssetResolver, facts: dict):
    c, t = deck.new_slide(), deck.theme
    panel_x = Inches(9.75)
    c.rect(panel_x, 0, deck.width - panel_x, deck.height, t.panel, name="DF_sidebar")
    top = layout.title_block(c, "Supplier confidence is similar across our three largest sourcing markets",
                             sub="Supplier survey, agreement with 'we can meet 2027 volumes'", rule=True,
                             width=Inches(8.9), rule_to=Inches(9.35))
    c.text(MARGIN, top + Inches(0.2), Inches(4), Inches(0.3), "Percentage of suppliers", size=12, color=t.muted,
           name="likert_unit")
    rows = list(CONFIDENCE.values())
    frame = (Inches(2.4), top + Inches(1.0), Inches(6.95), Inches(2.6))
    colors = ["#D9DEE6", "#D9DEE6", "#D9DEE6", "#9CC3F5", t.accent, "#1E40AF"]
    box = charts.stacked_bar_100(c, frame, rows, ["Strongly disagree", "2", "3", "4", "5", "Strongly agree"],
                                 colors, label_colors=[t.ink] * 4 + ["#FFFFFF"] * 2)
    c.text(box.x, frame[1] - Inches(0.32), Inches(2.5), Inches(0.28), "Strongly disagree", size=12, bold=True,
           name="likert_left")
    c.text(box.x + box.w - Inches(2.5), frame[1] - Inches(0.32), Inches(2.5), Inches(0.28), "Strongly agree",
           size=12, bold=True, align=PP_ALIGN.RIGHT, name="likert_right")
    names = {"cn": "China", "us": "United States", "de": "Germany"}
    for i, code in enumerate(CONFIDENCE):
        yc = box.cat_center(i)
        flag = assets.flag(code, 240)
        c.picture(flag, Inches(1.75), yc - Inches(0.17), Inches(0.45), Inches(0.34), name=f"flag_{code}", fmt="PNG")
        c.text(MARGIN, yc - Inches(0.15), Inches(1.25), Inches(0.3), names[code], size=12, name=f"row_{code}")
    agree = {k: sum(v[3:]) for k, v in CONFIDENCE.items()}
    gap = max(agree.values()) - min(agree.values())
    c.text(panel_x + Inches(0.4), Inches(1.9), Inches(3.0), Inches(1.0), f"{min(agree.values())}%+",
           font=t.title_font, size=44, bold=True, color=t.panel_number, name="side_big_1")
    c.text(panel_x + Inches(0.4), Inches(2.85), Inches(3.0), Inches(0.9), "of suppliers in every market expect "
           "to meet 2027 volumes", size=14, bold=True, color="#FFFFFF", name="side_desc_1")
    c.text(panel_x + Inches(0.4), Inches(4.1), Inches(3.0), Inches(1.0), f"{gap} pp", font=t.title_font, size=44,
           bold=True, color=t.panel_number, name="side_big_2")
    c.text(panel_x + Inches(0.4), Inches(5.05), Inches(3.0), Inches(0.9), "spread between the most and least "
           "confident market", size=14, bold=True, color="#FFFFFF", name="side_desc_2")
    layout.footer(c, SOURCE, right=panel_x - Inches(0.3))


def kpis(deck: Deck, assets: AssetResolver, facts: dict):
    c, t = deck.new_slide(), deck.theme
    bg = assets.background(AssetNeed(kind="background", role="backdrop", seed=9))
    c.picture(bg, 0, 0, deck.width, deck.height, name="kpi_bg")
    c.text(MARGIN + Inches(0.6), Inches(0.75), Inches(11.5), Inches(1.0),
           f"The programme halves supply risk and pays back in {facts['payback']:.1f} years",
           font=t.title_font, size=30, color=t.ink, name="DF_title")
    tiles = [(f"{facts['risk_cut']:.0%}", "lower ", "supply risk index", " by FY28"),
             (f"${facts['savings']}M", "annual ", "cost-to-serve savings", " at run rate"),
             (f"{facts['payback']:.1f} yrs", "payback on ", f"${PROGRAMME_INVESTMENT}M", " one-off investment")]
    x = MARGIN + Inches(0.6)
    for i, (big, pre, key, post) in enumerate(tiles):
        c.text(x, Inches(2.9), Inches(3.4), Inches(1.1), big, size=60, bold=True, color=t.ink, name=f"kpi_{i}")
        c.text(x, Inches(4.15), Inches(3.2), Inches(1.0), [[(pre, False), (key, True), (post, False)]], size=16,
               color=t.accent, name=f"kpi_desc_{i}")
        if i < 2:
            c.line(x + Inches(3.6), Inches(3.0), x + Inches(3.6), Inches(4.9), "#FFFFFF", 1.5)
        x += Inches(3.9)
    layout.footer(c, SOURCE)


def closing(deck: Deck, assets: AssetResolver):
    c, t = deck.new_slide(), deck.theme
    bg = assets.background(AssetNeed(kind="background", role="divider", seed=21))
    c.picture(bg, 0, 0, deck.width, deck.height, name="close_bg")
    c.text(MARGIN + Inches(0.6), Inches(0.9), Inches(11), Inches(1.0), "Three decisions needed from the board today",
           font=t.title_font, size=32, color="#FFFFFF", name="DF_title")
    steps = [("Approve", "dual-sourcing of the twelve critical lanes", "COO, Q1 2027"),
             ("Fund", f"the ${PROGRAMME_INVESTMENT}M programme in two tranches", "CFO, Q4 2026"),
             ("Mandate", "the control tower pilot in the APAC region", "CSCO, Q1 2027")]
    x = MARGIN + Inches(0.6)
    for i, (verb, what, owner) in enumerate(steps):
        c.text(x, Inches(2.8), Inches(0.7), Inches(0.9), f"{i + 1}", font=t.title_font, size=54, bold=True,
               color=t.panel_number, name=f"step_num_{i}")
        c.text(x + Inches(0.85), Inches(2.95), Inches(2.9), Inches(1.6), [[(f"{verb} ", True), (what, False)]],
               size=18, color="#FFFFFF", name=f"step_text_{i}")
        c.text(x + Inches(0.85), Inches(4.55), Inches(2.9), Inches(0.35), owner, size=12, color="#DCE6F5",
               name=f"step_owner_{i}")
        x += Inches(3.95)


def facts_from_data() -> dict:
    ranked = sorted(SPEND_SHARE.values(), reverse=True)
    start = COST_BRIDGE[0][1]
    end = start + sum(v for _, v, k in COST_BRIDGE if k == "delta")
    savings = start - end
    years = list(DISRUPTION.values())
    return {
        "top5": sum(ranked[:5]),
        "disruption_phrase": growth_phrase(years[-1] / years[0]),
        "lever_share": sum(v for *_, v in LEVERS),
        "cost_cut": savings / start,
        "savings": savings,
        "payback": PROGRAMME_INVESTMENT / savings,
        "risk_cut": RISK_INDEX_CUT,
    }


def build(out_dir: Path) -> tuple[Path, list]:
    deck = Deck(MERIDIAN)
    assets = AssetResolver(MERIDIAN)
    f = facts_from_data()
    cover(deck, assets)
    agenda(deck, assets, active=0)
    exec_summary(deck, assets, f)
    network_map(deck, assets, f)
    disruption_band(deck, assets, f)
    levers(deck, assets, f)
    cost_bridge(deck, f)
    confidence(deck, assets, f)
    kpis(deck, assets, f)
    closing(deck, assets)
    actions, issues = lint_and_repair(deck)
    path = deck.save(out_dir / "deckforge_demo.pptx")
    assets.manifest(out_dir / "deckforge_demo.assets.json")
    return path, actions, issues


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("out")
    p, repairs, problems = build(out)
    print(p)
    print("repairs:", "none" if not repairs else "\n  " + "\n  ".join(repairs))
    print("lint:", "clean" if not problems else "\n  " + "\n  ".join(map(str, problems)))
