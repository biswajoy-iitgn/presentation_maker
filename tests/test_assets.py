import numpy as np
from PIL import Image
from pptx.util import Inches

from deckforge.assets import qa, treatment
from deckforge.assets.needs import AssetNeed
from deckforge.assets.resolver import AssetResolver
from deckforge.assets.sources import geo, procedural, stock
from deckforge.assets.sources.generate import ImageBrief, TextToImageClient
from deckforge.render.canvas import Deck
from deckforge.tokens import MERIDIAN


def test_luminance_and_contrast():
    assert treatment.luminance("#FFFFFF") == 1.0 and treatment.luminance("#000000") == 0.0
    assert round(treatment.contrast_ratio(1.0, 0.0), 1) == 21.0


def test_duotone_maps_extremes():
    img = Image.new("RGB", (2, 1))
    img.putpixel((0, 0), (0, 0, 0))
    img.putpixel((1, 0), (255, 255, 255))
    out = treatment.duotone(img, "#102030", "#F0E0D0")
    assert out.getpixel((0, 0)) == (16, 32, 48) and out.getpixel((1, 0)) == (240, 224, 208)


def test_gradient_alpha_endpoints():
    a = treatment.gradient_alpha(101, 5, 0.8, 0.0, 0)
    assert abs(a[0, 0] - 0.8) < 1e-6 and abs(a[0, -1]) < 1e-6


def test_smart_crop_aspect_and_avoids_text_zone():
    img = Image.new("RGB", (1600, 900), (20, 20, 20))
    img.paste((255, 255, 255), (100, 350, 300, 550))          # salient object on the left
    crop = treatment.smart_crop(img, 1.0, avoid=(0.0, 0.0, 0.5, 1.0))
    assert abs(crop.width / crop.height - 1.0) < 0.02
    arr = np.asarray(crop.convert("L"))
    left, right = arr[:, : crop.width // 2].mean(), arr[:, crop.width // 2:].mean()
    assert right >= left                                       # object kept out of the left text zone


def test_scrim_alpha_zero_when_already_legible_and_positive_when_not():
    dark = Image.new("RGB", (100, 100), (10, 10, 30))
    light = Image.new("RGB", (100, 100), (230, 230, 240))
    box = (0, 0, 1000, 1000)
    assert treatment.scrim_alpha_for(dark, box, box, "#FFFFFF", "#000000", 4.5) == 0.0
    assert treatment.scrim_alpha_for(light, box, box, "#FFFFFF", "#000000", 4.5) > 0.3


def test_procedural_styles_are_deterministic():
    for name, fn in procedural.STYLES.items():
        a, b, c = fn(w=320, h=180, seed=1), fn(w=320, h=180, seed=1), fn(w=320, h=180, seed=2)
        assert a.size == (320, 180), name
        assert a.tobytes() == b.tobytes() and a.tobytes() != c.tobytes(), name


def test_qa_flags_duplicates_and_low_resolution():
    img = procedural.aurora(w=640, h=360, seed=4)
    first = qa.check(img, min_width=600)
    assert first.passed
    again = qa.check(img, min_width=1280, seen_hashes=[first.hash])
    assert not again.passed and len(again.reasons) == 2


def test_stock_sources_parse_and_unsplash_pings(fake_get):
    p = stock.PexelsSource("k", get=fake_get).search("city")
    u = stock.UnsplashSource("k", get=fake_get).search("city")
    o = stock.OpenverseSource(get=fake_get).search("city")
    assert p[0].licence == "Pexels License" and u[0].use_ping and o[0].licence == "CC0"
    stock.download(u[0], fake_get)
    assert any("api.unsplash.com/dl/u1" in url for url, _ in fake_get.calls)


def test_photo_chain_uses_stock_then_records_licence(fake_get):
    r = AssetResolver(MERIDIAN, stock_sources=[stock.PexelsSource("k", get=fake_get)],
                      t2i=TextToImageClient(endpoint=None), get=fake_get)
    img = r.photo(AssetNeed(kind="photo", role="band", width_px=1280, height_px=400), ImageBrief("city"))
    assert img.size == (1280, 400)
    assert r.records[-1].source == "pexels" and r.records[-1].licence == "Pexels License"


def test_photo_chain_prefers_generation_and_marks_ai(fake_get):
    import base64
    import io
    buf = io.BytesIO()
    Image.open(io.BytesIO(fake_get("https://img/x.jpg"))).save(buf, "PNG")
    t2i = TextToImageClient("http://gpu:8601", post=lambda url, payload: {
        "image_base64": base64.b64encode(buf.getvalue()).decode(), "model": "flux1-schnell"})
    r = AssetResolver(MERIDIAN, stock_sources=[], t2i=t2i, get=fake_get)
    r.photo(AssetNeed(kind="photo", role="band", width_px=1280, height_px=400), ImageBrief("city"))
    assert r.records[-1].source == "t2i:flux1-schnell" and r.records[-1].ai_generated


def test_photo_chain_falls_back_to_procedural(fake_get):
    r = AssetResolver(MERIDIAN, connected=False, stock_sources=[], t2i=TextToImageClient(None), get=fake_get)
    img = r.photo(AssetNeed(kind="photo", role="band", width_px=960, height_px=200), ImageBrief("anything"))
    assert img.size == (960, 200) and r.records[-1].source.startswith("procedural:")


def test_icons_flags_and_map(fake_get):
    r = AssetResolver(MERIDIAN, stock_sources=[], t2i=TextToImageClient(None), get=fake_get)
    icon = r.icon("truck", "#123456", px=64)
    assert icon.mode == "RGBA" and icon.size == (64, 64)
    assert r.flag("de", 120).size == (120, 90)
    countries = r.countries()
    assert set(countries) == {"AAA", "BBB"}                    # Antarctica excluded
    deck = Deck(MERIDIAN)
    c = deck.new_slide()
    anchors = geo.draw_world(c, (0, 0, Inches(8), Inches(4)), {"AAA": "#FF0000"}, "#DDDDDD", countries=countries,
                             min_area_deg2=0.6)
    assert "AAA" in anchors
    assert sum(1 for s in c.slide.shapes if s.name.startswith("map_")) == 2
