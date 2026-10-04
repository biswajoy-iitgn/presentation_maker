import urllib.request

import pytest
from PIL import Image
from pptx.util import Inches

from deckforge.qa.lint import lint
from deckforge.qa.repair import lint_and_repair
from deckforge.render.canvas import Deck
from deckforge.tokens import MERIDIAN


def test_overlap_and_off_slide_detected():
    deck = Deck(MERIDIAN)
    c = deck.new_slide()
    c.text(Inches(1), Inches(1), Inches(4), Inches(0.5), "First block of text", name="a")
    c.text(Inches(2), Inches(1.1), Inches(4), Inches(0.5), "Second block of text", name="b")
    c.text(Inches(12), Inches(7.3), Inches(3), Inches(0.5), "Too far right", name="c")
    codes = {(i.code, i.message.split("'")[1]) for i in lint(deck)}
    assert ("overlap", "a") in codes and ("off_slide", "c") in codes


def test_contrast_on_fill_detected():
    deck = Deck(MERIDIAN)
    c = deck.new_slide()
    c.rect(0, 0, Inches(5), Inches(2), MERIDIAN.panel)
    c.text(Inches(0.5), Inches(0.5), Inches(4), Inches(0.5), "Navy on navy", color="#1A2A44", name="bad")
    assert [i.code for i in lint(deck)] == ["contrast"]


def test_repair_adds_backlight_on_bright_image():
    deck = Deck(MERIDIAN)
    c = deck.new_slide()
    c.picture(Image.new("RGB", (400, 200), (235, 238, 245)), 0, 0, Inches(6), Inches(3), name="bg")
    c.text(Inches(0.5), Inches(1), Inches(4), Inches(0.5), "White text on a bright photo", color="#FFFFFF",
           size=14, name="caption")
    assert any(i.code == "contrast" for i in lint(deck))
    actions, issues = lint_and_repair(deck)
    assert actions and not issues
    names = [s.name for s in c.slide.shapes]
    assert names.index("DF_backlight") < names.index("caption")   # backlight sits behind the text


def _github_reachable() -> bool:
    try:
        urllib.request.urlopen("https://raw.githubusercontent.com", timeout=5)
        return True
    except OSError as e:
        return getattr(e, "code", None) is not None   # an HTTP error still proves reachability


@pytest.mark.network
@pytest.mark.skipif(not _github_reachable(), reason="needs GitHub raw content for icons, flags, boundaries")
def test_demo_deck_builds_lint_clean(tmp_path):
    from deckforge.demo.build_demo import build
    path, _, issues = build(tmp_path)
    assert path.exists() and not issues
