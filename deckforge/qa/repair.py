"""Deterministic repairs routed from lint issues (TRD 5.3). Each repair is local and re-checked."""

from __future__ import annotations

from deckforge.assets.treatment import luminance, scrim_alpha_for
from deckforge.qa.lint import Issue, lint, min_contrast
from deckforge.render.canvas import Deck


def repair_contrast(deck: Deck, max_alpha: float = 0.85) -> list[str]:
    """For text over imagery that fails WCAG contrast, add the weakest backlight that passes."""
    actions = []
    for c in deck.slides:
        for i, p in enumerate(c.placed):
            if p.kind != "text" or p.shape is None:
                continue
            cx, cy = p.box[0] + p.box[2] // 2, p.box[1] + p.box[3] // 2
            bg = next((b for b in reversed(c.placed[:i]) if b.kind in ("image", "fill")
                       and b.box[0] <= cx <= b.box[0] + b.box[2] and b.box[1] <= cy <= b.box[1] + b.box[3]), None)
            if bg is None or bg.kind != "image":
                continue
            light_text = luminance(p.color) > 0.4
            scrim = deck.theme.glow[0] if light_text else deck.theme.paper
            alpha = scrim_alpha_for(bg.image, bg.box, p.box, p.color, scrim, min_contrast(p.size, p.bold))
            if alpha > 0:
                alpha = min(max_alpha, alpha + 0.1)        # margin for feathered edges
                c.backlight(p, scrim, alpha)
                actions.append(f"slide {c.index}: backlight {alpha:.2f} behind '{p.name}'")
    return actions


def lint_and_repair(deck: Deck) -> tuple[list[str], list[Issue]]:
    actions = repair_contrast(deck) if any(i.code == "contrast" for i in lint(deck)) else []
    return actions, lint(deck)
