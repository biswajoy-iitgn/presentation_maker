"""Cross-slide consistency: the storyline must not contradict itself between exhibits.

A partner reads the deck as one argument. If the prioritisation matrix calls a lever a quick win but the
roadmap starts it in a later wave, or calls it a major project but schedules it first, the deck loses
credibility on that page. These checks compare the structured data behind the exhibits, not the pixels.
"""

from __future__ import annotations

QUADRANT = {(True, True): "quick win", (False, True): "major project", (True, False): "fill-in",
            (False, False): "deprioritise"}


def quadrant(point: dict, x_ref: float, y_ref: float) -> str:
    return QUADRANT[(point["x"] > x_ref, point["y"] > y_ref)]


def matrix_vs_roadmap(levers: dict, roadmap: dict) -> list[str]:
    """levers: matrix dataset (points with label, x = ease, y = value; x_ref, y_ref).
    roadmap: tasks with wave (0 = first) and lever (the matrix label the task delivers).
    Quick wins must start in the first wave. Major projects and deprioritised levers must not."""
    issues = []
    xr, yr = levers["x_ref"][0], levers["y_ref"][0]
    waves: dict[str, set[int]] = {}
    for t in roadmap["tasks"]:
        if t.get("lever"):
            waves.setdefault(t["lever"], set()).add(t["wave"])
    for p in levers["points"]:
        q = quadrant(p, xr, yr)
        w = waves.get(p["label"])
        if w is None:
            issues.append(f"{p['label']} is on the prioritisation matrix but no roadmap task delivers it")
        elif q == "quick win" and min(w) != 0:
            issues.append(f"{p['label']} is a quick win on the matrix but starts in wave {min(w) + 1} of the roadmap")
        elif q in ("major project", "deprioritise") and min(w) == 0:
            issues.append(f"{p['label']} is a {q} on the matrix but the roadmap schedules it in wave 1")
    return issues
