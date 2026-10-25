"""See the Barn from the Air (2026-10-24). Scott: "some sort of pin on the barn. The fly over isn't showing what
building it is", then the street in front "is quite acceptable", "Both" (barn pages and My Farm) and A of
farm-account/notes/from-barns-air-*-2026-10-24.png, on notes/barn-from-the-air-*-2026-10-24.png."""
import json
import math
import re
from datetime import date
from pathlib import Path

import barn_pages
import build
import cards
from tests.test_barns import answer, barns_file  # noqa: F401  (the fixture)

ROOT = Path(build.__file__).parent


def test_a_barn_with_a_spot_gets_the_section_and_one_without_does_not(barns_file, tmp_path, monkeypatch):
    spots = tmp_path / "spots.json"
    spots.write_text(json.dumps({"barns": {"1848": {"lat": 40.70, "lon": -99.08, "from": "address"},
                                           "9999": {"lat": 0, "lon": 0, "from": "address"}}}), encoding="utf-8")
    monkeypatch.setattr(barn_pages, "SPOTS", spots)
    monkeypatch.setattr(barn_pages.load_spots, "__defaults__", (spots,))
    cards.record_barns(answer(400), date(2026, 9, 25))
    site = build.build()
    page = (site / "barn-kearney-ne-1848.html").read_text(encoding="utf-8")
    assert '<h2 id="from-the-air">See the Barn from the Air</h2>' in page and 'data-lat="40.7" data-lon="-99.08"' in page
    assert page.index('id="from-the-air"') < page.index('id="contact"')                 # just above Contact the Barn
    assert ">Fly Over the Barn</button>" in page and "so it may" in page and '<script src="barn-air.js' in page
    assert "maplibre-gl" not in page                     # the 3D map loads only when Fly Over the Barn is pressed
    other = (site / "barn-lexington-ne-1849.html").read_text(encoding="utf-8")
    assert "from-the-air" not in other and "barn-air.js" not in other
    listed = json.loads((site / "barn-list.json").read_text(encoding="utf-8"))["barns"]
    assert listed["1848"]["air"] is True and listed["1849"]["air"] is False
    assert "9999" not in barn_pages.load_spots(spots)                                     # not in the lower 48


def test_the_still_photo_is_centred_on_the_pin():
    url = barn_pages.photo_url(40.25826, -103.61094)
    x0, y0, x1, y1 = (float(v) for v in re.search(r"bbox=([^&]+)", url).group(1).split(","))
    lon = (x0 + x1) / 2 * 180 / 20037508.342789244
    lat = math.degrees(2 * math.atan(math.exp((y0 + y1) / 2 * math.pi / 20037508.342789244)) - math.pi / 2)
    assert abs(lat - 40.25826) < 1e-4 and abs(lon + 103.61094) < 1e-4
    assert abs((x1 - x0) / (y1 - y0) - 16 / 9) < 0.01 and "USGSImageryOnly" in url and "size=1280,720" in url


def test_the_spots_are_the_sites_barns_with_their_source():
    data = json.loads((ROOT / "content" / "barn_spots.json").read_text(encoding="utf-8"))
    assert "APHIS" in data["source"] and "Census Geocoder" in data["source"]
    barns = cards.load_barns()["barns"]
    for slug, s in data["barns"].items():
        assert slug in barns, slug
        assert s["from"] in ("address", "checked") and s["address"] and date.fromisoformat(s["checked"])
        assert 24 <= s["lat"] <= 50 and -125 <= s["lon"] <= -66
    assert data["barns"]["3090"]["from"] == data["barns"]["1902"]["from"] == "checked"    # Scott dragged these two
    assert "1830" not in data["barns"]          # Ada: its county-road address didn't match, so no pin until placed


def test_the_fly_over_is_the_tested_one():
    js = (ROOT / "static" / "barn-air.js").read_text(encoding="utf-8")
    for words in ("zoom: 14.5, pitch: 60, bearing: 75, speed: 0.35", 'map.once("moveend", () => map.once("idle", spin));',
                  "cp.altitude - (map.transform.elevation + rel) >= 250", '"raster-opacity-transition": { duration: 0 }',
                  'maplibregl.setWorkerUrl("maplibre/maplibre-gl-csp-worker.js")', "map_action=pano&viewpoint=",
                  '"Fly Again"', '"Road Names"', '"Street View \u203a"'):
        assert words in js, words
    assert "innerHTML" not in js and "setBearing" not in js       # one long easeTo, never a step every frame
    for name in ("maplibre-gl-csp.js", "maplibre-gl-csp-worker.js", "maplibre-gl.css", "LICENSE.txt"):
        assert (ROOT / "static" / "maplibre" / name).is_file(), name
    css = (ROOT / "static" / "site.css").read_text(encoding="utf-8")
    assert ".air-map .air-canvas { position: absolute; inset: 0; width: 100%; height: 100%; }" in css
    assert ".air-pin.on-map {" in css and ".live" not in css[css.index("/* See the Barn from the Air"):]
    privacy = (ROOT / "templates" / "privacy.html").read_text(encoding="utf-8")
    assert '<li id="barn-air"><strong>A barn from the air.</strong>' in privacy


def test_street_view_shows_in_the_box_only_with_a_key(barns_file, tmp_path, monkeypatch):  # noqa: F811
    """2026-10-25, A of notes/street-view-in-page-2026-10-25.png. The key comes from the CORNERPOST_GOOGLE_EMBED_KEY
    setting or the Git-ignored google_embed_key.txt; without one the page keeps the smaller-window Street View."""
    import config
    spots = tmp_path / "spots.json"
    spots.write_text(json.dumps({"barns": {"1848": {"lat": 40.70, "lon": -99.08, "from": "address"}}}), encoding="utf-8")
    monkeypatch.setattr(barn_pages, "SPOTS", spots)
    monkeypatch.setattr(barn_pages.load_spots, "__defaults__", (spots,))
    cards.record_barns(answer(400), date(2026, 9, 25))
    monkeypatch.setattr(config, "google_embed_key", lambda: "")
    page = (build.build() / "barn-kearney-ne-1848.html").read_text(encoding="utf-8")
    assert "data-sv-key" not in page and "Street View: Google." not in page
    monkeypatch.setattr(config, "google_embed_key", lambda: "test-key-1")
    page = (build.build() / "barn-kearney-ne-1848.html").read_text(encoding="utf-8")
    assert 'data-sv-key="test-key-1"' in page and "Street View: Google." in page


def test_the_key_is_read_from_the_setting_or_the_ignored_file(tmp_path, monkeypatch):
    import config
    monkeypatch.setenv("CORNERPOST_GOOGLE_EMBED_KEY", " from-env ")
    assert config.google_embed_key() == "from-env"
    monkeypatch.delenv("CORNERPOST_GOOGLE_EMBED_KEY")
    assert "google_embed_key.txt" in (ROOT / ".gitignore").read_text(encoding="utf-8").split()
    assert "AIza" not in (ROOT / "config.py").read_text(encoding="utf-8")          # never written in the source


def test_the_page_script_swaps_the_map_for_street_view_and_back():
    js = (ROOT / "static" / "barn-air.js").read_text(encoding="utf-8")
    for words in ('const svKey = box.dataset.svKey || "";', "https://www.google.com/maps/embed/v1/streetview?key=",
                  "\\u2039 Back to the Map", "Open in Google Maps \\u203a", 'sv.addEventListener("click", svKey ? streetViewHere : streetView);',
                  "map.resize();"):
        assert words in js, words
    css = (ROOT / "static" / "site.css").read_text(encoding="utf-8")
    assert ".air-sv-box {" in css and ".air-sv {" in css
    privacy = (ROOT / "templates" / "privacy.html").read_text(encoding="utf-8")
    assert " ".join(privacy.split()).count("Nothing of Google's loads until you press it") == 2
