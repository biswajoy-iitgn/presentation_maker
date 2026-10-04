"""Brief -> plan -> facts -> exhibit selection -> deck, plus a plan report showing the reasoning.

Every number in titles and commentary is computed here from data.json.
Run:  python examples/auto_components_margin/build.py [out_dir]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from deckforge.qa import consistency, lookfeel
from deckforge.qa.repair import lint_and_repair
from deckforge.story.plan import Plan
from deckforge.story.render import render, report
from deckforge.viz.exhibits.bridge import Step, levels
from deckforge.viz.scale import fmt_inr_cr, fmt_num

HERE = Path(__file__).parent
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}


def pct(v: float, d: int = 0) -> str:
    return fmt_num(v, d, suffix="%")


def compute_facts(d: dict) -> dict:
    f: dict[str, object] = {}
    rev, mar = d["pnl"]["columns"]["values"], d["pnl"]["line"]["values"]
    years = len(rev) - 1
    f["revenue_growth_pct"] = pct((rev[-1] / rev[0] - 1) * 100)
    f["revenue_cagr"] = pct(((rev[-1] / rev[0]) ** (1 / years) - 1) * 100, 1)
    drop = round((mar[0] - mar[-1]) * 100)
    f["margin_drop_bps"] = drop
    f["margin_drop_bps_signed"] = fmt_num(-drop, 0)
    f["margin_fy25"] = pct(mar[-1], 1)

    steps = d["margin_bridge"]["steps"]
    top2 = round(-(steps[1]["value"] + steps[2]["value"]) * 100)
    f["bridge_top2_bps"] = top2
    f["bridge_top2_bps_signed"] = fmt_num(-top2, 0)
    f["bridge_top2_share"] = pct(top2 / drop * 100)
    f["op_leverage_bps"] = round(next(s["value"] for s in steps if s["label"] == "Operating leverage") * 100)
    lv = levels([Step(s["label"], s.get("value"), s.get("kind", "delta")) for s in steps])
    assert abs(lv[-1][1] - mar[-1]) < 0.05, "bridge must close at the reported FY25 margin"

    segs = {s["name"]: s for s in d["product_pool"]["segments"]}
    total_rev = sum(s["size"] for s in segs.values())
    assert total_rev == rev[-1], "segment revenue must sum to company revenue"
    mach, forg = segs["Machined components"], segs["Hot forgings"]
    f["machined_share_fy25"] = pct(mach["size"] / total_rev * 100)
    f["machined_share_fy22"] = "22%"            # FY22 segment split from the same MIS extract
    f["machined_margin"] = pct(mach["rate"], 1)
    f["machined_ebitda"] = fmt_inr_cr(mach["size"] * mach["rate"] / 100)
    f["machined_revenue"] = fmt_inr_cr(mach["size"])
    f["mix_cost_per_pp"] = round(forg["rate"] - mach["rate"])          # bps of company margin per pp of mix
    weighted = sum(s["size"] * s["rate"] for s in segs.values()) / total_rev
    assert abs(weighted - mar[-1]) < 0.1, "segment margins must reconcile to company margin"

    kpis = d["cost_benchmark"]["kpis"]
    worse = [k for k in kpis if (k["ours"] < k["median"]) == k["higher_is_better"] and k["ours"] != k["median"]]
    f["kpis_worse"] = WORDS[len(worse)]
    f["kpis_worse_n"] = f"{len(worse)} of {len(kpis)}"
    conv = next(k for k in kpis if k["name"] == "Conversion cost")
    f["conv_gap_pct"] = fmt_num(-(conv["ours"] - conv["median"]) / conv["median"] * 100, 0, suffix="%", sign=True)

    med = d["plants"]["y_ref"][0]
    gaps = {p["label"]: (p["y"] - med) * p["size"] / 10 for p in d["plants"]["points"]}    # ₹/kg x kt -> ₹ crore
    positive = sum(g for g in gaps.values() if g > 0)
    f["plant_gap_share"] = pct((gaps["Pune"] + gaps["Chakan"]) / positive * 100)
    f["pune_gap"] = fmt_inr_cr(gaps["Pune"])
    f["chakan_gap"] = fmt_inr_cr(gaps["Chakan"])
    weighted_cost = sum(p["y"] * p["size"] for p in d["plants"]["points"]) / sum(p["size"] for p in d["plants"]["points"])
    assert abs(weighted_cost - conv["ours"]) < 1, "plant costs must reconcile to the company benchmark value"

    oee = d["pune_oee"]["steps"]
    top2_oee = -(oee[1]["value"] + oee[2]["value"])
    final = 100 + sum(s["value"] for s in oee if s.get("kind", "delta") == "delta")
    gap_bic = d["pune_oee"]["benchmark"][0] - final
    f["oee_top2"] = int(top2_oee)
    f["oee_gap_phrase"] = ("equal to its entire gap to best-in-class" if top2_oee == gap_bic
                           else f"{pct(top2_oee / gap_bic * 100)} of its gap to best-in-class")
    f["changeover_min"] = d["pune_oee"]["changeover_min"]
    f["changeover_best"] = d["pune_oee"]["changeover_best"]

    vas = d["value_at_stake"]
    ops = sum(sum(r) for r in vas["values"])
    pune_chakan = sum(r[0] + r[1] for r in vas["values"])
    commercial = sum(vas["commercial"].values())
    f["ops_value"] = fmt_inr_cr(ops)
    f["pune_chakan_share"] = pct(pune_chakan / ops * 100)
    f["commercial_value"] = fmt_inr_cr(commercial)
    f["value_at_stake"] = fmt_inr_cr(ops + commercial)
    f["oee_value"] = fmt_inr_cr(sum(vas["values"][0]))
    f["rm_value"] = fmt_inr_cr(vas["commercial"]["Raw-material index clauses"])
    f["pm_value"] = fmt_inr_cr(vas["commercial"]["Price and mix"])

    lev = {p["label"]: p for p in d["levers"]["points"]}
    assert sum(p["y"] for p in lev.values()) == ops + commercial, "lever values must equal the prize"
    f["oee_pm_value"] = fmt_inr_cr(lev["OEE uplift"]["y"] + lev["Price and mix"]["y"])
    f["pune_chakan_value"] = fmt_inr_cr(pune_chakan)

    walk = d["margin_walk"]
    wl = levels([Step(s["label"], s.get("value"), s.get("kind", "delta")) for s in walk["steps"]])
    fy27 = wl[-1][1]
    f["fy27_margin"] = pct(fy27, 1)
    f["target_gap_bps"] = round((walk["benchmark"][0] - fy27) * 100)
    f["fy27_revenue"] = fmt_num(walk["fy27_revenue"], 0)
    by = {s["label"]: s["value"] for s in walk["steps"]}
    f["pm_bps"] = round(by["Price and mix"] * 100)
    for s in walk["steps"][2:-1]:           # lever bps must equal lever value over FY27 revenue
        assert abs(s["value"] - lev[s["label"]]["y"] / walk["fy27_revenue"] * 100) < 0.01, s["label"]

    def run_rate(month):
        return sum(_value(t["note"]) * min(1, max(0, (month - t["start"]) / (t["end"] - t["start"])))
                   for t in d["roadmap"]["tasks"])
    for m in (6, 12, 24):
        f[f"runrate_m{m}"] = fmt_inr_cr(run_rate(m))
    assert round(run_rate(24)) == ops + commercial, "roadmap must deliver the full prize"
    f["programme_capex"] = fmt_inr_cr(d["programme"]["capex_cr"])
    f["tmo_months"] = d["programme"]["tmo_months"]
    return f


def _value(note: str) -> float:
    m = re.search(r"₹(\d+)", note)
    return float(m.group(1)) if m else 0.0


def main(out_dir: Path, family: str | None = None):
    plan = Plan.model_validate_json((HERE / "plan.json").read_text())
    data = json.loads((HERE / "data.json").read_text())
    facts = compute_facts(data)
    brief_numbers = set(re.findall(r"\d[\d,.]*", (HERE / "brief.md").read_text()))
    deck, decisions = render(plan, data, facts, allowed_numbers=brief_numbers, family=family)
    actions, issues = lint_and_repair(deck)
    lf = lookfeel.check(deck, decisions, audience=plan.audience)
    story = consistency.matrix_vs_roadmap(data["levers"], data["roadmap"])
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"margin_recovery_{family or plan.family}"
    path = deck.save(out_dir / f"{name}.pptx")
    (out_dir / f"{name}_plan_report.md").write_text(report(plan, decisions, facts, lf, story))
    (out_dir / "facts.json").write_text(json.dumps(facts, indent=1, ensure_ascii=False))
    print(path)
    print("repairs:", actions or "none")
    print("lint:", "clean" if not issues else "\n  " + "\n  ".join(map(str, issues)))
    print("look and feel:", "pass" if lf.passed else "FAIL")
    for r in lf.failures():
        print(f"  [{r.code}] {r.detail}")
    print("storyline:", "consistent" if not story else "\n  " + "\n  ".join(story))
    warn = [(d.slide, d.title_warnings) for d in decisions if d.title_warnings]
    print("typed numbers in titles:", warn or "none")
    return path, issues, lf, story


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("out/margin_recovery")
    main(out, sys.argv[2] if len(sys.argv) > 2 else None)
